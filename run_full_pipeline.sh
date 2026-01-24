#!/bin/bash

# Full pipeline: from raw data to final combined reading measures

RAW_FILE=$1
ITEMS_JSON=${2:-"ro_items.json"}

if [ -z "$RAW_FILE" ]; then
    echo "Usage: ./run_full_pipeline.sh <raw_data_file> [items_json_file]"
    echo "Example: ./run_full_pipeline.sh data-1-2026-01-22-19-42.csv ro_items.json"
    exit 1
fi

if [ ! -f "$RAW_FILE" ]; then
    echo "Error: Raw data file not found: $RAW_FILE"
    exit 1
fi

if [ ! -f "$ITEMS_JSON" ]; then
    echo "Error: Items JSON file not found: $ITEMS_JSON"
    exit 1
fi

echo "================================================"
echo "MoTR Full Pipeline"
echo "================================================"
echo "Raw data file: $RAW_FILE"
echo "Items file: $ITEMS_JSON"
echo ""

# Step 1: Clean up previous results
echo "Step 1: Cleaning up previous results..."
rm -rf divided trial_files associations reading_measures output_combined temp_page processed_trial test_item10
echo "✓ Cleanup complete"
echo ""

# Step 2: Split raw data by ItemId and PageNumber
echo "Step 2: Splitting raw data by ItemId and PageNumber..."
conda run -n cavaenv python3 MoTR/post_processing/utils/splitByItemAndPage.py "$RAW_FILE" divided
if [ $? -ne 0 ]; then
    echo "✗ Error splitting data"
    exit 1
fi
echo ""

# Step 3: Create trial files for each page
echo "Step 3: Creating trial files for each page..."
conda run -n cavaenv python3 MoTR/post_processing/utils/createTrialsByPage.py "$ITEMS_JSON" trial_files
if [ $? -ne 0 ]; then
    echo "✗ Error creating trial files"
    exit 1
fi
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
        filename=$(basename "$csv_file")
        item_id=$(echo "$filename" | sed 's/item_//' | sed 's/_page_.*//')
        page_num=$(echo "$filename" | sed 's/.*_page_//' | sed 's/.csv//')
        
        trial_file="trial_files/trial_item_${item_id}_page_${page_num}.tsv"
        
        if [ -f "$trial_file" ]; then
            # Create temp directory with just this page
            mkdir -p temp_page
            cp "$csv_file" temp_page/
            
            # Run pipeline for this page (suppress output)
            conda run -n cavaenv python3 MoTR/post_processing/postprocessing.py \
                --processed_trial_file "$trial_file" \
                --divided_dir temp_page \
                --low_thres 160 \
                --up_thres 3000 \
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

# Step 5: Combine all results into one file
echo "Step 5: Combining all results..."
FINAL_OUTPUT="output_combined/all_reading_measures.csv"
first_file=true

for result_file in output_combined/item_*_page_*_measures.csv; do
    if [ -f "$result_file" ]; then
        if [ "$first_file" = true ]; then
            cat "$result_file" > "$FINAL_OUTPUT"
            first_file=false
        else
            tail -n +2 "$result_file" >> "$FINAL_OUTPUT"
        fi
    fi
done
echo "✓ Combined all results"
echo ""

# Step 6: Clean up temporary files and folders
echo "Step 6: Cleaning up temporary files..."
rm -rf divided trial_files associations reading_measures temp_page processed_trial test_item10
rm -f output_combined/item_*_page_*_measures.csv
echo "✓ Cleanup complete"
echo ""

# Summary
echo "================================================"
echo "Pipeline Complete!"
echo "================================================"
echo "Total pages processed: $total_pages"
echo "Success: $success_pages"
echo "Failed: $failed_pages"
echo ""
echo "Final output: $FINAL_OUTPUT"
if [ -f "$FINAL_OUTPUT" ]; then
    word_count=$(wc -l < "$FINAL_OUTPUT")
    echo "Total lines: $word_count"
    echo ""
    echo "First few lines:"
    head -3 "$FINAL_OUTPUT"
fi
echo ""
echo "================================================"
