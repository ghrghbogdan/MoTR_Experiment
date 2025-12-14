from pathlib import Path
import pandas as pd
import os


class FileDivider:
    """
    A class that divides a raw data file containing reading data for all participants into separate files for each participant.
    """

    def __init__(self, raw_data_path, new_data_path):
        # Initialize the FileDivider object with the paths of the raw data file and the directory for the divided files.
        # self.raw_data_path = Path(f"{raw_data_path}")
        self.raw_data_path = raw_data_path
        # self.new_data_path = Path(f"{new_data_path}")
        self.new_data_path = new_data_path
        self.raw_data_df = pd.read_csv(self.raw_data_path, dtype={"Index": str, "ItemId": str,
                                                                  "Condition": str, "Experiment": str,
                                                                  "mousePositionX": str, "mousePositionY": str})
        
        # Handle both SubjectId and submission_id column names
        if 'SubjectId' in self.raw_data_df.columns:
            # Forward fill SubjectId first (it's only in the first row per participant)
            self.raw_data_df['SubjectId'].ffill(inplace=True)
            if 'submission_id' not in self.raw_data_df.columns:
                self.raw_data_df['submission_id'] = self.raw_data_df['SubjectId']

    # Check if the directory for the divided files exists, if not, make one
    def _make_directory_for_divided_data(self) -> None:
        if not os.path.exists(self.new_data_path):
            os.mkdir(self.new_data_path)

    def divide_raw_file(self) -> None:
        self._make_directory_for_divided_data()
        # Fill any NaN values in the 'response' column and preprocess other columns.
        self._fill_nan_response_column()
        # Ensure submission_id column exists
        if 'submission_id' not in self.raw_data_df.columns:
            if 'SubjectId' in self.raw_data_df.columns:
                self.raw_data_df['submission_id'] = self.raw_data_df['SubjectId']
            else:
                raise ValueError("Neither 'submission_id' nor 'SubjectId' column found in data")
        # Group the data by 'submission_id' and create separate files for each group/participant.
        grouped_data = self.raw_data_df.groupby('submission_id')
        for submission_id, group in grouped_data:
            group.to_csv(self.new_data_path / f'reader_{submission_id}.csv', index=False, float_format=None, encoding='utf-8-sig')

    def _fill_nan_response_column(self) -> None:
        # Fill NaN values in different columns and perform necessary type conversions.
        # This ensures the data is in the correct format for further processing.
        
        # Extract response from answer columns if available
        # Răspunsurile sunt pe rânduri speciale unde Experiment e null dar question_1 e populated
        if 'answer_1' in self.raw_data_df.columns:
            # Găsește rândurile cu răspunsuri (Experiment null + question_1 populated)
            answer_rows_mask = (self.raw_data_df['Experiment'].isna()) & (self.raw_data_df['question_1'].notna())
            
            # Pentru fiecare rând cu răspunsuri, calculează corectitudinea
            def calculate_correctness(row):
                correct_answers = []
                for i in range(1, 7):
                    ans_col = f'answer_{i}'
                    correct_col = f'correct_answer_{i}'
                    if pd.notna(row.get(ans_col)) and pd.notna(row.get(correct_col)):
                        is_correct = str(row[ans_col]).strip() == str(row[correct_col]).strip()
                        correct_answers.append('1' if is_correct else '0')
                return ','.join(correct_answers) if correct_answers else ''
            
            # Creează coloana response doar pe rândurile cu răspunsuri
            self.raw_data_df.loc[answer_rows_mask, 'response'] = self.raw_data_df[answer_rows_mask].apply(calculate_correctness, axis=1)
        
        # Forward fill ItemId înainte de backward fill response
        self.raw_data_df['ItemId'].fillna(method='ffill', inplace=True)
        
        # Backward fill response pentru a propaga de la rândurile cu răspunsuri la toate rândurile ItemId-ului
        if 'response' in self.raw_data_df.columns:
            self.raw_data_df['response'].fillna(method='bfill', inplace=True)
        
        self.raw_data_df.dropna(subset=['ItemId'], inplace=True)
        self.raw_data_df['ItemId'] = self.raw_data_df['ItemId'].astype(float)
        self.raw_data_df['ItemId'] = self.raw_data_df['ItemId'].astype(int)
        self.raw_data_df['Experiment'].fillna(method='ffill', inplace=True)
        self.raw_data_df['Experiment'] = self.raw_data_df['Experiment'].astype(float).astype(int)
        self.raw_data_df['Condition'].fillna(method='ffill', inplace=True)
        self.raw_data_df['Condition'] = self.raw_data_df['Condition'].astype(float).astype(int)
        self.raw_data_df['Index'].fillna(value=-100, inplace=True)
        self.raw_data_df['Index'] = self.raw_data_df['Index'].astype(float).astype(int)
        # self.raw_data_df['Word'].fillna(value="NULL", inplace=True)
        self.raw_data_df['mousePositionX'].fillna(value=425, inplace=True)
        self.raw_data_df['mousePositionX'] = self.raw_data_df['mousePositionX'].astype(float).astype(int)
        self.raw_data_df['mousePositionY'].fillna(value=285, inplace=True)
        self.raw_data_df['mousePositionY'] = self.raw_data_df['mousePositionY'].astype(float).astype(int)

    def correct_motr_data(self):
        # List all CSV files in the directory
        divided_files = Path(self.new_data_path).glob('*.csv')
        corrected_divided_path = Path(self.new_data_path).parent / f'corrected_{Path(self.new_data_path).name}'
        corrected_divided_path.mkdir(parents=True, exist_ok=True)
        for file_path in divided_files:
            df = pd.read_csv(file_path)
            # Check if there are negative values in "mousePositionX"
            if (df['mousePositionX'] < -1).any():
                print(f"I am correcting file: {file_path}")
                # df for corrections where "mousePositionX" is negative --> words are split between two lines
                negative_mouse_positions = df['mousePositionX'] < 0
                only_to_correct_word_position = (
                        df['wordPositionLeft'].notnull() &
                        df['wordPositionTop'].notnull() &
                        (df['mousePositionX'] > 94) &
                        (df['mousePositionY'] > 20)
                )
                combined_positions = negative_mouse_positions | only_to_correct_word_position
                # df for corrections if "wordPositionLeft" and "wordPositionTop" are not None and "mousePositionX" and "mousePositionY" are offset --> normal words
                normal_mouse_positions = (
                        df['wordPositionLeft'].notnull() &
                        df['wordPositionTop'].notnull() &
                        (df['mousePositionX'] <= df['wordPositionRight'] - df['wordPositionLeft']) |
                        (df['mousePositionY'] <= df['wordPositionBottom'] - df['wordPositionTop'])
                )
                blank_mouse_positions = ((df['mousePositionX'] < 90) & (df['mousePositionY'] < 20)) & \
                                        ~(combined_positions | normal_mouse_positions)

                # Correct the "mousePositionX" and "mousePositionY" values
                df.loc[normal_mouse_positions, 'mousePositionX'] += df['wordPositionLeft']
                df.loc[normal_mouse_positions, 'mousePositionY'] += df['wordPositionTop']
                df.loc[combined_positions, ['wordPositionBottom', 'wordPositionTop']] += 40
                # Find the offset value for the "wordPositionLeft" and "wordPositionRight" columns
                for index in df[combined_positions].index:
                    offset_value = df.at[index, 'wordPositionLeft'] - 94
                    df.at[index, 'wordPositionLeft'] -= offset_value
                    df.at[index, 'wordPositionRight'] -= offset_value
                # Pre-calculate the next valid 'wordPositionLeft' for each row
                last_valid_index = None
                for i in reversed(range(len(df))):  # Start from the last row
                    if pd.notnull(df.at[i, 'wordPositionLeft']):
                        last_valid_index = i
                    elif last_valid_index is not None and blank_mouse_positions[i]:
                        # Update mousePositionX for the current row using wordPositionLeft from the nearest valid row below
                        df.at[i, 'mousePositionX'] += df.at[last_valid_index, 'wordPositionLeft']
                        df.at[i, 'mousePositionY'] += df.at[last_valid_index, 'wordPositionTop']
                # Re-evaluate blank_mouse_positions after initial corrections
                blank_mouse_positions = df['mousePositionX'] < 0
                # Additional adjustments for rows with mousePositionX < 0 after initial corrections
                df.loc[blank_mouse_positions, 'mousePositionX'] += 739
                df.loc[blank_mouse_positions, 'mousePositionY'] += 67
            df.to_csv(f'{corrected_divided_path}/{file_path.stem}.csv', index=False, encoding='utf-8-sig')
        print(f"All files in '{self.new_data_path}' have been processed and corrected files are saved in '{corrected_divided_path}'.")