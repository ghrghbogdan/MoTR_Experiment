import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
import glob
import os
import wordfreq
import pyphen
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

MODEL_SAVE_DIR = './saved_models/'
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

PATH_MOTR_FOLDER = './MoTR/MoTRReadingMeasures/'
PATH_ET_FOLDER = './MoTR/ETReadingMeasures/'

COL_MOTR_DUR = 'total_duration'
COL_ET_DUR = 'total_duration'

MODEL_NAME = "bert-base-multilingual-cased"
MIN_DURATION_MS = 50.0
MAX_DURATION_MS = 3000.0
BATCH_SIZE = 64
dic = pyphen.Pyphen(lang='ro')

def compute_linguistic_features(df, text_col='word'):
    df['word_clean'] = df[text_col].astype(str)
    
    def get_zipf(w): return wordfreq.zipf_frequency(str(w).lower(), 'ro')
    def get_len(w): return len(str(w).strip(".,!?;:\"'()"))
    def get_syl(w):
        try: return len(dic.inserted(str(w).lower()).split('-'))
        except: return 1

    unique_words = df['word_clean'].unique()
    word_feats = {}
    for w in unique_words:
        word_feats[w] = [get_zipf(w), get_len(w), get_syl(w)]

    temp_feats = np.array([word_feats[w] for w in df['word_clean']])
    df['freq'] = temp_feats[:, 0]
    df['len'] = temp_feats[:, 1]
    df['syl'] = temp_feats[:, 2]

    DEFAULT_FREQ = 8.0; DEFAULT_LEN = 0.0
    
    df['prev_freq'] = df['freq'].shift(1).fillna(DEFAULT_FREQ)
    df['prev_len']  = df['len'].shift(1).fillna(DEFAULT_LEN)
    df['prev2_freq'] = df['freq'].shift(2).fillna(DEFAULT_FREQ)
    df['prev2_len']  = df['len'].shift(2).fillna(DEFAULT_LEN)
    df['next_freq'] = df['freq'].shift(-1).fillna(DEFAULT_FREQ)
    df['next_len']  = df['len'].shift(-1).fillna(DEFAULT_LEN)

    if 'para_nr' in df.columns:
        df['rel_pos'] = df.groupby('para_nr').cumcount() / (df.groupby('para_nr')['word_clean'].transform('count') + 1)
    else:
        df['rel_pos'] = 0.5

    feat_cols = ['freq', 'len', 'syl', 'prev_freq', 'prev_len', 'prev2_freq', 'prev2_len', 'next_freq', 'next_len', 'rel_pos']
    df = df.dropna(subset=feat_cols)
    return df, feat_cols

class ExtractionDataset(Dataset):
    def __init__(self, words, tokenizer, max_len=32):
        self.words = words
        self.tokenizer = tokenizer
        self.max_len = max_len
    def __len__(self): return len(self.words)
    def __getitem__(self, idx):
        word = str(self.words[idx])
        tok = self.tokenizer(word, return_tensors='pt', padding='max_length', truncation=True, max_length=self.max_len)
        return {'input_ids': tok['input_ids'].flatten(), 'attention_mask': tok['attention_mask'].flatten()}

def get_bert_pca_features(df, n_components=32):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    model.eval()
    
    unique_words = df['word_clean'].unique()
    ds = ExtractionDataset(unique_words, tokenizer)
    dl = DataLoader(ds, batch_size=BATCH_SIZE)
    
    emb_map = {}
    with torch.no_grad():
        for i, batch in enumerate(dl):
            ids = batch['input_ids'].to(DEVICE)
            mask = batch['attention_mask'].to(DEVICE)
            outputs = model(ids, mask)
            cls_emb = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            start_idx = i * BATCH_SIZE
            for j, emb in enumerate(cls_emb):
                emb_map[unique_words[start_idx + j]] = emb

    raw_embeddings = np.stack(df['word_clean'].map(emb_map).values)
    pca = PCA(n_components=n_components, random_state=42)
    reduced_embeddings = pca.fit_transform(raw_embeddings)
    return reduced_embeddings

def load_and_prep_dataset(folder, dur_col, label):
    all_files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not all_files: return None, None, None
    
    df = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)
    if 'word' not in df.columns and 'Word' in df.columns: df.rename(columns={'Word': 'word'}, inplace=True)
    
    if dur_col not in df.columns: return None, None, None
    df['target'] = pd.to_numeric(df[dur_col], errors='coerce')
    df = df[(df['target'] > MIN_DURATION_MS) & (df['target'] < MAX_DURATION_MS)].copy()

    sort_keys = [k for k in ['expr_id', 'participant_id', 'para_nr', 'word_nr'] if k in df.columns]
    if sort_keys:
        for k in sort_keys: df[k] = pd.to_numeric(df[k], errors='coerce').fillna(-1)
        df = df.sort_values(sort_keys).reset_index(drop=True)

    df, ling_cols = compute_linguistic_features(df)
    X_ling = df[ling_cols].values
    X_bert = get_bert_pca_features(df)
    X_fusion = np.hstack([X_ling, X_bert])
    y = df['target'].values
    return X_fusion, y, df

def run_experiment(X_train, y_train, X_test, y_test, title, ax, model_name=None):
    
    model = RandomForestRegressor(n_estimators=100, min_samples_leaf=10, n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if model_name:
        model_path = os.path.join(MODEL_SAVE_DIR, f"{model_name}.pkl")
        joblib.dump(model, model_path)

    r, _ = pearsonr(y_test, y_pred)
    rho, _ = spearmanr(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    idx = np.random.choice(len(y_test), min(2000, len(y_test)), replace=False)
    sns.scatterplot(x=y_test[idx], y=y_pred[idx], alpha=0.15, ax=ax, color='purple')
    sns.regplot(x=y_test[idx], y=y_pred[idx], scatter=False, ax=ax, color='yellow', label=f'rho={rho:.2f}')
    
    ax.set_title(f"{title}\nrho={rho:.2f} | MAE={mae:.0f}ms")
    ax.set_xlabel("Real"); ax.set_ylabel("Predicted")
    ax.legend()
    ax.set_xlim(0, 2000); ax.set_ylim(0, 2000)

def compare_fusion_all():
    X_motr, y_motr, _ = load_and_prep_dataset(PATH_MOTR_FOLDER, COL_MOTR_DUR, "MoTR")

    try:
        X_et, y_et, _ = load_and_prep_dataset(PATH_ET_FOLDER, COL_ET_DUR, "Eye-Tracking")
    except:
        X_et = None

    if X_motr is None: return

    X_motr_train, X_motr_test, y_motr_train, y_motr_test = train_test_split(X_motr, y_motr, test_size=0.2, random_state=42)

    if X_et is None:
        X_et_train, X_et_test, y_et_train, y_et_test = X_motr_train, X_motr_test, y_motr_train, y_motr_test
    else:
        X_et_train, X_et_test, y_et_train, y_et_test = train_test_split(X_et, y_et, test_size=0.2, random_state=42)

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    plt.subplots_adjust(hspace=0.35, wspace=0.3)

    run_experiment(X_motr_train, y_motr_train, X_motr_test, y_motr_test, "1. MoTR -> MoTR (Fusion)", axes[0,0],
                   model_name="rf_fusion_motr_to_motr_ms")
    run_experiment(X_et_train, y_et_train, X_et_test, y_et_test, "2. ET -> ET (Fusion)", axes[1,1],
                   model_name="rf_fusion_et_to_et_ms")
    run_experiment(X_motr, y_motr, X_et, y_et, "3. MoTR -> ET (Cross-Modal)", axes[0,1],
                   model_name="rf_fusion_motr_to_et_cross_ms")
    run_experiment(X_et, y_et, X_motr, y_motr, "4. ET -> MoTR (Cross-Modal)", axes[1,0],
                   model_name="rf_fusion_et_to_motr_cross_ms")

    plt.suptitle("FUSION MODEL (Ling + BERT): Universal Validation", fontsize=16)
    plt.savefig("fusion_comparison_matrix.svg", format='svg')

if __name__ == "__main__":
    compare_fusion_all()