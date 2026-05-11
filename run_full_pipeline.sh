#!/bin/bash

# Full pipeline: from raw data to final combined reading measures
# Processes all CSV files in RawMoTRData folder

ITEMS_JSON=${1:-"ro_items.json"}
RAW_DATA_DIR="RawETData2"

if [ ! -f "$ITEMS_JSON" ]; then
    echo "Error: Items JSON file not found: $ITEMS_JSON"
    exit 1
fi

if [ ! -d "$RAW_DATA_DIR" ]; then
    echo "Error: Raw data directory not found: $RAW_DATA_DIR"
    exit 1
fi

echo "================================================"
echo "MoTR Full Pipeline - Batch Processing"
echo "================================================"
echo "Raw data directory: $RAW_DATA_DIR"
echo "Items file: $ITEMS_JSON"
echo ""

# Step 1: Clean up previous results
echo "Step 1: Cleaning up previous results..."
rm -rf divided trial_files associations reading_measures output_combined temp_page processed_trial test_item10 output
echo "✓ Cleanup complete"
echo ""

# Create output directory
mkdir -p output

# Count CSV files to process
csv_count=$(ls -1 "$RAW_DATA_DIR"/*.csv 2>/dev/null | wc -l)
if [ $csv_count -eq 0 ]; then
    echo "Error: No CSV files found in $RAW_DATA_DIR"
    exit 1
fi

echo "Found $csv_count CSV file(s) to process"
echo ""

# Step 2: Create trial files (only once, same for all CSV files)
echo "Step 2: Creating trial files for each page..."
conda run -n cavaenv python3 MoTR/post_processing/utils/createTrialsByPage.py "$ITEMS_JSON" trial_files
if [ $? -ne 0 ]; then
    echo "✗ Error creating trial files"
    exit 1
fi
echo "✓ Trial files created"
echo ""

# Process each CSV file
csv_counter=0
total_pages_all=0
success_pages_all=0
failed_pages_all=0

for RAW_FILE in "$RAW_DATA_DIR"/*.csv; do
    if [ -f "$RAW_FILE" ]; then
        csv_counter=$((csv_counter + 1))
        filename=$(basename "$RAW_FILE")
        
        echo "================================================"
        echo "Processing file $csv_counter/$csv_count: $filename"
        echo "================================================"
        
        # Step 3: Split raw data by ItemId and PageNumber
        echo "Step 3: Splitting raw data by ItemId and PageNumber..."
        conda run -n cavaenv python3 MoTR/post_processing/utils/splitByItemAndPage.py "$RAW_FILE" divided
        if [ $? -ne 0 ]; then
            echo "✗ Error splitting data for $filename"
            continue
        fi
        echo "✓ Data split complete"
        echo ""
        
        # Step 4: Process each page and collect results
        echo "Step 4: Processing all pages..."
        mkdir -p output_combined
        total_pages=0
        success_pages=0
        failed_pages=0
        
        for csv_file in divided/*.csv; do
            if [ -f "$csv_file" ]; then
                total_pages=$((total_pages + 1))
                
                # Extract item_id and page_num from filename (e.g., item_10_page_5.csv)
                csv_filename=$(basename "$csv_file")
                item_id=$(echo "$csv_filename" | sed 's/item_//' | sed 's/_page_.*//')
                page_num=$(echo "$csv_filename" | sed 's/.*_page_//' | sed 's/.csv//')
                
                trial_file="trial_files/trial_item_${item_id}_page_${page_num}.tsv"
                
                if [ -f "$trial_file" ]; then
                    # Create temp directory with just this page
                    mkdir -p temp_page
                    cp "$csv_file" temp_page/
                    
                    # Run pipeline for this page (suppress output)
                    conda run -n cavaenv python3 MoTR/post_processing/postprocessing.py \
                        --processed_trial_file "$trial_file" \
                        --divided_dir temp_page \
                        --low_thres 80 \
                        --up_thres 100000 \
                        > /dev/null 2>&1
                    
                    # Copy results to output
                    if [ -f "reading_measures/reader_${item_id}_reading_measures.csv" ]; then
                        cp "reading_measures/reader_${item_id}_reading_measures.csv" \
                           "output_combined/item_${item_id}_page_${page_num}_measures.csv"
                        success_pages=$((success_pages + 1))
                        echo "  ✓ Item $item_id, Page $page_num"
                    else
                        failed_pages=$((failed_pages + 1))
                        echo "  ✗ Item $item_id, Page $page_num (failed)"
                    fi
                    
                    # Cleanup temp files
                    rm -rf temp_page associations reading_measures
                else
                    failed_pages=$((failed_pages + 1))
                    echo "  ⚠ Item $item_id, Page $page_num (no trial file)"
                fi
            fi
        done
        echo ""
        
        # Step 5: Combine results from this CSV file
        echo "Step 5: Combining results from $filename..."
        CSV_OUTPUT="output/${filename%.csv}_all_measures.csv"
        first_file=true
        
        for result_file in output_combined/item_*_page_*_measures.csv; do
            if [ -f "$result_file" ]; then
                if [ "$first_file" = true ]; then
                    cat "$result_file" > "$CSV_OUTPUT"
                    first_file=false
                else
                    tail -n +2 "$result_file" >> "$CSV_OUTPUT"
                fi
            fi
        done
        
        if [ -f "$CSV_OUTPUT" ]; then
            line_count=$(wc -l < "$CSV_OUTPUT")
            echo "✓ Results saved: $CSV_OUTPUT ($line_count lines)"
        fi
        echo ""
        
        # Update totals
        total_pages_all=$((total_pages_all + total_pages))
        success_pages_all=$((success_pages_all + success_pages))
        failed_pages_all=$((failed_pages_all + failed_pages))
        
        # Cleanup for next file
        rm -rf divided output_combined
        echo "✓ File $csv_counter/$csv_count complete"
        echo ""
    fi
done

# Step 6: Combine ALL results from all CSV files into one master file
echo "================================================"
echo "Step 6: Creating master file with all results..."
echo "================================================"
MASTER_OUTPUT="output/all_reading_measures_combined.csv"
first_file=true

for result_file in output/*_all_measures.csv; do
    if [ -f "$result_file" ]; then
        if [ "$first_file" = true ]; then
            cat "$result_file" > "$MASTER_OUTPUT"
            first_file=false
        else
            tail -n +2 "$result_file" >> "$MASTER_OUTPUT"
        fi
    fi
done

if [ -f "$MASTER_OUTPUT" ]; then
    total_lines=$(wc -l < "$MASTER_OUTPUT")
    echo "✓ Master file created: $MASTER_OUTPUT"
    echo "  Total lines: $total_lines"
fi
echo ""

# Step 7: Clean up temporary files and folders
echo "Step 7: Cleaning up temporary files..."
rm -rf divided trial_files associations reading_measures temp_page processed_trial test_item10 output_combined
echo "✓ Cleanup complete"
echo ""

# Final Summary
echo "================================================"
echo "Pipeline Complete!"
echo "================================================"
echo "CSV files processed: $csv_counter"
echo "Total pages processed: $total_pages_all"
echo "Success: $success_pages_all"
echo "Failed: $failed_pages_all"
echo ""
echo "Output directory: output/"
echo "Master file: $MASTER_OUTPUT"
echo ""
echo "Individual files:"
ls -lh output/*.csv 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "================================================"
