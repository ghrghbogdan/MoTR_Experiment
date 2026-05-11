import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = '/home/ASUS/MoTR/ETReadingMeasures/'

TIME_METRICS = ['total_duration']

def ms_to_hz(ms_val):
    if pd.isna(ms_val) or ms_val <= 0:
        return np.nan
    return 1000.0 / ms_val

def load_all_data(folder_path, method_name):
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    all_data = []
    
    for f in all_files:
        df = pd.read_csv(f, low_memory=False)
        df['method'] = method_name
        df['participant'] = os.path.basename(f)
        all_data.append(df)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        return combined
    return pd.DataFrame()

def prepare_data_for_distribution(df):
    for metric in TIME_METRICS:
        if metric in df.columns:
            df[f"{metric}_hz"] = df[metric].apply(ms_to_hz)
    return df

def plot_distributions():
    # Încarcă datele
    motr_data = load_all_data(PATH_MOTR_FOLDER, 'MoTR')
    et_data = load_all_data(PATH_ET_FOLDER, 'ET')
    
    if motr_data.empty or et_data.empty:
        print("Nu s-au găsit date suficiente!")
        return
    
    # Pregătește datele
    motr_data = prepare_data_for_distribution(motr_data)
    et_data = prepare_data_for_distribution(et_data)
    
    # Combină pentru vizualizare
    all_data = pd.concat([motr_data, et_data], ignore_index=True)
    
    print(f"MoTR: {len(motr_data)} observații")
    print(f"ET: {len(et_data)} observații")
    
    # Creează figura cu doar 2 violin plots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = {'MoTR': '#3498db', 'ET': '#e74c3c'}
    
    # Setează dimensiuni mai mari pentru font
    plt.rcParams.update({'font.size': 16})
    
    for idx, metric in enumerate(TIME_METRICS):
        # MS - Violin plot
        ax_violin_ms = axes[0]
        data_for_violin_ms = []
        for method in ['MoTR', 'ET']:
            data = all_data[all_data['method'] == method][metric].dropna()
            q99 = data.quantile(0.99)
            data_filtered = data[data <= q99]
            df_temp = pd.DataFrame({
                'value': data_filtered,
                'method': method
            })
            data_for_violin_ms.append(df_temp)
        
        if data_for_violin_ms:
            df_violin_ms = pd.concat(data_for_violin_ms, ignore_index=True)
            sns.violinplot(data=df_violin_ms, x='method', y='value', ax=ax_violin_ms, palette=colors)
            ax_violin_ms.set_xlabel('Method', fontsize=18, fontweight='bold')
            ax_violin_ms.set_ylabel(f'{metric} (ms)', fontsize=18, fontweight='bold')
            ax_violin_ms.set_title(f'Violin Plot: {metric} (MS)', fontsize=20, fontweight='bold')
            ax_violin_ms.tick_params(labelsize=16)
            ax_violin_ms.grid(True, alpha=0.3, axis='y')
            
            # Adaugă statistici
            for method in ['MoTR', 'ET']:
                data = all_data[all_data['method'] == method][metric].dropna()
                print(f"\n{method} - {metric} (MS):")
                print(f"  Mean: {data.mean():.2f}")
                print(f"  Median: {data.median():.2f}")
                print(f"  Std: {data.std():.2f}")
                print(f"  Min: {data.min():.2f}")
                print(f"  Max: {data.max():.2f}")
        
        # Hz - Violin plot
        metric_hz = f"{metric}_hz"
        ax_violin_hz = axes[1]
        data_for_violin_hz = []
        for method in ['MoTR', 'ET']:
            data = all_data[all_data['method'] == method][metric_hz].dropna()
            data = data[(data > 0) & (data < 100)]
            df_temp = pd.DataFrame({
                'value': data,
                'method': method
            })
            data_for_violin_hz.append(df_temp)
        
        if data_for_violin_hz:
            df_violin_hz = pd.concat(data_for_violin_hz, ignore_index=True)
            sns.violinplot(data=df_violin_hz, x='method', y='value', ax=ax_violin_hz, palette=colors)
            ax_violin_hz.set_xlabel('Method', fontsize=18, fontweight='bold')
            ax_violin_hz.set_ylabel(f'{metric} (Hz)', fontsize=18, fontweight='bold')
            ax_violin_hz.set_title(f'Violin Plot: {metric} (Hz)', fontsize=20, fontweight='bold')
            ax_violin_hz.tick_params(labelsize=16)
            ax_violin_hz.grid(True, alpha=0.3, axis='y')
            
            # Adaugă statistici
            for method in ['MoTR', 'ET']:
                data = all_data[all_data['method'] == method][metric_hz].dropna()
                data = data[(data > 0) & (data < 100)]
                print(f"\n{method} - {metric} (Hz):")
                print(f"  Mean: {data.mean():.2f}")
                print(f"  Median: {data.median():.2f}")
                print(f"  Std: {data.std():.2f}")
                print(f"  Min: {data.min():.2f}")
                print(f"  Max: {data.max():.2f}")
    
    plt.tight_layout()
    plt.savefig('distribution_violin.svg', format='svg', dpi=300)
    print("\n✓ Saved: distribution_violin.svg")

if __name__ == "__main__":
    plot_distributions()
