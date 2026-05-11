import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import glob
import os

# --- CONFIGURARE ---
FOLDER_ET = '/home/ASUS/MoTR/ETReadingMeasures/' 
FOLDER_MOTR = '/home/ASUS/MoTR/MoTRReadingMeasures/'

# Coloanele care indica Fixatie si Regresie (0 sau 1)
# Asigura-te ca ai aceste coloane in CSV-uri. 
# Daca ai doar durate, scriptul le va converti automat (durata > 0 -> 1).
COL_FIX = 'FPFix'       # First Pass Fixation (1=Fixat, 0=Skip)
COL_REG = 'RegIn_incl'  # Regression In (1=Re-citit, 0=Nu)

def load_and_combine_files(folder_path):
    """Încarcă toate fișierele CSV dintr-un folder și le combină."""
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    df_list = []
    
    for file in all_files:
        try:
            df = pd.read_csv(file, low_memory=False)
            df_list.append(df)
            print(f"  ✓ Încarcat: {os.path.basename(file)} ({len(df)} rânduri)")
        except Exception as e:
            print(f"  ✗ Eroare la {os.path.basename(file)}: {e}")
    
    if df_list:
        combined = pd.concat(df_list, ignore_index=True)
        return combined
    return pd.DataFrame()

def analyze_global_rates():
    print("🚀 Analiza Globala: Rate de Fixare si Regresie...")

    # 1. Incarcare Date
    try:
        print("\n📂 Încărcare fișiere MoTR...")
        df_motr = load_and_combine_files(FOLDER_MOTR)
        
        print("\n📂 Încărcare fișiere ET...")
        df_et = load_and_combine_files(FOLDER_ET)
        
        print(f"\n📊 Date combinate: MoTR={len(df_motr)} rânduri, ET={len(df_et)} rânduri.")
    except Exception as e:
        print(f"❌ Eroare fisiere: {e}")
        return

    stats_list = []

    # 2. Procesare pentru fiecare metoda
    for name, df in [('MoTR', df_motr), ('Eye-Tracking', df_et)]:
        print(f"\n--- Procesare {name} ---")
        
        # A. CALCUL RATA FIXARE (Fixations / Total Words)
        if COL_FIX in df.columns:
            # Daca coloana e binara (0/1), media = procentul
            fix_rate = df[COL_FIX].mean() * 100
        elif 'first_duration' in df.columns:
            # Daca nu avem FPFix, o deducem din durata: daca durata > 0 inseamna ca a fost fixat
            fix_rate = (df['first_duration'] > 0).mean() * 100
        else:
            print(f"⚠️ Nu gasesc coloana pentru fixatii in {name}")
            fix_rate = 0

        # B. CALCUL RATA REGRESIE (Regressions / Total Words)
        if COL_REG in df.columns:
            reg_rate = df[COL_REG].mean() * 100
        elif 'RegIn_excl' in df.columns:
            reg_rate = df['RegIn_excl'].mean() * 100
        elif 'FPReg' in df.columns:
            reg_rate = df['FPReg'].mean() * 100
        else:
            print(f"⚠️ Nu gasesc coloana pentru regresii in {name}")
            reg_rate = 0

        print(f"   ➤ Fixation Rate: {fix_rate:.2f}%")
        print(f"   ➤ Regression Rate: {reg_rate:.2f}%")

        stats_list.append({'Method': name, 'Metric': 'Fixation Rate (%)', 'Value': fix_rate})
        stats_list.append({'Method': name, 'Metric': 'Regression Rate (%)', 'Value': reg_rate})

    # 3. Vizualizare Comparativa
    df_stats = pd.DataFrame(stats_list)

    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    # Setează dimensiuni mai mari pentru font
    plt.rcParams.update({'font.size': 16})

    # Barplot Grupat
    ax = sns.barplot(
        data=df_stats, 
        x='Metric', 
        y='Value', 
        hue='Method', 
        palette={'MoTR': 'tab:orange', 'Eye-Tracking': 'tab:blue'},
        edgecolor='black'
    )

    # Adaugam valorile pe bare
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3, fontweight='bold', fontsize=16)

    plt.title("Global Comparison: Reading Behavior (MoTR vs ET)", fontsize=20, fontweight='bold')
    plt.ylabel("Percentage (%)", fontsize=18)
    plt.xlabel("", fontsize=18)
    ax.tick_params(labelsize=16)
    plt.ylim(0, 100) # Fixam axa Y la 100%
    plt.legend(title='Method', fontsize=16, title_fontsize=16)
    
    plt.tight_layout()
    plt.savefig('global_rates_comparison.svg', dpi=300)
    print("\n🖼️ Grafic salvat: global_rates_comparison.png")

    # Interpretare automata
    motr_fix = df_stats[(df_stats['Method']=='MoTR') & (df_stats['Metric']=='Fixation Rate (%)')]['Value'].values[0]
    et_fix = df_stats[(df_stats['Method']=='Eye-Tracking') & (df_stats['Metric']=='Fixation Rate (%)')]['Value'].values[0]
    
    diff = abs(motr_fix - et_fix)
    print("\n--- CONCLUZIE ---")
    if diff < 10:
        print(f"✅ EXCELENT! Diferenta de strategie e mica ({diff:.1f}%). MoTR induce un comportament natural.")
    else:
        print(f"⚠️ NOTA: Exista o diferenta de strategie ({diff:.1f}%). Posibil ca una din metode sa fie mai solicitanta.")

if __name__ == "__main__":
    analyze_global_rates()