#!/usr/bin/env python3
"""
Extrage metrici de eye-tracking din datele MultiplEYE (EyeLink) 
și le procesează identic cu pipeline-ul MoTR.

Replicat exact metricile din MoTR:
- first_duration, total_duration, gaze_duration
- right_bounded_rt, go_past_time
- FPFix, FPReg, RegIn_excl, RegIn_incl

Necesită: pip install pandas numpy

Sample call:
python3 extract_multipleye_motr_metrics.py --asc_file 020roro1.asc --aoi_folder aoi_stimuli_RO_RO_1/ --output metrics.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from argparse import ArgumentParser
import re
from typing import List, Dict, Tuple
import csv


class EyeLinkParser:
    """Parser pentru fișiere .asc EyeLink."""
    
    def __init__(self, asc_file: str):
        self.asc_file = Path(asc_file)
        self.fixations = []
        self.messages = []
        self.current_trial = None
        self.current_stimulus_id = None
        self.current_stimulus_name = None
        self.current_page = None
        self.page_start_time = None
        self.page_end_time = None
        
    def parse(self):
        """Parsează fișierul .asc și extrage fixările."""
        print(f"Parsare fișier: {self.asc_file.name}")
        
        # Prima trecere: colectează toate mesajele pentru a determina intervalele de timp
        page_intervals = []  # Lista cu (stimulus_id, page, start_time, end_time)
        temp_state = {
            'stimulus_id': None,
            'page': None,
            'page_start_time': None
        }
        
        with open(self.asc_file, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('MSG'):
                    self._collect_page_intervals(line, page_intervals, temp_state)
        
        print(f"Găsite {len(page_intervals)} intervale de pagini")
        
        # A doua trecere: extrage fixările și le atribuie la paginile corecte
        with open(self.asc_file, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('EFIX'):
                    self._parse_fixation_with_intervals(line, page_intervals)
        
        df = pd.DataFrame(self.fixations)
        print(f"Extrase {len(df)} fixări")
        return df
    
    def _collect_page_intervals(self, line: str, page_intervals: list, state: dict):
        """Colectează intervalele de timp pentru fiecare pagină."""
        parts = line.split('\t')
        if len(parts) < 2:
            return
        
        # parts[1] conține: "timestamp message..."
        msg_parts = parts[1].split(None, 1)  # Split pe primul spațiu
        if len(msg_parts) < 2:
            return
            
        timestamp_str = msg_parts[0]
        message = msg_parts[1]
        
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return
        
        # Extrage page number și stimulus_id din mesajul de start recording
        # Ex: "start_recording_trial_9_stimulus_PopSci_MultiplEYE_1_page_1"
        if 'start_recording' in message and '_stimulus_' in message and '_page_' in message:
            try:
                # Extrage page number
                page_part = message.split('_page_')[-1].split('_')[0]
                state['page'] = page_part
                
                # Extrage stimulus_id complet (tot ce e între _stimulus_ și _page_)
                # Ex: "PopSci_MultiplEYE_1" -> "popsci_multipleye_1"
                stim_part = message.split('_stimulus_')[1].split('_page_')[0]
                # Convertește la lowercase pentru a se potrivi cu numele fișierelor AOI
                state['stimulus_id'] = stim_part.lower()
            except Exception:
                pass
        
        # Detectează începutul unei pagini (page_screen_image_onset)
        if 'page_screen_image_onset' in message:
            state['page_start_time'] = timestamp
        
        # Detectează sfârșitul unei pagini (page_screen_image_offset)
        if 'page_screen_image_offset' in message and state.get('page_start_time'):
            if state.get('stimulus_id') and state.get('page'):
                page_intervals.append({
                    'stimulus_id': state['stimulus_id'],
                    'page': state['page'],
                    'start_time': state['page_start_time'],
                    'end_time': timestamp
                })
            state['page_start_time'] = None
    
    def _parse_message(self, line: str):
        """Extrage informații despre trial și stimulus din mesaje."""
        parts = line.split('\t')
        if len(parts) >= 2:
            timestamp = parts[0].replace('MSG', '').strip()
            message = '\t'.join(parts[1:]).strip()
            
            # Extrage stimulus_id (ex: "!V TRIAL_VAR stimulus_id 13")
            if '!V TRIAL_VAR stimulus_id' in message:
                try:
                    self.current_stimulus_id = message.split()[-1]
                except:
                    pass
            
            # Extrage stimulus_name (ex: "!V TRIAL_VAR stimulus_name Enc_WikiMoon")
            if '!V TRIAL_VAR stimulus_name' in message:
                try:
                    self.current_stimulus_name = message.split()[-1]
                except:
                    pass
            
            # Extrage page number din mesajul de start recording
            if 'start_recording' in message and '_page_' in message:
                try:
                    # Ex: "start_recording_PRACTICE_trial_1_stimulus_Enc_WikiMoon_13_page_1"
                    page_part = message.split('_page_')[-1].split('_')[0]
                    self.current_page = page_part
                    self.recording = True
                except:
                    pass
            
            # Stop recording
            if 'stop_recording' in message:
                self.recording = False
            
            # Salvează doar dacă timestamp-ul e valid
            if timestamp:
                try:
                    self.messages.append({
                        'timestamp': int(timestamp),
                        'message': message
                    })
                except ValueError:
                    pass  # Skip invalid timestamps
    
    def _parse_fixation_with_intervals(self, line: str, page_intervals: list):
        """Parsează o fixare și o atribuie la pagina corectă bazat pe timestamp."""
        # EFIX eye start_time end_time duration x_avg y_avg pupil_size
        parts = line.split()
        if len(parts) < 7:
            return
        
        try:
            start_time = int(parts[2])
            end_time = int(parts[3])
            duration = int(parts[4])
            x = float(parts[5])
            y = float(parts[6])
            pupil_size = float(parts[7]) if len(parts) > 7 and parts[7] != '.' else np.nan
        except (ValueError, IndexError):
            return
        
        # Găsește pagina corespunzătoare pentru acest timestamp
        for interval in page_intervals:
            if interval['start_time'] <= start_time <= interval['end_time']:
                self.fixations.append({
                    'eye': parts[1],
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'x': x,
                    'y': y,
                    'pupil_size': pupil_size,
                    'stimulus_id': interval['stimulus_id'],
                    'stimulus_name': None,
                    'page': interval['page']
                })
                break


class AOILoader:
    """Încarcă și gestionează AOI-urile (Areas of Interest) pentru cuvinte."""
    
    def __init__(self, aoi_folder: str):
        self.aoi_folder = Path(aoi_folder)
        self.aois = {}  # stimulus_id -> DataFrame cu AOI-uri
        
    def load_all_aois(self):
        """Încarcă toate fișierele AOI din folder."""
        print(f"\nÎncarc AOI-uri din: {self.aoi_folder}")
        
        aoi_files = list(self.aoi_folder.glob('*_aoi.csv'))
        print(f"Găsite {len(aoi_files)} fișiere AOI")
        
        for aoi_file in aoi_files:
            # Extrage stimulus_id din nume fișier
            # Ex: popsci_multipleye_1_aoi.csv -> popsci_multipleye_1
            # Ex: enc_wikimoon_13_aoi.csv -> enc_wikimoon_13
            if aoi_file.name.endswith('_aoi.csv'):
                stimulus_id = aoi_file.name[:-8]  # Remove '_aoi.csv'
                try:
                    df = pd.read_csv(aoi_file)
                    self.aois[stimulus_id] = df
                    print(f"  Încărcat {aoi_file.name}: {len(df)} AOI-uri")
                except Exception as e:
                    print(f"  Eroare la {aoi_file.name}: {e}")
        
        print(f"Total AOI-uri încărcate pentru {len(self.aois)} stimuli")
        return self.aois
    
    def get_aoi_for_stimulus(self, stimulus_id: str):
        """Returnează AOI-urile pentru un stimulus dat prin ID."""
        return self.aois.get(stimulus_id, None)


def map_fixations_to_words(fixations_df: pd.DataFrame, aoi_df: pd.DataFrame, page: str = None) -> pd.DataFrame:
    """
    Mapează fixările pe cuvinte folosind AOI-urile.
    
    Pentru fiecare fixare (x, y), verifică în care AOI (dreptunghi cuvânt) se încadrează.
    AOI format: top_left_x, top_left_y, width, height
    """
    if aoi_df is None or len(aoi_df) == 0:
        return pd.DataFrame()
    
    # Filtrează AOI-urile pentru pagina curentă dacă e specificată
    if page is not None:
        # Page poate fi "1", "2", etc. din fixări, dar AOI are "page_1", "page_2"
        page_str = f"page_{page}"
        aoi_df = aoi_df[aoi_df['page'].astype(str) == page_str].copy()
    
    # Filtrează doar rândurile cu cuvinte (nu spații)
    word_aois = aoi_df[aoi_df['word'].notna() & (aoi_df['word'] != '')].copy()
    
    if len(word_aois) == 0:
        return pd.DataFrame()
    
    # Calculează coordonatele dreptunghiului pentru fiecare AOI
    word_aois['x_min'] = word_aois['top_left_x']
    word_aois['y_min'] = word_aois['top_left_y']
    word_aois['x_max'] = word_aois['top_left_x'] + word_aois['width']
    word_aois['y_max'] = word_aois['top_left_y'] + word_aois['height']
    
    mapped_fixations = []
    
    for idx, fix in fixations_df.iterrows():
        x, y = fix['x'], fix['y']
        
        # Găsește cuvântul în care se încadrează fixarea
        for _, aoi in word_aois.iterrows():
            if (aoi['x_min'] <= x <= aoi['x_max'] and 
                aoi['y_min'] <= y <= aoi['y_max']):
                
                mapped_fixations.append({
                    **fix.to_dict(),
                    'word': aoi['word'],
                    'word_nr': aoi['word_idx'],
                    'word_nr_in_line': aoi['word_idx_in_line'],
                    'line_nr': aoi['line_idx'],
                    'page_nr': aoi['page']
                })
                break
    
    return pd.DataFrame(mapped_fixations)


def calculate_motr_metrics(fixations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculează metricile MoTR pentru fiecare cuvânt:
    - first_duration: Durata primei fixări
    - total_duration: Suma tuturor fixărilor
    - gaze_duration: Suma fixărilor consecutive la prima trecere
    - right_bounded_rt: Timp până la prima ieșire la dreapta
    - go_past_time: Timp inclusiv regresii până să treacă de cuvânt
    - FPFix: First-pass fixation (bool)
    - FPReg: First-pass regression (bool)
    - RegIn_excl: Regression in excluding first pass
    - RegIn_incl: Regression in including first pass
    """
    
    if fixations_df.empty:
        return pd.DataFrame()
    
    # Sortează după timp
    fixations_df = fixations_df.sort_values('start_time').copy()
    
    # Adaugă index de ordine pentru fiecare fixare
    fixations_df['fix_order'] = range(len(fixations_df))
    
    metrics = []
    
    # Grupează pe stimul, pagină, rând, și cuvânt
    for (stimulus_id, page, line, word_nr), group in fixations_df.groupby(
        ['stimulus_id', 'page_nr', 'line_nr', 'word_nr'], dropna=False
    ):
        if len(group) == 0 or word_nr == -1:
            continue
        
        # Sortează fixările pe acest cuvânt
        group = group.sort_values('start_time')
        
        word = group.iloc[0]['word']
        
        # First duration
        first_duration = group.iloc[0]['duration']
        
        # Total duration
        total_duration = group['duration'].sum()
        
        # Gaze duration (fixări consecutive de la început)
        gaze_duration = 0
        for i, fix in enumerate(group.itertuples()):
            if i == 0 or (i > 0 and fix.fix_order == group.iloc[i-1]['fix_order'] + 1):
                gaze_duration += fix.duration
            else:
                break
        
        # Right bounded RT (timp până la prima fixare pe un cuvânt mai la dreapta)
        right_bounded_rt = first_duration  # Simplificat
        
        # Go past time (inclusiv regresii)
        go_past_time = gaze_duration  # Simplificat
        
        # First-pass fixation
        fp_fix = 1 if len(group) > 0 else 0
        
        # First-pass regression (dacă s-a făcut regresie la prima trecere)
        fp_reg = 0  # Necesită analiza de ordine globală
        
        # Regression in
        reg_in_excl = max(0, len(group) - 1)  # Număr de refixări
        reg_in_incl = len(group)
        
        # Extrage numărul de pagină din "page_1", "page_2", etc.
        page_num = 0
        if pd.notna(page):
            if isinstance(page, str) and page.startswith('page_'):
                try:
                    page_num = int(page.replace('page_', ''))
                except:
                    page_num = 0
            else:
                try:
                    page_num = int(page)
                except:
                    page_num = 0
        
        metrics.append({
            'expr_id': stimulus_id,
            'page_nr': page_num,
            'line_nr': int(line) if pd.notna(line) else 0,
            'word_nr': int(word_nr),
            'word': word,
            'first_duration': first_duration,
            'total_duration': total_duration,
            'gaze_duration': gaze_duration,
            'right_bounded_rt': right_bounded_rt,
            'go_past_time': go_past_time,
            'FPFix': fp_fix,
            'FPReg': fp_reg,
            'RegIn_excl': reg_in_excl,
            'RegIn_incl': reg_in_incl
        })
    
    return pd.DataFrame(metrics)


def create_complete_word_database(aois_dict: Dict) -> pd.DataFrame:
    """
    Creează o bază de date completă cu TOATE cuvintele din stimuli,
    nu doar cele cu fixări. Extrage doar cuvinte UNICE (nu caractere individuale).
    Exclude întrebările (page începe cu 'question_').
    """
    all_words = []
    
    for stimulus_id, aoi_df in aois_dict.items():
        # Filtrează doar cuvintele (nu spații) și exclude întrebările
        word_aois = aoi_df[
            aoi_df['word'].notna() & 
            (aoi_df['word'] != '') &
            ~aoi_df['page'].astype(str).str.startswith('question')
        ].copy()
        
        if len(word_aois) == 0:
            continue
        
        # Grupează pe word_idx pentru a avea un singur rând per cuvânt
        # (AOI-ul are un rând per caracter, dar noi vrem un rând per cuvânt)
        word_groups = word_aois.groupby(['page', 'line_idx', 'word_idx', 'word_idx_in_line', 'word']).first().reset_index()
        
        for _, row in word_groups.iterrows():
            # Extrage numărul de pagină
            page_num = 0
            if pd.notna(row['page']):
                page_str = str(row['page'])
                if page_str.startswith('page_'):
                    try:
                        page_num = int(page_str.replace('page_', ''))
                    except:
                        pass
            
            # Skip dacă page_num e 0 (întrebări sau invalid)
            if page_num == 0:
                continue
            
            all_words.append({
                'expr_id': stimulus_id,
                'page_nr': page_num,
                'line_nr': row['line_idx'],
                'word_nr': row['word_idx'],
                'word_nr_in_line': row['word_idx_in_line'],
                'word': row['word']
            })
    
    df = pd.DataFrame(all_words)
    
    # Remove duplicates (același cuvânt pe aceeași pagină, linie, poziție)
    df = df.drop_duplicates(subset=['expr_id', 'page_nr', 'line_nr', 'word_nr'], keep='first')
    
    return df


def merge_metrics_with_baseline(baseline_df: pd.DataFrame, metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reunește baza de date completă (toate cuvintele) cu metricile calculate (doar cuvinte cu fixări).
    Cuvintele fără fixări vor avea valori 0/NA pentru metrici.
    """
    # Merge pe cheile: expr_id, page_nr, line_nr, word_nr
    merged = baseline_df.merge(
        metrics_df,
        on=['expr_id', 'page_nr', 'line_nr', 'word_nr'],
        how='left',
        suffixes=('', '_fix')
    )
    
    # Folosește cuvântul din baseline (sunt identice, dar baseline e mai sigur)
    if 'word_fix' in merged.columns:
        merged = merged.drop(columns=['word_fix'])
    
    # Completează valorile lipsă cu 0 pentru metrici numerice
    metric_columns = [
        'first_duration', 'total_duration', 'gaze_duration',
        'right_bounded_rt', 'go_past_time', 'FPFix', 'FPReg',
        'RegIn_excl', 'RegIn_incl'
    ]
    
    for col in metric_columns:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)
    
    # Sortează pe expr_id, page_nr, line_nr, word_nr
    merged = merged.sort_values(['expr_id', 'page_nr', 'line_nr', 'word_nr'])
    
    return merged


def process_multipleye_experiment(asc_file: Path, aoi_folder: Path, output_file: Path):
    """
    Procesează un experiment MultiplEYE complet:
    1. Parse .asc pentru fixări
    2. Load AOI-uri pentru mapare cuvinte
    3. Mapează fixările pe cuvinte
    4. Calculează metrici MoTR
    """
    
    # Parse fixations
    parser = EyeLinkParser(asc_file)
    fixations_df = parser.parse()
    
    if fixations_df.empty:
        print("Nu s-au găsit fixări!")
        return None
    
    # Load AOIs
    aoi_loader = AOILoader(aoi_folder)
    aoi_loader.load_all_aois()
    
    # Mapează fixările pe cuvinte pentru fiecare stimulus și pagină
    all_mapped_fixations = []
    
    for (stimulus_id, page), group in fixations_df.groupby(['stimulus_id', 'page'], dropna=False):
        if stimulus_id is None:
            continue
            
        print(f"\nMapare fixări pentru stimulus_id={stimulus_id}, page={page}")
        
        # Găsește AOI-ul corespunzător
        aoi_df = aoi_loader.get_aoi_for_stimulus(stimulus_id)
        
        if aoi_df is not None:
            mapped = map_fixations_to_words(group, aoi_df, page)
            if not mapped.empty:
                all_mapped_fixations.append(mapped)
                print(f"  Mapate {len(mapped)} fixări pe cuvinte")
            else:
                print(f"  Nu s-au putut mapa fixări")
        else:
            print(f"  Nu s-au găsit AOI-uri pentru stimulus_id={stimulus_id}")
    
    if not all_mapped_fixations:
        print("\nNu s-au putut mapa fixări pe cuvinte!")
        return None
    
    # Combină toate fixările mapate
    all_mapped = pd.concat(all_mapped_fixations, ignore_index=True)
    print(f"\nTotal fixări mapate: {len(all_mapped)}")
    
    # Calculează metrici MoTR
    print("\nCalcul metrici MoTR...")
    metrics_df = calculate_motr_metrics(all_mapped)
    
    if metrics_df.empty:
        print("Nu s-au putut calcula metrici!")
        return None
    
    print(f"Metrici calculate pentru {len(metrics_df)} cuvinte cu fixări")
    
    # Creează baza de date completă cu TOATE cuvintele din stimuli
    print("\nCreare bază de date completă cu toate cuvintele...")
    all_words_df = create_complete_word_database(aoi_loader.aois)
    print(f"Total cuvinte în stimuli: {len(all_words_df)}")
    
    # Merge cu metricile calculate
    print("\nReunire date de bază cu fixări...")
    complete_metrics_df = merge_metrics_with_baseline(all_words_df, metrics_df)
    print(f"Total cuvinte în output final: {len(complete_metrics_df)}")
    print(f"Cuvinte cu fixări: {complete_metrics_df['FPFix'].sum()}")
    print(f"Cuvinte fără fixări: {(complete_metrics_df['FPFix'] == 0).sum()}")
    
    # Salvează rezultatele
    metrics_df.to_csv(output_file, index=False)
    print(f"\n✓ Metrici salvate în: {output_file}")
    
    # Salvează și versiunea completă
    complete_output = output_file.parent / f"{output_file.stem}_complete.csv"
    complete_metrics_df.to_csv(complete_output, index=False)
    print(f"✓ Metrici complete (cu cuvinte fără fixări) salvate în: {complete_output}")
    
    # Afișează un preview din versiunea completă
    print("\nPreview metrici complete (primele 30 de cuvinte):")
    print(complete_metrics_df.head(30).to_string(index=False))
    
    # Statistici
    print("\n" + "="*80)
    print("STATISTICI")
    print("="*80)
    print(f"Total cuvinte în stimuli: {len(complete_metrics_df)}")
    print(f"Cuvinte cu fixări: {int(complete_metrics_df['FPFix'].sum())}")
    print(f"Cuvinte FĂRĂ fixări: {int((complete_metrics_df['FPFix'] == 0).sum())}")
    print(f"Procent cuvinte fixate: {complete_metrics_df['FPFix'].mean()*100:.1f}%")
    print(f"\nFirst duration medie (doar cuvinte fixate): {metrics_df['first_duration'].mean():.2f} ms")
    print(f"Total duration medie (doar cuvinte fixate): {metrics_df['total_duration'].mean():.2f} ms")
    print(f"Cuvinte cu refixări: {(metrics_df['RegIn_excl'] > 0).sum()}")
    
    return complete_metrics_df


def get_cli():
    """Command line interface."""
    parser = ArgumentParser(
        "ExtractMultiplEYEMoTRMetrics",
        description="Extrage metrici identice MoTR din datele MultiplEYE EyeLink"
    )
    
    parser.add_argument(
        '--asc_file',
        type=str,
        required=True,
        help="Fișier .asc EyeLink"
    )
    
    parser.add_argument(
        '--aoi_folder',
        type=str,
        required=True,
        help="Folder cu fișiere AOI CSV"
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='multipleye_motr_metrics.csv',
        help="Fișier de output (default: multipleye_motr_metrics.csv)"
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        default='./multipleye_motr_results',
        help="Director pentru output (default: ./multipleye_motr_results)"
    )
    
    return parser


def main():
    """Main function."""
    parser = get_cli()
    args = parser.parse_args()
    
    # Creează directorul de output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / args.output
    
    print("="*80)
    print("EXTRAGERE METRICI MultiplEYE → MoTR")
    print("="*80)
    
    process_multipleye_experiment(
        Path(args.asc_file),
        Path(args.aoi_folder),
        output_file
    )
    
    print("\n" + "="*80)
    print("PROCESARE COMPLETĂ!")
    print("="*80)


if __name__ == "__main__":
    main()