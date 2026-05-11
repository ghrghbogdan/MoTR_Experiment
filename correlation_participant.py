import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os
import re

PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = '/home/ASUS/MoTR/ETReadingMeasures/'

TIME_METRICS = ['first_duration', 'total_duration']
MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']

def extract_participant_number(filename):
    match = re.search(r'\d+', filename)
    return int(match.group()) if match else 0

def load_single_file(file_path):
    df = pd.read_csv(file_path, low_memory=False)
    for col in MERGE_KEYS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)
    return df

def analyze_participant_correlations():
    motr_files = sorted(glob.glob(os.path.join(PATH_MOTR_FOLDER, "*.csv")),
                        key=lambda x: extract_participant_number(os.path.basename(x)))
    et_files = sorted(glob.glob(os.path.join(PATH_ET_FOLDER, "*.csv")),
                      key=lambda x: extract_participant_number(os.path.basename(x)))

    if not motr_files or not et_files:
        return

    n_pairs = min(len(motr_files), len(et_files))
    results = []

    for i in range(n_pairs):
        motr_name = os.path.basename(motr_files[i])
        et_name = os.path.basename(et_files[i])
        
        motr_num = extract_participant_number(motr_name)
        et_num = extract_participant_number(et_name)

        df_motr = load_single_file(motr_files[i])
        df_et = load_single_file(et_files[i])

        cols_motr = MERGE_KEYS + [m for m in TIME_METRICS if m in df_motr.columns]
        cols_et = MERGE_KEYS + [m for m in TIME_METRICS if m in df_et.columns]

        motr_agg = df_motr[cols_motr].groupby(MERGE_KEYS).mean().reset_index()
        et_agg = df_et[cols_et].groupby(MERGE_KEYS).mean().reset_index()

        merged = pd.merge(motr_agg, et_agg, on=MERGE_KEYS, how='inner', suffixes=('_motr', '_et'))

        common_metrics = [m for m in TIME_METRICS if m in df_motr.columns and m in df_et.columns]

        for metric in common_metrics:
            col_m = f"{metric}_motr"
            col_e = f"{metric}_et"
            temp = merged[[col_m, col_e]].dropna()
            
            if len(temp) < 5:
                continue

            r, p = stats.pearsonr(temp[col_m], temp[col_e])
            signif = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
            
            results.append({
                'Participant_MoTR': motr_num,
                'Participant_ET': et_num,
                'Metric': metric,
                'Pearson_r': r,
                'p_value': p,
                'Significance': signif,
                'N': len(temp)
            })

    if results:
        res_df = pd.DataFrame(results)
        print("\nParticipant-Level Correlations:")
        print(res_df.to_string(index=False))

        fig, axes = plt.subplots(1, len(TIME_METRICS), figsize=(7*len(TIME_METRICS), 6))
        if len(TIME_METRICS) == 1:
            axes = [axes]

        for idx, metric in enumerate(TIME_METRICS):
            metric_data = res_df[res_df['Metric'] == metric].copy()
            metric_data = metric_data.sort_values(by='Participant_MoTR')

            ax = axes[idx]
            ax.bar(metric_data['Participant_MoTR'].astype(str), metric_data['Pearson_r'],
                   color='steelblue', edgecolor='black')
            ax.set_title(f'{metric}', fontsize=14, fontweight='bold')
            ax.set_xlabel('Participant', fontsize=12)
            ax.set_ylabel('Pearson r', fontsize=12)
            ax.axhline(0, color='gray', linestyle='--', linewidth=1)
            ax.set_ylim(-0.2, 1.1)
            ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig('correlation_participant.svg', format='svg')
        res_df.to_csv('correlation_participant_stats.csv', index=False)
        print("\nSaved: correlation_participant.svg, correlation_participant_stats.csv")

if __name__ == "__main__":
    analyze_participant_correlations()
