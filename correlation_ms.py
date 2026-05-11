import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = '/home/ASUS/MoTR/ETReadingMeasures/'

TIME_METRICS = ['first_duration', 'total_duration']
MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']

def load_folder_data(folder_path):
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not all_files:
        return pd.DataFrame()
    big_df = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)
    return big_df

def analyze_ms_correlations():
    df_motr = load_folder_data(PATH_MOTR_FOLDER)
    df_et = load_folder_data(PATH_ET_FOLDER)

    if df_motr.empty or df_et.empty:
        return

    for df in [df_motr, df_et]:
        for col in MERGE_KEYS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)

    cols_motr = MERGE_KEYS + [m for m in TIME_METRICS if m in df_motr.columns]
    cols_et = MERGE_KEYS + [m for m in TIME_METRICS if m in df_et.columns]

    motr_agg = df_motr[cols_motr].groupby(MERGE_KEYS).mean().reset_index()
    et_agg = df_et[cols_et].groupby(MERGE_KEYS).mean().reset_index()

    merged = pd.merge(motr_agg, et_agg, on=MERGE_KEYS, how='inner', suffixes=('_motr', '_et'))

    results = []
    common_metrics = [m for m in TIME_METRICS if m in df_motr.columns and m in df_et.columns]

    for metric in common_metrics:
        col_m = f"{metric}_motr"
        col_e = f"{metric}_et"
        temp = merged[[col_m, col_e]].dropna()
        
        if len(temp) < 10:
            continue

        r, p = stats.pearsonr(temp[col_m], temp[col_e])
        signif = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
        
        results.append({
            'Metric': metric,
            'Pearson_r': r,
            'p_value': p,
            'Significance': signif,
            'N': len(temp)
        })

    if results:
        res_df = pd.DataFrame(results).sort_values(by='Pearson_r', ascending=False)
        print("\nMS Correlations (MoTR vs ET):")
        print(res_df.to_string(index=False))

        plt.figure(figsize=(10, 6))
        sns.set_style("whitegrid")
        
        ax = sns.barplot(
            data=res_df, y='Metric', x='Pearson_r',
            palette='viridis', edgecolor='black', orient='h'
        )

        for container in ax.containers:
            ax.bar_label(container, fmt='%.2f', padding=3, fontweight='bold')

        plt.title("Correlation MoTR vs ET (Milliseconds)", fontsize=16, fontweight='bold')
        plt.xlabel("Pearson r", fontsize=14)
        plt.xlim(-0.2, 1.1)
        plt.tight_layout()
        plt.savefig('correlation_ms.svg', format='svg')
        res_df.to_csv('correlation_ms_stats.csv', index=False)
        print("\nSaved: correlation_ms.svg, correlation_ms_stats.csv")

if __name__ == "__main__":
    analyze_ms_correlations()
