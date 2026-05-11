import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

# --- CONFIGURARE ---
PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/' 
PATH_ET_FOLDER = '/home/ASUS/MoTR/ETReadingMeasures/'

# Metricile pe care vrem sa le convertim in Hz
# (Doar cele care reprezinta TIMP/DURATA)
TIME_METRICS = [
    'first_duration',
    'total_duration',
    'gaze_duration',
    'right_bounded_rt',
    'go_past_time'
]

# Metricile de probabilitate raman la fel (nu se masoara in Hz)
PROB_METRICS = [
    'FPFix',        
    'FPReg',
    'RegIn_excl',
    'RegIn_incl'
]

MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']

def load_folder_data(folder_path, label):
    """ Incarca datele """
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not all_files:
        print(f"❌ Nu am gasit fisiere in {folder_path}")
        return pd.DataFrame()
    big_df = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)
    print(f"   ✅ {label} Incarcat: {len(big_df)} randuri.")
    return big_df

def convert_to_hz(df, metrics):
    """ 
    Transforma coloanele de timp (ms) in Frecventa (Hz).
    Formula: Hz = 1000 / ms
    """
    df_hz = df.copy()
    new_cols = []
    
    for m in metrics:
        if m in df.columns:
            # Convertim la numeric
            col_data = pd.to_numeric(df[m], errors='coerce')
            
            # Evitam impartirea la zero (Zero ms -> Infinit Hz -> NaN)
            # Daca durata e 0 (skip), frecventa e 'undefined' sau infinit, deci o ignoram la corelatie
            hz_values = 1000.0 / col_data
            hz_values.replace([np.inf, -np.inf], np.nan, inplace=True)
            
            new_col_name = f"{m}_Hz"
            df_hz[new_col_name] = hz_values
            new_cols.append(new_col_name)
    
    return df_hz, new_cols

def analyze_hz_correlations():
    # 1. Incarcare
    df_motr_raw = load_folder_data(PATH_MOTR_FOLDER, "MoTR")
    df_et_raw = load_folder_data(PATH_ET_FOLDER, "Eye-Tracking")

    if df_motr_raw.empty or df_et_raw.empty: return

    # 2. Curatare Chei
    for df in [df_motr_raw, df_et_raw]:
        for col in MERGE_KEYS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)

    # 3. CONVERSIE IN Hz (Transformarea Cheie) ⚡
    print("🔄 Convertim metricile de timp din ms in Hz...")
    df_motr_hz, hz_cols_motr = convert_to_hz(df_motr_raw, TIME_METRICS)
    df_et_hz, hz_cols_et = convert_to_hz(df_et_raw, TIME_METRICS)

    # Lista finala de metrici pentru analiza (Hz + Probabilitati originale)
    analysis_metrics_motr = hz_cols_motr + [m for m in PROB_METRICS if m in df_motr_raw.columns]
    analysis_metrics_et = hz_cols_et + [m for m in PROB_METRICS if m in df_et_raw.columns]

    # 4. Agregare (Mean per cuvant)
    # Atentie: Media frecventelor != Frecventa mediei, dar in analiza datelor de obicei agregam intai
    cols_to_keep_m = MERGE_KEYS + analysis_metrics_motr
    cols_to_keep_e = MERGE_KEYS + analysis_metrics_et

    motr_agg = df_motr_hz[cols_to_keep_m].groupby(MERGE_KEYS).mean().reset_index()
    et_agg = df_et_hz[cols_to_keep_e].groupby(MERGE_KEYS).mean().reset_index()

    # 5. Merge
    merged_df = pd.merge(
        motr_agg, 
        et_agg, 
        on=MERGE_KEYS, 
        how='inner', 
        suffixes=('_motr', '_et')
    )

    # 6. Corelatii
    results_data = []
    
    # Facem lista comuna de metrici (fara sufixe)
    # Scoatem '_Hz' din nume pentru a gasi perechea
    common_base_metrics = []
    for c in analysis_metrics_motr:
        if c in analysis_metrics_et: # Daca exista in ambele (ex: total_duration_Hz)
            common_base_metrics.append(c)
    
    print(f"📊 Analizam corelatiile pentru: {common_base_metrics}")

    for metric in common_base_metrics:
        col_m = f"{metric}_motr"
        col_e = f"{metric}_et"
        
        # Eliminam NaN (generat de impartirea la zero sau lipsa datelor)
        temp = merged_df[[col_m, col_e]].dropna()
        
        # Filtru optional: eliminam valori extreme de Hz (peste 20Hz inseamna <50ms, probabil eroare)
        # temp = temp[(temp[col_m] < 20) & (temp[col_e] < 20)]

        if len(temp) < 10: continue

        r, p = stats.pearsonr(temp[col_m], temp[col_e])
        signif = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
        
        results_data.append({
            'Metric (Hz)': metric,
            'Pearson_r': r,
            'Significance': signif,
            'N': len(temp)
        })

    # 7. Plotare
    if results_data:
        res_df = pd.DataFrame(results_data).sort_values(by='Pearson_r', ascending=False)
        print("\nRezultate Corelații (Hz):")
        print(res_df)

        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        
        ax = sns.barplot(
            data=res_df, y='Metric (Hz)', x='Pearson_r', 
            palette='magma', edgecolor='black', orient='h'
        )

        for i, container in enumerate(ax.containers):
            ax.bar_label(container, fmt='%.2f', padding=3, fontweight='bold')

        plt.title("Correlation MoTR vs ET (Processing Rate in Hz)", fontsize=16)
        plt.xlabel("Pearson Coefficient (r)", fontsize=14)
        plt.xlim(-0.2, 1.1) # Lasam loc si pt corelatii negative daca apar
        plt.legend([],[], frameon=False)
        
        plt.tight_layout()
        plt.savefig('hz_correlations.png', dpi=300)
        res_df.to_csv('hz_stats.csv', index=False)
        print("🖼️ Plot salvat: hz_correlations.png")

if __name__ == "__main__":
    analyze_hz_correlations()