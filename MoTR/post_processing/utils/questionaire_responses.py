#!/usr/bin/env python3
"""
Analizează răspunsurile la întrebările de comprehensiune din datele MoTR

Sample call:
python3 analyze_questions.py --in_file data-1-2026-01-23-20-04.csv
python3 analyze_questions.py --in_folder data/
"""

import pandas as pd
import numpy as np
from pathlib import Path
from argparse import ArgumentParser
import sys


def extract_question_data(df):
    """
    Extrage și procesează datele despre întrebări din DataFrame.
    Propagă ItemId, Experiment, Condition de la rândurile anterioare.
    
    Args:
        df: DataFrame cu datele raw
        
    Returns:
        DataFrame cu analiza răspunsurilor
    """
    # Găsește coloanele cu întrebări
    question_cols = [col for col in df.columns if col.startswith('question_')]
    answer_cols = [col for col in df.columns if col.startswith('answer_')]
    correct_cols = [col for col in df.columns if col.startswith('correct_answer_')]
    
    if not question_cols:
        print("Nu s-au găsit coloane cu întrebări în dataset!")
        return None
    
    # Numărul de întrebări per trial
    num_questions = len(question_cols)
    print(f"S-au găsit {num_questions} întrebări per trial")
    
    # Propagă ItemId, Experiment, Condition înainte (forward fill)
    for col in ['ItemId', 'Experiment', 'Condition']:
        if col in df.columns:
            df[col] = df[col].fillna(method='ffill')
    
    # Selectează doar rândurile care au date de întrebări
    question_rows = df[df[question_cols[0]].notna()].copy()
    
    if question_rows.empty:
        print("Nu s-au găsit date despre întrebări!")
        return None
    
    print(f"S-au găsit {len(question_rows)} seturi complete de răspunsuri")
    
    # Creează lista cu rezultatele
    results = []
    
    for idx, row in question_rows.iterrows():
        subject_id = row.get('SubjectId', row.get('prolific_pid', 'Unknown'))
        item_id = row.get('ItemId', 'Unknown')
        experiment = row.get('Experiment', 'Unknown')
        condition = row.get('Condition', 'Unknown')
        
        # Analizează fiecare întrebare
        correct_count = 0
        total_answered = 0
        
        for q_num in range(1, num_questions + 1):
            q_col = f'question_{q_num}'
            a_col = f'answer_{q_num}'
            c_col = f'correct_answer_{q_num}'
            
            if pd.notna(row[q_col]):
                question_text = row[q_col]
                user_answer = row[a_col] if pd.notna(row[a_col]) else "No answer"
                correct_answer = row[c_col] if pd.notna(row[c_col]) else "Unknown"
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    correct_count += 1
                total_answered += 1
                
                results.append({
                    'SubjectId': subject_id,
                    'ItemId': item_id,
                    'Experiment': experiment,
                    'Condition': condition,
                    'QuestionNumber': q_num,
                    'Question': question_text,
                    'UserAnswer': user_answer,
                    'CorrectAnswer': correct_answer,
                    'IsCorrect': is_correct,
                    'Score': None  # Va fi completat mai târziu
                })
        
        # Actualizează scorul pentru toate întrebările acestui trial
        if total_answered > 0:
            trial_score = f"{correct_count}/{total_answered}"
            for result in results[-total_answered:]:
                result['Score'] = trial_score
    
    return pd.DataFrame(results)


def generate_item_statistics(question_df):
    """
    Generează statistici per item.
    
    Args:
        question_df: DataFrame cu datele despre întrebări
        
    Returns:
        DataFrame cu statistici per item
    """
    # Statistici per item
    item_stats = question_df.groupby('ItemId').agg({
        'IsCorrect': ['sum', 'count', 'mean']
    }).reset_index()
    item_stats.columns = ['ItemId', 'CorrectAnswers', 'TotalQuestions', 'Accuracy']
    item_stats['Accuracy'] = (item_stats['Accuracy'] * 100).round(2)
    item_stats = item_stats.sort_values('Accuracy', ascending=False)
    
    print("\n" + "="*80)
    print("STATISTICI PER ITEM (sortate după acuratețe)")
    print("="*80)
    print(item_stats.to_string(index=False))
    
    # Statistici generale
    total_questions = len(question_df)
    total_correct = question_df['IsCorrect'].sum()
    overall_accuracy = (total_correct / total_questions * 100).round(2)
    
    print("\n" + "="*80)
    print("STATISTICI GENERALE")
    print("="*80)
    print(f"Total întrebări: {total_questions}")
    print(f"Răspunsuri corecte: {total_correct}")
    print(f"Răspunsuri incorecte: {total_questions - total_correct}")
    print(f"Acuratețe generală: {overall_accuracy}%")
    
    return item_stats


def process_file(input_file, output_dir):
    """
    Procesează un fișier CSV și generează analiza întrebărilor.
    
    Args:
        input_file: Path către fișierul CSV de input
        output_dir: Path către directorul de output
    """
    print(f"\nProcesez fișierul: {input_file}")
    
    try:
        df = pd.read_csv(input_file)
        print(f"S-au încărcat {len(df)} rânduri din {input_file}")
        
        # Extrage datele despre întrebări
        question_df = extract_question_data(df)
        
        if question_df is None or question_df.empty:
            print(f"Nu s-au putut extrage date despre întrebări din {input_file}")
            return None
        
        # Salvează question_analysis.csv
        output_path = output_dir / 'question_analysis.csv'
        question_df.to_csv(output_path, index=False)
        print(f"\n✓ Salvat: {output_path}")
        
        # Generează și salvează item_statistics.csv
        item_stats = generate_item_statistics(question_df)
        item_stats_path = output_dir / 'item_statistics.csv'
        item_stats.to_csv(item_stats_path, index=False)
        print(f"✓ Salvat: {item_stats_path}")
        
        return question_df
        
    except Exception as e:
        print(f"Eroare la procesarea fișierului {input_file}: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_folder(input_folder, output_dir):
    """
    Procesează toate fișierele CSV dintr-un folder.
    
    Args:
        input_folder: Path către folderul cu fișiere CSV
        output_dir: Path către directorul de output
    """
    input_path = Path(input_folder)
    
    if not input_path.exists():
        print(f"Folderul {input_folder} nu există!")
        return
    
    csv_files = list(input_path.glob('*.csv'))
    
    if not csv_files:
        print(f"Nu s-au găsit fișiere CSV în {input_folder}")
        return
    
    print(f"S-au găsit {len(csv_files)} fișiere CSV în {input_folder}")
    
    all_question_data = []
    
    for csv_file in csv_files:
        print(f"\n{'='*80}")
        print(f"Procesez: {csv_file.name}")
        print(f"{'='*80}")
        
        try:
            df = pd.read_csv(csv_file)
            question_df = extract_question_data(df)
            
            if question_df is not None and not question_df.empty:
                all_question_data.append(question_df)
        except Exception as e:
            print(f"Eroare la procesarea {csv_file.name}: {e}")
            continue
    
    if not all_question_data:
        print("\nNu s-au putut extrage date despre întrebări din niciun fișier!")
        return
    
    # Combină toate datele
    combined_df = pd.concat(all_question_data, ignore_index=True)
    
    # Salvează question_analysis.csv combinat
    output_path = output_dir / 'question_analysis.csv'
    combined_df.to_csv(output_path, index=False)
    print(f"\n{'='*80}")
    print(f"✓ Salvat: {output_path}")
    
    # Generează și salvează item_statistics.csv combinat
    print("\n" + "="*80)
    print("STATISTICI PENTRU TOATE DATELE COMBINATE")
    print("="*80)
    
    item_stats = generate_item_statistics(combined_df)
    item_stats_path = output_dir / 'item_statistics.csv'
    item_stats.to_csv(item_stats_path, index=False)
    print(f"✓ Salvat: {item_stats_path}")


def get_cli():
    """Command line interface pentru analiza întrebărilor."""
    parser = ArgumentParser("AnalyzeQuestions",
                          description="Analizează răspunsurile la întrebările de comprehensiune")
    
    # Input
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--in_file',
                           type=str,
                           help="Fișier CSV cu datele raw MoTR")
    input_group.add_argument('--in_folder',
                           type=str,
                           help="Folder cu mai multe fișiere CSV")
    
    # Output
    parser.add_argument('--output_dir',
                       type=str,
                       default='./question_analysis',
                       help="Director pentru fișierele de output (default: ./question_analysis)")
    
    return parser


def main():
    """Main function."""
    parser = get_cli()
    args = parser.parse_args()
    
    # Creează directorul de output dacă nu există
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.in_file:
        # Procesează un singur fișier
        process_file(args.in_file, output_dir)
    elif args.in_folder:
        # Procesează un folder întreg
        process_folder(args.in_folder, output_dir)
    
    print("\n" + "="*80)
    print("ANALIZA COMPLETĂ!")
    print("="*80)


if __name__ == "__main__":
    main()