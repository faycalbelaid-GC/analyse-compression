import pandas as pd
import numpy as np

def generate_data(filename="sample_data.csv"):
    fc = 30.0 # MPa
    eps0 = 0.002
    epsu = 0.0035

    # Generate strain points
    strains_asc = np.linspace(0, eps0, 100)
    strains_desc = np.linspace(eps0, epsu, 50)[1:]

    strains = np.concatenate([strains_asc, strains_desc])
    stresses = np.zeros_like(strains)

    # Ascending branch (parabola)
    mask_asc = strains <= eps0
    stresses[mask_asc] = fc * (2 * (strains[mask_asc] / eps0) - (strains[mask_asc] / eps0)**2)

    # Descending branch (linear softening to 0.85 fc)
    mask_desc = strains > eps0
    stresses[mask_desc] = fc * (1 - 0.15 * (strains[mask_desc] - eps0) / (epsu - eps0))

    # Add some noise
    noise = np.random.normal(0, 0.2, len(stresses))
    stresses = np.clip(stresses + noise, 0, None)

    df = pd.DataFrame({
        "Strain": strains,
        "Stress": stresses
    })
    df.to_csv(filename, index=False)
    print(f"Données générées et sauvegardées dans {filename}")

if __name__ == "__main__":
    generate_data()
