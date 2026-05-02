# Analyse d'essais de compression automatisée

Ce projet contient un script Python conçu pour analyser automatiquement les données issues d'une presse d'essai de compression (contrainte et déformation).

## Fonctionnalités
- **Lecture CSV** : Traitement des données brutes avec `pandas`.
- **Analyse Mécanique** :
  - Extraction de la Résistance à la compression ($f_c$).
  - Extraction de la Déformation ultime ($\varepsilon_u$).
  - Calcul automatique du Module de Young ($E$) par régression linéaire sur la phase élastique initiale.
- **Visualisation** : Génération d'une courbe de comportement Matériau avec `matplotlib`.
- **Rapport Automatisé** : Création d'un rapport de synthèse au format PDF (incluant résultats et graphiques) avec `reportlab`.

## Fichiers du Dépôt
- `analyse_compression.py` : Le script principal qui prend en entrée un fichier CSV, effectue les calculs, trace le graphique et génère le PDF.
- `générer_données_exemple.py` : Script utilitaire pour générer des données factices afin de tester le programme sans données réelles.
- `requirements.txt` : Liste des dépendances nécessaires pour faire tourner les scripts.

## Installation et Utilisation

1. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

2. **Générer un fichier de test (Optionnel)**
   ```bash
   python générer_données_exemple.py
   ```
   *Ceci créera un fichier `sample_data.csv` dans le dossier.*

3. **Exécuter l'analyse sur un seul fichier**
   ```bash
   python analyse_compression.py sample_data.csv
   ```

4. **Exécuter l'analyse en lot (sur tout un dossier)**
   Placez plusieurs fichiers `.csv` dans un dossier et lancez la commande :
   ```bash
   python analyse_compression.py chemin/vers/le/dossier
   ```
   *Ceci analysera tous les CSV, générera les graphes et PDF pour chacun, et créera un fichier global `synthese_essais.xlsx`.*

## Résultats produits
Après exécution du script principal :
- Pour un fichier : Un graphe `plot.png` et un document `rapport.pdf`.
- Pour un dossier : Un graphe et un PDF par essai, plus un tableau récapitulatif `synthese_essais.xlsx`.
