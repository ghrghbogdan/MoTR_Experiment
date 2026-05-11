import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import numpy as np
import glob
import os

# --- CONFIGURARE ---
# 1. Folderul unde ai cele 6 fisiere MoTR
PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/' 

# 2. Fisierul (sau folderul) cu datele Eye-Tracking
# Daca ET e tot impartit in fisiere, pune calea catre folder. 
# Daca e un singur fisier mare, lasa calea catre fisier.
PATH_ET_DATA = '/home/ASUS/MoTR/ETReadingMeasures/'

# Chei de unire (Identificarea textului)
MERGE_KEYS = ['expr_id', 'cond_id', 'para_nr', 'line_nr', 'word_nr']
METRICS = ['first_duration', 'total_duration']

def load_data_from_source(path):
    """ Functie inteligenta care incarca fie un fisier, fie un folder intreg. """
    if os.path.isfile(path):
        print(f"📄 Incarc fisier unic: {path}")
        return pd.read_csv(path, low_memory=False)
    
    elif os.path.isdir(path):
        print(f"📂 Detectat folder. Caut fisiere CSV in: {path}")
        all_files = glob.glob(os.path.join(path, "*.csv"))
        
        if not all_files:
            print("❌ Nu am gasit niciun .csv in folder!")
            return None
            
        print(f"   ➤ Am gasit {len(all_files)} fisiere. Le unesc...")
        df_list = []
        for filename in all_files:
            try:
                temp_df = pd.read_csv(filename, low_memory=False)
                df_list.append(temp_df)
            except Exception as e:
                print(f"⚠️ Eroare la fisierul {filename}: {e}")
        
        if df_list:
            big_df = pd.concat(df_list, ignore_index=True)
            print(f"   ✅ Gata! Total randuri unite: {len(big_df)}")
            return big_df
        else:
            return None
    else:
        print(f"❌ Calea nu exista: {path}")
        return None

def analyze_pooled_word_length():
    print("🚀 Start Analiză Agregată (Pooling 6 Participanți)...")

    # 1. Incarcam MoTR (din folder)
    df_motr = load_data_from_source(PATH_MOTR_FOLDER)
    if df_motr is None: return

    # 2. Incarcam ET (fisier sau folder)
    df_et = load_data_from_source(PATH_ET_DATA)
    if df_et is None: return

    # 3. Calcul Lungime Cuvant (pe dataset-ul mare)
    print("📏 Calculam lungimea cuvintelor...")
    for df in [df_motr, df_et]:
        word_col = next((c for c in ['word', 'Word', 'text', 'Text'] if c in df.columns), None)
        if word_col:
            df['word_len'] = df[word_col].astype(str).apply(lambda x: len(x.strip('.,;:!? "()')))

    # 4. PREGATIRE PENTRU MERGE
    # Aici e trucul: Avem multi participanti MoTR si (poate) multi ET.
    # Nu putem face merge direct pe SubjectID ca nu corespund.
    # Facem merge PE TEXT.
    # Asta inseamna ca pentru cuvantul "X" vom avea o multiplicare a randurilor (Multi-to-Multi join).
    # E PERFECT pentru ce ne trebuie noua (Confidence Interval).
    
    for df in [df_motr, df_et]:
        for k in MERGE_KEYS:
            if k in df.columns:
                df[k] = pd.to_numeric(df[k], errors='coerce').fillna(-1).astype(int)

    print("🔗 Unificam seturile de date (Join pe structura textului)...")
    merged = pd.merge(df_motr, df_et, on=MERGE_KEYS, how='inner', suffixes=('_motr', '_et'))
    
    # Rezolvam word_len
    if 'word_len_et' in merged.columns: merged['word_len'] = merged['word_len_et']
    elif 'word_len_motr' in merged.columns: merged['word_len'] = merged['word_len_motr']
    
    print(f"✅ Dataset Final: {len(merged)} puncte de date comparabile.")
    
    # 5. VIZUALIZARE
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    sns.set_style("whitegrid")

    for i, metric in enumerate(METRICS):
        ax = axes[i]
        col_motr = f"{metric}_motr"
        col_et = f"{metric}_et"

        # Filtram date valide (fara skips, lungimi normale)
        subset = merged[
            (merged['word_len'] >= 3) & 
            (merged['word_len'] <= 15) & 
            (merged[col_motr] > 0) & 
            (merged[col_et] > 0)
        ].copy()

        # Calculam statistici pentru titlu
        grouped = subset.groupby('word_len')[[col_motr, col_et]].mean().reset_index()
        if len(grouped) > 2:
            r, p = stats.pearsonr(grouped[col_motr], grouped[col_et])
            signif = "***" if p < 0.001 else "**" if p < 0.01 else "*"
            title = f"{metric}\nr = {r:.2f} ({signif})"
        else:
            title = metric

        # Desenam cu Confidence Interval (umbra)
        color_et = 'tab:blue'
        ax.set_xlabel('Word Length', fontsize=12)
        ax.set_ylabel(f'ET {metric} (ms)', color=color_et, fontsize=12)
        
        # Lineplot foloseste automat toate datele celor 6 oameni pt a calcula CI
        sns.lineplot(data=subset, x='word_len', y=col_et, ax=ax, color=color_et, marker='o', label='Eye-Tracking')
        ax.tick_params(axis='y', labelcolor=color_et)
        ax.grid(True, linestyle='--', alpha=0.5)

        ax2 = ax.twinx()
        color_motr = 'tab:orange'
        ax2.set_ylabel(f'MoTR {metric} (ms)', color=color_motr, fontsize=12)
        
        sns.lineplot(data=subset, x='word_len', y=col_motr, ax=ax2, color=color_motr, marker='s', linestyle='--', label='MoTR')
        ax2.tick_params(axis='y', labelcolor=color_motr)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Legenda
        lines_1, labels_1 = ax.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax.legend(lines_1 + lines_2, ['Eye-Tracking', 'MoTR'], loc='upper left')
        ax2.get_legend().remove()

    plt.tight_layout()
    plt.savefig('pooled_analysis_results.svg', format='svg')
    print("\n🖼️ Grafic generat: pooled_analysis_results.svg")

if __name__ == "__main__":
    analyze_pooled_word_length()