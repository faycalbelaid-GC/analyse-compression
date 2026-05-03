import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import io
from scipy.signal import savgol_filter

def load_data(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    if 'Strain' not in df.columns or 'Stress' not in df.columns:
        raise ValueError("Le fichier CSV doit contenir les colonnes 'Strain' et 'Stress'.")
    return df

def analyze_data(df, apply_smoothing=False, e_start_pct=10, e_end_pct=40, age_days=None, target_fc=None):
    strains = df['Strain'].values
    stresses = df['Stress'].values

    if apply_smoothing and len(stresses) > 11:
        stresses = savgol_filter(stresses, window_length=11, polyorder=3)
        stresses = np.maximum(stresses, 0)

    idx_max = np.argmax(stresses)
    fc = stresses[idx_max]
    eps0 = strains[idx_max]
    eps_u = strains[-1]

    toughness = np.trapz(stresses, strains)

    stress_start = (e_start_pct / 100.0) * fc
    stress_end = (e_end_pct / 100.0) * fc

    asc_stresses = stresses[:idx_max+1]
    asc_strains = strains[:idx_max+1]

    idx_start = np.argmin(np.abs(asc_stresses - stress_start))
    idx_end = np.argmin(np.abs(asc_stresses - stress_end))

    if idx_start >= idx_end:
        idx_end = idx_start + 1
        if idx_end >= len(asc_strains):
            idx_end = len(asc_strains) - 1
            idx_start = max(0, idx_end - 1)

    strain_range = asc_strains[idx_start:idx_end+1]
    stress_range = asc_stresses[idx_start:idx_end+1]

    A = np.vstack([strain_range, np.ones(len(strain_range))]).T
    m, c = np.linalg.lstsq(A, stress_range, rcond=None)[0]
    E = m

    fc_28_pred = None
    if age_days is not None and age_days > 0 and age_days != 28:
        s = 0.25 # Coefficient Eurocode 2 pour ciment classe N
        beta_cc = np.exp(s * (1 - np.sqrt(28 / age_days)))
        fc_28_pred = fc / beta_cc

    compliance_status = None
    if target_fc is not None and target_fc > 0:
        val_to_check = fc_28_pred if fc_28_pred is not None else fc
        if val_to_check >= target_fc:
            compliance_status = "Conforme"
        else:
            compliance_status = "Non-conforme"

    anomaly_flag = False
    if fc < 1.0 or E < 100 or eps0 > 0.05:
        anomaly_flag = True

    return {
        'fc': float(fc),
        'eps0': float(eps0),
        'eps_u': float(eps_u),
        'E': float(E),
        'toughness': float(toughness),
        'fc_28_pred': float(fc_28_pred) if fc_28_pred else None,
        'compliance_status': compliance_status,
        'anomaly_flag': anomaly_flag,
        'idx_start': int(idx_start),
        'idx_end': int(idx_end),
        'm': float(m),
        'c': float(c),
        'strains_plot': strains.tolist(),
        'stresses_plot': stresses.tolist()
    }

def plot_curve(results):
    strains = np.array(results['strains_plot'])
    stresses = np.array(results['stresses_plot'])

    plt.figure(figsize=(8, 6))
    plt.plot(strains, stresses, 'b-', label='Courbe expérimentale', alpha=0.7)
    plt.plot(results['eps0'], results['fc'], 'ro', label=f"fc = {results['fc']:.2f} MPa")

    strain_line = np.array([0, strains[results['idx_end']]])
    stress_line = results['m'] * strain_line + results['c']
    plt.plot(strain_line, stress_line, 'g--', label=f"Module E = {results['E']:.0f} MPa")

    plt.title("Courbe Contrainte-Déformation")
    plt.xlabel("Déformation (-)")
    plt.ylabel("Contrainte (MPa)")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=300)
    plt.close()
    img_buf.seek(0)
    return img_buf

def generate_pdf(results, plot_image_bytes, output_pdf_path, metadata=None):
    if metadata is None: metadata = {}
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor('#2c3e50'))
    elements.append(Paragraph("Rapport d'Essai de Compression", title_style))

    if metadata:
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=12, spaceAfter=6)
        if metadata.get('project'): elements.append(Paragraph(f"<b>Projet:</b> {metadata['project']}", meta_style))
        if metadata.get('specimen'): elements.append(Paragraph(f"<b>Échantillon:</b> {metadata['specimen']}", meta_style))
        if metadata.get('operator'): elements.append(Paragraph(f"<b>Opérateur:</b> {metadata['operator']}", meta_style))
        elements.append(Spacer(1, 20))

    data = [
        ['Propriété', 'Valeur', 'Unité'],
        ['Résistance à la compression (fc)', f"{results['fc']:.2f}", 'MPa'],
        ['Module de Young tangent (E)', f"{results['E']:.0f}", 'MPa'],
        ['Déformation à la contrainte max (ε0)', f"{results['eps0']:.5f}", '-'],
        ['Déformation ultime (εu)', f"{results['eps_u']:.5f}", '-']
    ]
    t = Table(data, colWidths=[200, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 8)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    img = Image(io.BytesIO(plot_image_bytes.getvalue()), width=450, height=337.5)
    elements.append(img)
    doc.build(elements)
