import pandas as pd
import numpy as np
import glob
import os
import wordfreq
import pyphen
import joblib
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from sklearn.decomposition import PCA

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

BERT_MODEL_NAME = "bert-base-multilingual-cased"
BATCH_SIZE = 64
PATH_MOTR_DATA = '/home/ASUS/MoTR/MoTRReadingMeasures/'
PATH_ET_DATA = '/home/ASUS/MoTR/ETReadingMeasures/'
MODEL_SAVE_DIR = '/home/ASUS/MoTR/RIDGEREG/saved_models/'

TARGET_PARA_NR = 8
MIN_DURATION_MS = 50.0
MAX_DURATION_MS = 4000.0

dic = pyphen.Pyphen(lang='ro')

MODELS_CONFIG = {
    'rf_motr_to_motr_ms': {'label': 'RF MoTR->MoTR (ms)', 'color': 'tomato', 'type': 'simple'},
    'rf_motr_to_motr_hz': {'label': 'RF MoTR→MoTR (Hz)', 'color': 'red', 'type': 'simple'},
    'rf_et_to_et_ms': {'label': 'RF ET→ET (ms)', 'color': 'dodgerblue', 'type': 'simple'},
    'rf_et_to_et_hz': {'label': 'RF ET→ET (Hz)', 'color': 'blue', 'type': 'simple'},
    'rf_motr_to_et_cross_ms': {'label': 'RF MoTR→ET Cross (ms)', 'color': 'orange', 'type': 'simple'},
    'rf_motr_to_et_cross_hz': {'label': 'RF MoTR→ET Cross (Hz)', 'color': 'darkorange', 'type': 'simple'},
    'rf_et_to_motr_cross_ms': {'label': 'RF ET→MoTR Cross (ms)', 'color': 'purple', 'type': 'simple'},
    'rf_et_to_motr_cross_hz': {'label': 'RF ET→MoTR Cross (Hz)', 'color': 'darkviolet', 'type': 'simple'},
    # Modele Fusion (BERT + Ling)
    'rf_fusion_motr_to_motr_ms': {'label': 'Fusion MoTR->MoTR (ms)', 'color': 'crimson', 'type': 'fusion'},
    'rf_fusion_motr_to_motr_hz': {'label': 'Fusion MoTR->MoTR (Hz)', 'color': 'darkred', 'type': 'fusion'},
    'rf_fusion_et_to_et_ms': {'label': 'Fusion ET->ET (ms)', 'color': 'deepskyblue', 'type': 'fusion'},
    'rf_fusion_et_to_et_hz': {'label': 'Fusion ET->ET (Hz)', 'color': 'darkblue', 'type': 'fusion'},
    'rf_fusion_motr_to_et_cross_ms': {'label': 'Fusion MoTR->ET Cross (ms)', 'color': 'gold', 'type': 'fusion'},
    'rf_fusion_motr_to_et_cross_hz': {'label': 'Fusion MoTR->ET Cross (Hz)', 'color': 'goldenrod', 'type': 'fusion'},
    'rf_fusion_et_to_motr_cross_ms': {'label': 'Fusion ET->MoTR Cross (ms)', 'color': 'orchid', 'type': 'fusion'},
    'rf_fusion_et_to_motr_cross_hz': {'label': 'Fusion ET->MoTR Cross (Hz)', 'color': 'mediumvioletred', 'type': 'fusion'},
}

def compute_features_for_prediction(df):
    df = df.copy()
    df['word_clean'] = df['word'].astype(str)
    
    def get_zipf(w): return wordfreq.zipf_frequency(str(w).lower(), 'ro')
    def get_len(w): return len(str(w).strip(".,!?;:\"'()"))
    def get_syl(w): 
        try: return len(dic.inserted(str(w).lower()).split('-'))
        except: return 1

    unique_words = df['word_clean'].unique()
    feats_lookup = {w: (get_zipf(w), get_len(w), get_syl(w)) for w in unique_words}
    
    df['freq'] = df['word_clean'].map(lambda x: feats_lookup[x][0])
    df['len'] = df['word_clean'].map(lambda x: feats_lookup[x][1])
    df['syl'] = df['word_clean'].map(lambda x: feats_lookup[x][2])
    
    DEFAULT_FREQ = 8.0; DEFAULT_LEN = 0.0
    
    df['prev_freq'] = df['freq'].shift(1).fillna(DEFAULT_FREQ)
    df['prev_len'] = df['len'].shift(1).fillna(DEFAULT_LEN)
    df['prev2_freq'] = df['freq'].shift(2).fillna(DEFAULT_FREQ)
    df['prev2_len'] = df['len'].shift(2).fillna(DEFAULT_LEN)
    df['next_freq'] = df['freq'].shift(-1).fillna(DEFAULT_FREQ)
    df['next_len'] = df['len'].shift(-1).fillna(DEFAULT_LEN)
    
    if 'para_nr' in df.columns:
        df['rel_pos'] = df.groupby('para_nr').cumcount() / (df.groupby('para_nr')['word_clean'].transform('count') + 1)
    else:
        df['rel_pos'] = 0.5
        
    feat_cols = ['freq', 'len', 'syl', 'prev_freq', 'prev_len', 'prev2_freq', 'prev2_len', 'next_freq', 'next_len', 'rel_pos']
    return df, feat_cols

def get_raw_rows(folder_path, para_nr):
    all_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))
    
    df_all = pd.concat((pd.read_csv(f, low_memory=False) for f in all_files), ignore_index=True)
    
    if 'word' not in df_all.columns and 'Word' in df_all.columns: 
        df_all.rename(columns={'Word': 'word'}, inplace=True)
    if 'para_nr' not in df_all.columns and 'Paragraph' in df_all.columns: 
        df_all.rename(columns={'Paragraph': 'para_nr'}, inplace=True)
    
    df_all['para_nr'] = pd.to_numeric(df_all['para_nr'], errors='coerce').fillna(-1).astype(int)
    df_para = df_all[df_all['para_nr'] == para_nr].copy()
    
    keys = ['expr_id', 'para_nr', 'word_nr']
    for k in keys: 
        if k in df_para.columns:
            df_para[k] = pd.to_numeric(df_para[k], errors='coerce').fillna(-1).astype(int)

    df_means = df_para.groupby(['para_nr', 'word_nr', 'word'], sort=False)['total_duration'].mean().reset_index()
    return df_means

def prepare_solaris_data():
    df_motr = get_raw_rows(PATH_MOTR_DATA, TARGET_PARA_NR)
    df_et = get_raw_rows(PATH_ET_DATA, TARGET_PARA_NR)

    if len(df_motr) == len(df_et):
        df_motr = df_motr.reset_index(drop=True)
        df_et = df_et.reset_index(drop=True)
        df_merged = pd.merge(df_motr, df_et, left_index=True, right_index=True, suffixes=('_motr', '_et'))
        df_merged['word'] = df_merged['word_motr']
        df_merged['word_nr'] = df_merged['word_nr_motr']
        df_merged['para_nr'] = df_merged['para_nr_motr']
    else:
        df_merged = pd.merge(df_motr, df_et, on=['para_nr', 'word_nr', 'word'], how='inner', suffixes=('_motr', '_et'))

    df_merged['gt_motr_sec'] = df_merged['total_duration_motr'] / 1000.0
    df_merged['gt_et_sec'] = df_merged['total_duration_et'] / 1000.0

    df_merged.loc[df_merged['total_duration_motr'] < MIN_DURATION_MS, 'gt_motr_sec'] = np.nan
    df_merged.loc[df_merged['total_duration_et'] < MIN_DURATION_MS, 'gt_et_sec'] = np.nan
    
    return df_merged

def split_into_sentences(df_merged):
    sentences = []
    curr_indices = []
    
    for idx, row in df_merged.iterrows():
        w = str(row['word']).strip()
        curr_indices.append(idx)
        
        if w.endswith('.') or w.endswith('?') or w.endswith('!'):
            if len(curr_indices) > 0:
                sentences.append(curr_indices.copy())
            curr_indices = []
    
    if len(curr_indices) > 0:
        sentences.append(curr_indices)
    return sentences

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
    tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL_NAME)
    model = AutoModel.from_pretrained(BERT_MODEL_NAME).to(DEVICE)
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

def load_available_models():
    loaded_models = {}
    
    for model_name, config in MODELS_CONFIG.items():
        model_path = os.path.join(MODEL_SAVE_DIR, f"{model_name}.pkl")
        if os.path.exists(model_path):
            try:
                loaded_models[model_name] = {
                    'model': joblib.load(model_path),
                    **config
                }
                print(f"   ✅ Loaded: {model_name}")
            except Exception as e:
                print(f"   ❌ Failed to load {model_name}: {e}")
        else:
            print(f"   ⚠️ Not found: {model_name}")
    
    return loaded_models

def predict_with_model(model, X, model_name):
    pred = model.predict(X)

    if '_hz' in model_name:
        pred = np.clip(pred, 0.1, 20.0)
        pred = 1.0 / pred
    else:
        pred = pred / 1000.0
    return pred

def create_visualization():
    df_merged = prepare_solaris_data()
    sentences = split_into_sentences(df_merged)
    
    # 2. Compute features
    print("\n📊 Computing linguistic features...")
    df_merged, feat_cols = compute_features_for_prediction(df_merged)
    
    # 3. Load models
    print("\n🤖 Loading RF models...")
    models = load_available_models()
    
    if not models:
        print("❌ No models found!")
        return
    
    # 4. Generate predictions for all models
    print("\n🔮 Generating predictions...")
    X_ling = df_merged[feat_cols].values
    
    # Compute BERT features pentru modelele fusion
    print("\n🧠 Computing BERT features for fusion models...")
    X_bert = get_bert_pca_features(df_merged)
    X_fusion = np.hstack([X_ling, X_bert])

    predictions = {}
    for model_name, model_data in models.items():
        try:
            # Alegem features-urile corecte
            if 'fusion' in model_name:
                X = X_fusion
            else:
                X = X_ling
            
            pred = predict_with_model(model_data['model'], X, model_name)
            predictions[model_name] = pred
            print(f"   ✅ Predicted: {model_name}")
        except Exception as e:
            print(f"   ❌ Prediction failed for {model_name}: {e}")
    
    # 5. Create Plotly figure with dropdown
    print("\n🎨 Creating Plotly visualization...")
    
    fig = go.Figure()
    
    # Definim culorile pentru ground truth
    GT_COLORS = {
        'gt_motr': 'darkred',
        'gt_et': 'darkblue'
    }
    
    # Pentru fiecare propoziție, adăugăm trace-uri
    for sent_idx, word_indices in enumerate(sentences):
        vis = True if sent_idx == 0 else False
        
        sent_df = df_merged.loc[word_indices]
        words = sent_df['word'].tolist()
        x_indices = list(range(len(words)))
        
        # Ground Truth MoTR
        fig.add_trace(go.Scatter(
            x=x_indices, 
            y=sent_df['gt_motr_sec'].tolist(),
            mode='lines+markers',
            name='Actual MoTR',
            line=dict(color=GT_COLORS['gt_motr'], width=3),
            marker=dict(size=10, symbol='circle'),
            visible=vis,
            customdata=words,
            hovertemplate='<b>%{customdata}</b><br>MoTR Real: %{y:.3f}s<extra></extra>',
            legendgroup='ground_truth'
        ))
        
        # Ground Truth ET
        fig.add_trace(go.Scatter(
            x=x_indices,
            y=sent_df['gt_et_sec'].tolist(),
            mode='lines+markers',
            name='Actual ET',
            line=dict(color=GT_COLORS['gt_et'], width=3),
            marker=dict(size=10, symbol='circle'),
            visible=vis,
            customdata=words,
            hovertemplate='<b>%{customdata}</b><br>ET Real: %{y:.3f}s<extra></extra>',
            legendgroup='ground_truth'
        ))
        
        # Predictions pentru fiecare model
        for model_name, pred_values in predictions.items():
            config = MODELS_CONFIG[model_name]
            sent_preds = pred_values[word_indices]
            
            # Determinăm stilul liniei
            dash_style = 'dot' if 'cross' in model_name else 'dash'
            
            fig.add_trace(go.Scatter(
                x=x_indices,
                y=sent_preds,
                mode='lines+markers',
                name=config['label'],
                line=dict(color=config['color'], width=2, dash=dash_style),
                marker=dict(size=6, symbol='diamond'),
                visible=vis,
                customdata=words,
                hovertemplate=f'{config["label"]}: %{{y:.3f}}s<extra></extra>',
                legendgroup=model_name
            ))
    
    # Calculăm câte trace-uri avem per propoziție
    num_models = len(predictions)
    traces_per_sentence = 2 + num_models  # 2 GT + predictions
    
    # Creăm butoanele dropdown
    buttons = []
    for sent_idx, word_indices in enumerate(sentences):
        visibility = [False] * (len(sentences) * traces_per_sentence)
        
        # Activăm trace-urile pentru această propoziție
        start_trace = sent_idx * traces_per_sentence
        for i in range(traces_per_sentence):
            visibility[start_trace + i] = True
        
        sent_df = df_merged.loc[word_indices]
        words = sent_df['word'].tolist()
        preview = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
        
        button = dict(
            label=f"Sent {sent_idx + 1}",
            method="update",
            args=[
                {"visible": visibility},
                {
                    "title": f"Sentence {sent_idx + 1}: {preview}",
                    "xaxis": {
                        "tickvals": list(range(len(words))),
                        "ticktext": words,
                        "title": "Word Sequence"
                    }
                }
            ]
        )
        buttons.append(button)
    
    # Setup inițial pentru prima propoziție
    first_words = df_merged.loc[sentences[0]]['word'].tolist() if sentences else []
    
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                x=0.0,
                xanchor="left",
                y=1.18,
                yanchor="top",
                direction="down",
                showactive=True
            )
        ],
        title=dict(
            text=f"🪐 Solaris Analysis - RF Models Comparison<br><sub>Paragraph {TARGET_PARA_NR} | {len(predictions)} models loaded</sub>",
            x=0.5
        ),
        xaxis=dict(
            tickvals=list(range(len(first_words))),
            ticktext=first_words,
            title="Word Sequence",
            tickangle=45
        ),
        yaxis=dict(
            title="Duration (seconds)",
            rangemode='tozero'
        ),
        template='plotly_white',
        hovermode='x unified',
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=150)
    )
    
    # Salvăm
    output_file = "solaris_rf_models_comparison.html"
    fig.write_html(output_file)

if __name__ == "__main__":
    create_visualization()
