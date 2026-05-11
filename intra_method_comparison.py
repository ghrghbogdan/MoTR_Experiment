import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os
import re

PATH_MOTR_FOLDER = '/home/ghr/Documents/Bogdan/MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = '/home/ghr/Documents/Bogdan/MoTR/ETReadingMeasures'

TIME_METRICS = ['first_duration', 'total_duration']
MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']

def ms_to_hz(ms_val):
    if pd.isna(ms_val) or ms_val <= 0:
        return np.nan
    return 1000.0 / ms_val

def extract_participant_number(filename):
    if 'motr_data_' in filename:
        match = re.search(r'motr_data_(\d+)', filename)
        return match.group(1) if match else filename
    elif 'data-1-' in filename:
        match = re.search(r'data-1-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})', filename)
        if match:
            timestamp = match.group(1)
            last_two = timestamp[-2:]
            return last_two
        return filename
    else:
        match = re.search(r'\d+', filename)
        return match.group() if match else filename

def load_all_participants(folder_path):
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    participants = {}
    for f in all_files:
        basename = os.path.basename(f).replace('.csv', '')
        pid = extract_participant_number(basename)
        df = pd.read_csv(f, low_memory=False)
        participants[pid] = df
    return participants

def prepare_participant(df):
    for col in MERGE_KEYS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1).astype(int)
    
    for metric in TIME_METRICS:
        if metric in df.columns:
            df[f"{metric}_hz"] = df[metric].apply(ms_to_hz)
    
    available = [m for m in TIME_METRICS if m in df.columns]
    hz_metrics = [f"{m}_hz" for m in TIME_METRICS if m in df.columns]
    cols = MERGE_KEYS + available + hz_metrics
    agg = df[cols].groupby(MERGE_KEYS).mean().reset_index()
    return agg, available, hz_metrics

def compute_pairwise_correlations(participants_dict, method_name):
    results_ms = []
    results_hz = []
    participant_ids = sorted(list(participants_dict.keys()), key=lambda x: int(x) if x.isdigit() else x)
    
    for i, p1_id in enumerate(participant_ids):
        p1_df, p1_metrics, p1_hz_metrics = prepare_participant(participants_dict[p1_id])
        
        for j, p2_id in enumerate(participant_ids):
            if i >= j:
                continue
            
            p2_df, p2_metrics, p2_hz_metrics = prepare_participant(participants_dict[p2_id])
            merged = pd.merge(p1_df, p2_df, on=MERGE_KEYS, how='inner', suffixes=('_p1', '_p2'))
            
            if len(merged) < 10:
                continue
            
            common_metrics_ms = list(set(p1_metrics) & set(p2_metrics))
            common_metrics_hz = list(set(p1_hz_metrics) & set(p2_hz_metrics))
            
            for metric in common_metrics_ms:
                col1 = f"{metric}_p1"
                col2 = f"{metric}_p2"
                temp = merged[[col1, col2]].dropna()
                
                if len(temp) < 10:
                    continue
                
                r, p = stats.pearsonr(temp[col1], temp[col2])
                
                results_ms.append({
                    'Method': method_name,
                    'Participant_1': p1_id,
                    'Participant_2': p2_id,
                    'Metric': metric,
                    'Pearson_r': r,
                    'p_value': p,
                    'N': len(temp)
                })
            
            for metric in common_metrics_hz:
                col1 = f"{metric}_p1"
                col2 = f"{metric}_p2"
                temp = merged[[col1, col2]].dropna()
                
                if len(temp) < 10:
                    continue
                
                r, p = stats.pearsonr(temp[col1], temp[col2])
                
                results_hz.append({
                    'Method': method_name,
                    'Participant_1': p1_id,
                    'Participant_2': p2_id,
                    'Metric': metric,
                    'Pearson_r': r,
                    'p_value': p,
                    'N': len(temp)
                })
    
    return pd.DataFrame(results_ms), pd.DataFrame(results_hz)

def analyze_intra_method():
    motr_participants = load_all_participants(PATH_MOTR_FOLDER)
    et_participants = load_all_participants(PATH_ET_FOLDER)
    
    if not motr_participants or not et_participants:
        print("Missing MoTR or ET data.")
        return
    
    # Map participant IDs to 1, 2, 3... for MoTR
    motr_ids = sorted(list(motr_participants.keys()), key=lambda x: int(x) if x.isdigit() else x)
    motr_map = {pid: i + 1 for i, pid in enumerate(motr_ids)}
    
    # Map participant IDs to 1, 2, 3... for ET
    et_ids = sorted(list(et_participants.keys()), key=lambda x: int(x) if x.isdigit() else x)
    et_map = {pid: i + 1 for i, pid in enumerate(et_ids)}

    motr_results_ms, motr_results_hz = compute_pairwise_correlations(motr_participants, 'MoTR')
    et_results_ms, et_results_hz = compute_pairwise_correlations(et_participants, 'ET')
    
    # Apply Mapping
    for df in [motr_results_ms, motr_results_hz]:
        if not df.empty:
            df['Participant_1'] = df['Participant_1'].map(motr_map)
            df['Participant_2'] = df['Participant_2'].map(motr_map)
            
    for df in [et_results_ms, et_results_hz]:
        if not df.empty:
            df['Participant_1'] = df['Participant_1'].map(et_map)
            df['Participant_2'] = df['Participant_2'].map(et_map)

    # Save CSVs
    pd.concat([motr_results_ms, et_results_ms]).to_csv('intra_method_correlations_ms.csv', index=False)
    pd.concat([motr_results_hz, et_results_hz]).to_csv('intra_method_correlations_hz.csv', index=False)
    
    # Plotting
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Dictionary of configs for clean looping
    plots_config = [
        {'df': motr_results_ms, 'metric': 'total_duration', 'cmap': 'Blues', 'ax': axes[0, 0], 'title': 'MoTR: total_duration (MS)'},
        {'df': motr_results_hz, 'metric': 'total_duration_hz', 'cmap': 'Reds', 'ax': axes[0, 1], 'title': 'MoTR: total_duration (Hz)'},
        {'df': et_results_ms, 'metric': 'total_duration', 'cmap': 'Greens', 'ax': axes[1, 0], 'title': 'ET: total_duration (MS)'},
        {'df': et_results_hz, 'metric': 'total_duration_hz', 'cmap': 'Oranges', 'ax': axes[1, 1], 'title': 'ET: total_duration (Hz)'}
    ]

    for cfg in plots_config:
        df_metric = cfg['df'][cfg['df']['Metric'] == cfg['metric']]
        if not df_metric.empty:
            pivot = df_metric.pivot_table(index='Participant_1', columns='Participant_2', values='Pearson_r')
            sns.heatmap(pivot, cmap=cfg['cmap'], annot=True, fmt='.2f', vmin=0, vmax=1, 
                        cbar_kws={'label': 'Pearson r'}, ax=cfg['ax'])
            cfg['ax'].set_title(cfg['title'], fontweight='bold', fontsize=12)
            cfg['ax'].set_xlabel('Participant')
            cfg['ax'].set_ylabel('Participant')
            avg_r = df_metric['Pearson_r'].mean()
            cfg['ax'].text(0.5, -0.18, f'Avg r = {avg_r:.3f}', transform=cfg['ax'].transAxes, 
                           ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig('intra_method_comparison.svg', format='svg')
    print("\nSaved: intra_method_comparison.svg with numbered participants (1-9).")

if __name__ == "__main__":
    analyze_intra_method()