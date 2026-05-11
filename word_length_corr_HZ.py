import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import numpy as np
import glob
import os

# --- CONFIGURARE ---
PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/' 
PATH_ET_DATA = '/home/ASUS/MoTR/ETReadingMeasures/'

MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']

# Metricile de timp pe care le convertim (cele originale in ms)
BASE_METRICS = ['first_duration', 'total_duration']

def load_data_from_source(path):
    if os.path.isfile(path):
        print(f"📄 Incarc fisier unic: {path}")
        return pd.read_csv(path, low_memory=False)
    elif os.path.isdir(path):
        print(f"📂 Detectat folder. Caut fisiere CSV in: {path}")
        all_files = glob.glob(os.path.join(path, "*.csv"))
        if not all_files: return None
        df_list = []
        for filename in all_files:
            try:
                df_list.append(pd.read_csv(filename, low_memory=False))
            except Exception: pass
        if df_list: return pd.concat(df_list, ignore_index=True)
    return None

def analyze_length_hz():
    print("🚀 Start Analiză: Lungime Cuvânt vs. Viteză (Hz)...")

    # 1. Incarcare
    df_motr = load_data_from_source(PATH_MOTR_FOLDER)
    df_et = load_data_from_source(PATH_ET_DATA)
    if df_motr is None or df_et is None: return

    # 2. Preprocesare (Lungime + Conversie Hz)
    print("⚙️  Calculam lungimile si convertim ms -> Hz...")
    
    for df in [df_motr, df_et]:
        # A. Asiguram chei numerice
        for k in MERGE_KEYS:
            if k in df.columns:
                df[k] = pd.to_numeric(df[k], errors='coerce').fillna(-1).astype(int)
        
        # B. Calculam Lungimea Cuvantului
        word_col = next((c for c in ['word', 'Word', 'text', 'Text'] if c in df.columns), None)
        if word_col:
            df['word_len'] = df[word_col].astype(str).apply(lambda x: len(x.strip('.,;:!? "()')))
        
        # C. Conversie in Hz (1000 / ms)
        for metric in BASE_METRICS:
            if metric in df.columns:
                # Convertim la numeric si fortam NaN pe erori
                vals_ms = pd.to_numeric(df[metric], errors='coerce')
                
                # Hz = 1000 / ms. 
                # Daca ms=0 (skip), Hz=inf -> NaN.
                vals_hz = 1000.0 / vals_ms
                vals_hz.replace([np.inf, -np.inf], np.nan, inplace=True)
                
                # Curățăm valorile extreme (ex: > 25Hz inseamna sub 40ms, probabil eroare/blink)
                vals_hz[vals_hz > 25.0] = np.nan
                
                df[f"{metric}_Hz"] = vals_hz

    # 3. Merge
    print("🔗 Unificam seturile de date...")
    merged = pd.merge(df_motr, df_et, on=MERGE_KEYS, how='inner', suffixes=('_motr', '_et'))
    
    # Rezolvam coloana word_len (luam una din ele)
    if 'word_len_et' in merged.columns: merged['word_len'] = merged['word_len_et']
    elif 'word_len_motr' in merged.columns: merged['word_len'] = merged['word_len_motr']

    print(f"✅ Dataset Final: {len(merged)} puncte.")

    # 4. VIZUALIZARE (Hz vs Length)
    metrics_hz = [f"{m}_Hz" for m in BASE_METRICS]
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    sns.set_style("whitegrid")

    for i, metric_hz in enumerate(metrics_hz):
        ax = axes[i]
        col_motr = f"{metric_hz}_motr"
        col_et = f"{metric_hz}_et"

        # Filtram: Lungimi normale (3-15) si valori Hz valide
        subset = merged[
            (merged['word_len'] >= 3) & 
            (merged['word_len'] <= 15) & # Ne oprim la 12 pt ca sunt putine cuvinte f. lungi si fac zgomot
            (merged[col_motr].notna()) & 
            (merged[col_et].notna())
        ].copy()

        if len(subset) == 0: continue

        # Calculam Corelatia Trendurilor (pe medii)
        grouped = subset.groupby('word_len')[[col_motr, col_et]].mean().reset_index()
        if len(grouped) > 2:
            r, p = stats.pearsonr(grouped[col_motr], grouped[col_et])
            signif = "***" if p < 0.001 else "**" if p < 0.01 else "*"
            title = f"{metric_hz}\nr = {r:.2f} ({signif})"
        else:
            title = metric_hz

        # --- Axa Stanga (Eye-Tracking) ---
        color_et = 'tab:blue'
        ax.set_xlabel('Word Length (characters)', fontsize=12)
        ax.set_ylabel(f'ET Speed ({metric_hz})', color=color_et, fontsize=12)
        
        sns.lineplot(
            data=subset, x='word_len', y=col_et, ax=ax, 
            color=color_et, marker='o', label='Eye-Tracking'
        )
        ax.tick_params(axis='y', labelcolor=color_et)
        ax.grid(True, linestyle='--', alpha=0.5)

        # --- Axa Dreapta (MoTR) ---
        ax2 = ax.twinx()
        color_motr = 'tab:orange'
        ax2.set_ylabel(f'MoTR Speed ({metric_hz})', color=color_motr, fontsize=12)
        
        sns.lineplot(
            data=subset, x='word_len', y=col_motr, ax=ax2, 
            color=color_motr, marker='s', linestyle='--', label='MoTR'
        )
        ax2.tick_params(axis='y', labelcolor=color_motr)
        
        ax.set_title(title, fontsize=14, fontweight='bold')

        # Legenda
        lines_1, labels_1 = ax.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax.legend(lines_1 + lines_2, ['Eye-Tracking (Hz)', 'MoTR (Hz)'], loc='upper right')
        ax2.get_legend().remove()

    plt.tight_layout()
    plt.savefig('length_vs_hz_analysis.svg', format='svg')
    print("\n🖼️ Grafic generat: length_vs_hz_analysis.svg")

if __name__ == "__main__":
    analyze_length_hz()