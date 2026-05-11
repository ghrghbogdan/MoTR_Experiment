import json
import pandas as pd
from pathlib import Path


class TrialCreator:
    def __init__(self, items_file, output_dir):
        self.items_file = Path(items_file)
        self.output_dir = Path(output_dir)
        
    def create_trials_by_page(self):
        """Create trial files for each ItemId and PageNumber"""
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Load items
        print(f"\n=== Creating trial files from {self.items_file.name} ===")
        with open(self.items_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        file_count = 0
        total_words = 0
        
        # For each item
        for item in items:
            para_nr = int(item['ItemId'])
            expr_id = int(item['Experiment'])
            cond_id = int(item['Condition'])
            pages = item['Pages']
            
            # For each page in this item
            for page_nr, page_text in enumerate(pages):
                rows = []
                
                # Split page into lines and words, filter out empty lines
                lines = [line for line in page_text.strip().split('\n') if line.strip()]
                word_counter = 0  # Global word counter for the entire page
                for line_nr, line in enumerate(lines):
                    words = line.split()
                    for word in words:
                        rows.append({
                            'expr_id': expr_id,
                            'cond_id': cond_id,
                            'para_nr': para_nr,
                            'line_nr': line_nr,
                            'word_nr': word_counter,
                            'word': word
                        })
                        word_counter += 1
                
                # Create DataFrame and save
                df = pd.DataFrame(rows)
                output_file = self.output_dir / f'trial_item_{para_nr}_page_{page_nr}.tsv'
                df.to_csv(output_file, sep='\t', index=False)
                
                file_count += 1
                total_words += len(rows)
        
        print(f"Created {file_count} trial files with {total_words} total words in {self.output_dir}/")
        
        return file_count


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python createTrialsByPage.py <items_json_file> [output_dir]")
        print("Example: python createTrialsByPage.py ro_items.json ./trial_files")
        sys.exit(1)
    
    items_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./trial_files"
    
    creator = TrialCreator(items_file, output_dir)
    creator.create_trials_by_page()
