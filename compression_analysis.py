import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import sys
import os

def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        if 'Strain' not in df.columns or 'Stress' not in df.columns:
            raise ValueError("Le fichier CSV doit contenir les colonnes 'Strain' et 'Stress'.")
        return df
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {filepath} : {e}")
        raise e

def analyze_data(df):
    strains = df['Strain'].values
    stresses = df['Stress'].values

    # 1. Résistance à la compression (fc) et Déformation correspondante (eps0)
    idx_max = np.argmax(stresses)
    fc = stresses[idx_max]
    eps0 = strains[idx_max]

    # 2. Déformation ultime (eps_u) - ici prise comme la déformation max de l'essai
    eps_u = strains[-1]

    # 3. Module de Young (E) - Régression linéaire entre 10% et 40% de fc
    stress_10 = 0.10 * fc
    stress_40 = 0.40 * fc

    # Trouver les indices correspondants avant le pic
    asc_stresses = stresses[:idx_max+1]
    asc_strains = strains[:idx_max+1]

    idx_10 = np.argmin(np.abs(asc_stresses - stress_10))
    idx_40 = np.argmin(np.abs(asc_stresses - stress_40))

    if idx_10 >= idx_40:
        idx_40 = idx_10 + 1 # Sécurité pour avoir au moins 2 points

    strain_range = asc_strains[idx_10:idx_40+1]
    stress_range = asc_stresses[idx_10:idx_40+1]

    # Régression linéaire (Moindres carrés)
    A = np.vstack([strain_range, np.ones(len(strain_range))]).T
    m, c = np.linalg.lstsq(A, stress_range, rcond=None)[0]
    E = m

    return {
        'fc': fc,
        'eps0': eps0,
        'eps_u': eps_u,
        'E': E,
        'idx_10': idx_10,
        'idx_40': idx_40,
        'm': m,
        'c': c
    }

def plot_curve(df, results, output_image='plot.png'):
    strains = df['Strain'].values
    stresses = df['Stress'].values

    plt.figure(figsize=(8, 6))
    plt.plot(strains, stresses, 'b-', label='Courbe expérimentale', alpha=0.7)

    # Point max (fc)
    plt.plot(results['eps0'], results['fc'], 'ro', label=f"fc = {results['fc']:.2f} MPa")

    # Ligne pour le module de Young
    strain_line = np.array([0, strains[results['idx_40']]])
    stress_line = results['m'] * strain_line + results['c']
    plt.plot(strain_line, stress_line, 'g--', label=f"Module E = {results['E']:.0f} MPa")

    plt.title("Courbe Contrainte-Déformation - Essai de Compression")
    plt.xlabel("Déformation (-)")
    plt.ylabel("Contrainte (MPa)")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_image, dpi=300)
    plt.close()

def generate_pdf(results, plot_image, output_pdf='rapport_essai.pdf'):
    doc = SimpleDocTemplate(output_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )
    elements.append(Paragraph("Rapport d'Essai de Compression", title_style))

    # Résultats sous forme de tableau
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

    # Image
    if os.path.exists(plot_image):
        img = Image(plot_image, width=450, height=337.5)
        elements.append(img)
    else:
        elements.append(Paragraph("Image du graphique introuvable.", styles['Normal']))

    # Générer le PDF
    doc.build(elements)
    print(f"Rapport généré avec succès : {output_pdf}")

def process_file(csv_file, output_prefix=None):
    if output_prefix is None:
        output_prefix = os.path.splitext(os.path.basename(csv_file))[0]
    
    print(f"\n--- Traitement de {csv_file} ---")
    try:
        df = load_data(csv_file)
        results = analyze_data(df)
        
        plot_img = f"{output_prefix}_plot.png"
        pdf_out = f"{output_prefix}_rapport.pdf"
        
        plot_curve(df, results, plot_img)
        generate_pdf(results, plot_img, pdf_out)
        
        results['Fichier'] = os.path.basename(csv_file)
        return results
    except Exception as e:
        print(f"-> Ignoré suite à une erreur : {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python compression_analysis.py <fichier.csv ou dossier>")
        sys.exit(1)

    path = sys.argv[1]
    all_results = []

    if os.path.isfile(path):
        if not path.lower().endswith('.csv'):
            print("Le fichier doit être un .csv")
            sys.exit(1)
        res = process_file(path)
        if res:
            all_results.append(res)
            
    elif os.path.isdir(path):
        csv_files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith('.csv')]
        if not csv_files:
            print(f"Aucun fichier CSV trouvé dans le dossier {path}")
            sys.exit(1)
            
        for f in csv_files:
            res = process_file(f)
            if res:
                all_results.append(res)
                
        # Export Excel global
        if all_results:
            df_summary = pd.DataFrame(all_results)
            cols = ['Fichier', 'fc', 'E', 'eps0', 'eps_u']
            df_summary = df_summary[cols]
            df_summary.rename(columns={
                'fc': 'Résistance (MPa)',
                'E': 'Module Young (MPa)',
                'eps0': 'Déformation (fc)',
                'eps_u': 'Déformation ultime'
            }, inplace=True)
            
            excel_out = os.path.join(path, "synthese_essais.xlsx")
            try:
                df_summary.to_excel(excel_out, index=False)
                print(f"\n=> Synthèse globale générée avec succès : {excel_out}")
            except Exception as e:
                print(f"\n=> Erreur lors de la génération Excel : {e}\n(Avez-vous installé openpyxl ? 'pip install openpyxl')")
    else:
        print("Chemin invalide.")
        sys.exit(1)

if __name__ == "__main__":
    main()
