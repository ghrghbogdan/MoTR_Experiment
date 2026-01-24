import pandas as pd
from pathlib import Path


class DataSplitter:
    def __init__(self, input_file, output_dir):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        
    def split_by_item_and_page(self):
        """Split raw data by ItemId and PageNumber into separate files"""
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Read the data
        print(f"\n=== Splitting {self.input_file.name} by ItemId and PageNumber ===")
        df = pd.read_csv(self.input_file)
        
        print(f"Total rows: {len(df)}")
        
        # Filter out rows with missing essential data
        df_filtered = df[
            df['ItemId'].notna() & 
            df['PageNumber'].notna() & 
            df['Index'].notna() & 
            df['Word'].notna()
        ].copy()
        
        print(f"Rows after filtering: {len(df_filtered)}")
        
        # Convert to proper types
        df_filtered['ItemId'] = df_filtered['ItemId'].astype(int)
        df_filtered['PageNumber'] = df_filtered['PageNumber'].astype(int)
        
        # Group by ItemId and PageNumber
        grouped = df_filtered.groupby(['ItemId', 'PageNumber'])
        
        print(f"Found {len(grouped)} unique ItemId-PageNumber combinations")
        
        # Save each group to a separate file
        file_count = 0
        for (item_id, page_num), group in grouped:
            output_file = self.output_dir / f"item_{item_id}_page_{page_num}.csv"
            group.to_csv(output_file, index=False)
            file_count += 1
        
        print(f"Saved {file_count} files to {self.output_dir}/")
        
        return file_count


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python splitByItemAndPage.py <input_file> [output_dir]")
        print("Example: python splitByItemAndPage.py data.csv ./divided")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./divided"
    
    splitter = DataSplitter(input_file, output_dir)
    splitter.split_by_item_and_page()
