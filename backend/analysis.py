import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import io

def load_data(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    if 'Strain' not in df.columns or 'Stress' not in df.columns:
        raise ValueError("Le fichier CSV doit contenir les colonnes 'Strain' et 'Stress'.")
    return df

def analyze_data(df):
    strains = df['Strain'].values
    stresses = df['Stress'].values

    idx_max = np.argmax(stresses)
    fc = stresses[idx_max]
    eps0 = strains[idx_max]
    eps_u = strains[-1]

    stress_10 = 0.10 * fc
    stress_40 = 0.40 * fc

    asc_stresses = stresses[:idx_max+1]
    asc_strains = strains[:idx_max+1]

    idx_10 = np.argmin(np.abs(asc_stresses - stress_10))
    idx_40 = np.argmin(np.abs(asc_stresses - stress_40))

    if idx_10 >= idx_40:
        idx_40 = idx_10 + 1 

    strain_range = asc_strains[idx_10:idx_40+1]
    stress_range = asc_stresses[idx_10:idx_40+1]

    A = np.vstack([strain_range, np.ones(len(strain_range))]).T
    m, c = np.linalg.lstsq(A, stress_range, rcond=None)[0]
    E = m

    return {
        'fc': float(fc),
        'eps0': float(eps0),
        'eps_u': float(eps_u),
        'E': float(E),
        'idx_10': int(idx_10),
        'idx_40': int(idx_40),
        'm': float(m),
        'c': float(c)
    }

def plot_curve(df, results):
    strains = df['Strain'].values
    stresses = df['Stress'].values

    plt.figure(figsize=(8, 6))
    plt.plot(strains, stresses, 'b-', label='Courbe expérimentale', alpha=0.7)
    plt.plot(results['eps0'], results['fc'], 'ro', label=f"fc = {results['fc']:.2f} MPa")

    strain_line = np.array([0, strains[results['idx_40']]])
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

def generate_pdf(results, plot_image_bytes, output_pdf_path):
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )
    elements.append(Paragraph("Rapport d'Essai de Compression", title_style))

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
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('PADDING', (0, 0), (-1, -1), 10)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    img = Image(io.BytesIO(plot_image_bytes.getvalue()), width=450, height=337.5)
    elements.append(img)

    doc.build(elements)
