import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os

# --- CONFIGURARE ---
PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/' 
PATH_ET_DATA = '/home/ASUS/MoTR/ETReadingMeasures/'
MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']
METRIC = 'total_duration' # Metrica principala

def load_pooled_data():
    # ... (Codul de incarcare e acelasi ca mai sus, il simplific aici) ...
    # 1. MoTR
    all_files = glob.glob(os.path.join(PATH_MOTR_FOLDER, "*.csv"))
    df_motr = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)
    
    # 2. ET
    all_files_et = glob.glob(os.path.join(PATH_ET_DATA, "*.csv"))
    df_et = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files_et), ignore_index=True)
    
    # 3. Calcul Lungime
    for df in [df_motr, df_et]:
        word_col = next((c for c in ['word', 'Word', 'text', 'Text'] if c in df.columns), None)
        if word_col: df['word_len'] = df[word_col].astype(str).apply(lambda x: len(x.strip('.,;:!? "()')))

    # 4. Merge
    for df in [df_motr, df_et]:
        for k in MERGE_KEYS: 
            if k in df.columns: df[k] = pd.to_numeric(df[k], errors='coerce').fillna(-1).astype(int)
            
    merged = pd.merge(df_motr, df_et, on=MERGE_KEYS, how='inner', suffixes=('_motr', '_et'))
    
    # Rezolvam word_len
    if 'word_len_et' in merged.columns: merged['word_len'] = merged['word_len_et']
    elif 'word_len_motr' in merged.columns: merged['word_len'] = merged['word_len_motr']
    
    return merged

def plot_z_scores():
    print("🚀 Generare Grafic Z-Score (Standardizat)...")
    
    df = load_pooled_data()
    if df is None: return

    # Filtrare date valide
    col_m = f"{METRIC}_motr"
    col_e = f"{METRIC}_et"
    subset = df[(df['word_len'] >= 3) & (df['word_len'] <= 15) & (df[col_m] > 0) & (df[col_e] > 0)].copy()

    # --- MAGIC STEP: Z-SCORE CALCULATION ---
    # z = (x - mean) / std
    # Asta aduce ambele distributii la Media 0 si Deviatia 1.
    subset['z_motr'] = (subset[col_m] - subset[col_m].mean()) / subset[col_m].std()
    subset['z_et'] = (subset[col_e] - subset[col_e].mean()) / subset[col_e].std()

    # Acum putem pune ambele pe ACEEASI AXA Y!
    
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    # Plotam Z-Scores
    sns.lineplot(data=subset, x='word_len', y='z_et', color='blue', marker='o', label='Eye-Tracking (Z-Score)')
    sns.lineplot(data=subset, x='word_len', y='z_motr', color='orange', marker='s', linestyle='--', label='MoTR (Z-Score)')
    
    plt.title(f"Standardized Comparison:", fontsize=14)
    plt.xlabel("Word Length", fontsize=12)
    plt.ylabel("Z-Score", fontsize=12)
    plt.axhline(0, color='black', linewidth=1, linestyle=':', alpha=0.5) # Linia mediei
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('z_score_comparison.png', dpi=300)
    print("🖼️ Grafic salvat: z_score_comparison.png")

if __name__ == "__main__":
    plot_z_scores()