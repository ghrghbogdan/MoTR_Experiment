import pandas as pd
import numpy as np
import glob
import os
import wordfreq
import pyphen
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

MODEL_SAVE_DIR = '/home/ASUS/MoTR/REG/saved_models/'
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

PATH_MOTR_FOLDER = '/home/ASUS/MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = '/home/ASUS/MoTR/ETReadingMeasures/'

COL_MOTR_DUR = 'total_duration'
COL_ET_DUR = 'total_duration'

MIN_DURATION_MS = 50.0
MAX_DURATION_MS = 4000.0

dic = pyphen.Pyphen(lang='ro')

def compute_rich_features(df, text_col='word'):
    df['word_clean'] = df[text_col].astype(str)

    def get_zipf(w): return wordfreq.zipf_frequency(str(w).lower(), 'ro')
    def get_len(w): return len(str(w).strip(".,!?;:\"'()"))
    def get_syl(w):
        try: return len(dic.inserted(str(w).lower()).split('-'))
        except: return 1

    df['freq'] = df['word_clean'].apply(get_zipf)
    df['len'] = df['word_clean'].apply(get_len)
    df['syl'] = df['word_clean'].apply(get_syl)

    DEFAULT_FREQ = 8.0; DEFAULT_LEN = 0.0
    
    df['prev_freq'] = df['freq'].shift(1).fillna(DEFAULT_FREQ)
    df['prev_len']  = df['len'].shift(1).fillna(DEFAULT_LEN)
    df['prev2_freq'] = df['freq'].shift(2).fillna(DEFAULT_FREQ)
    df['prev2_len']  = df['len'].shift(2).fillna(DEFAULT_LEN)
    df['next_freq'] = df['freq'].shift(-1).fillna(DEFAULT_FREQ)
    df['next_len']  = df['len'].shift(-1).fillna(DEFAULT_LEN)

    if 'para_nr' in df.columns:
        df['rel_pos'] = df.groupby('para_nr').cumcount() / df.groupby('para_nr')['word_clean'].transform('count')
    else:
        df['rel_pos'] = 0.5

    feat_cols = ['freq', 'len', 'syl', 'prev_freq', 'prev_len', 'prev2_freq', 'prev2_len', 'next_freq', 'next_len', 'rel_pos']
    df = df.dropna(subset=feat_cols)
    return df, feat_cols

def load_dataset(folder_path, duration_col_name, label="Dataset"):
    all_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))
    if not all_files:
        return None, None

    df = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)

    if 'word' not in df.columns and 'Word' in df.columns: df.rename(columns={'Word': 'word'}, inplace=True)

    if duration_col_name not in df.columns:
        return None, None
    df['target'] = pd.to_numeric(df[duration_col_name], errors='coerce')
    df = df[(df['target'] > MIN_DURATION_MS) & (df['target'] < MAX_DURATION_MS)].copy()

    sort_keys = [k for k in ['expr_id', 'participant_id', 'para_nr', 'sentence_id', 'word_nr', 'word_id'] if k in df.columns]
    if sort_keys:
        for k in sort_keys: df[k] = pd.to_numeric(df[k], errors='coerce').fillna(-1)
        df = df.sort_values(sort_keys).reset_index(drop=True)

    df, feat_cols = compute_rich_features(df)
    return df, feat_cols

def run_experiment(train_df, test_df, features, title, ax, model_name=None):
    
    X_train = train_df[features].values
    y_train = train_df['target'].values
    X_test = test_df[features].values
    y_test = test_df['target'].values

    model = RandomForestRegressor(
        n_estimators=100,
        min_samples_leaf=10,
        n_jobs=-1,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if model_name:
        model_path = os.path.join(MODEL_SAVE_DIR, f"{model_name}.pkl")
        joblib.dump(model, model_path)

    r, _ = pearsonr(y_test, y_pred)
    rho, _ = spearmanr(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    idx = np.random.choice(len(y_test), min(2000, len(y_test)), replace=False)
    sns.scatterplot(x=y_test[idx], y=y_pred[idx], alpha=0.15, ax=ax, color='blue')
    sns.regplot(x=y_test[idx], y=y_pred[idx], scatter=False, ax=ax, color='red', label=f'r={r:.2f}')
    
    ax.set_title(f"{title}\nrho={rho:.2f} | MAE={mae:.0f}ms")
    ax.set_xlabel("Real Duration (ms)")
    ax.set_ylabel("Predicted Duration (ms)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 2000)
    ax.set_ylim(0, 2000)

def compare_all():
    df_motr, feats = load_dataset(PATH_MOTR_FOLDER, COL_MOTR_DUR, "MoTR Data")
    if df_motr is None: return

    motr_train, motr_test = train_test_split(df_motr, test_size=0.2, random_state=42)

    df_et, _ = load_dataset(PATH_ET_FOLDER, COL_ET_DUR, "Eye-Tracking Data")

    if df_et is None:
        df_et = motr_test.copy()

    et_train, et_test = train_test_split(df_et, test_size=0.2, random_state=42)

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    plt.subplots_adjust(hspace=0.3, wspace=0.3)

    run_experiment(motr_train, motr_test, feats, "1. Train MoTR -> Test MoTR", axes[0, 0],
                   model_name="rf_motr_to_motr_ms")
    run_experiment(et_train, et_test, feats, "2. Train ET -> Test ET", axes[1, 1],
                   model_name="rf_et_to_et_ms")
    run_experiment(df_motr, df_et, feats, "3. Train MoTR -> Test ET (Cross-Modal)", axes[0, 1],
                   model_name="rf_motr_to_et_cross_ms")
    run_experiment(df_et, df_motr, feats, "4. Train ET -> Test MoTR (Cross-Modal)", axes[1, 0],
                   model_name="rf_et_to_motr_cross_ms")

    plt.suptitle("Universal Psycholinguistic Validation: MoTR vs Eye-Tracking", fontsize=16)
    plt.savefig("comparison_matrix.svg", format='svg')

if __name__ == "__main__":
    compare_all()