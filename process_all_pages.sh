#!/bin/bash

# Script to process all pages of a specific item
ITEM_ID=$1

if [ -z "$ITEM_ID" ]; then
    echo "Usage: ./process_all_pages.sh <item_id>"
    echo "Example: ./process_all_pages.sh 10"
    exit 1
fi

echo "Processing all pages for item $ITEM_ID..."

# Clean up previous results
rm -rf associations reading_measures output_combined
mkdir -p output_combined

# Find all pages for this item
for csv_file in divided/item_${ITEM_ID}_page_*.csv; do
    if [ -f "$csv_file" ]; then
        # Extract page number from filename
        page_num=$(basename "$csv_file" | sed "s/item_${ITEM_ID}_page_//" | sed 's/.csv//')
        trial_file="trial_files/trial_item_${ITEM_ID}_page_${page_num}.tsv"
        
        if [ -f "$trial_file" ]; then
            echo "Processing page $page_num..."
            
            # Create temp directory with just this page
            mkdir -p temp_page
            cp "$csv_file" temp_page/
            
            # Run pipeline for this page
            conda run -n cavaenv python3 MoTR/post_processing/postprocessing.py \
                --processed_trial_file "$trial_file" \
                --divided_dir temp_page \
                --low_thres 150 \
                --up_thres 3000 \
                2>&1 | grep -E "(Welcome|associations|computing|Error)" || true
            
            # Copy results to output
            if [ -f "reading_measures/reader_${ITEM_ID}_reading_measures.csv" ]; then
                cp "reading_measures/reader_${ITEM_ID}_reading_measures.csv" \
                   "output_combined/item_${ITEM_ID}_page_${page_num}_measures.csv"
                echo "✓ Page $page_num completed"
            else
                echo "✗ Page $page_num failed"
            fi
            
            # Cleanup
            rm -rf temp_page associations reading_measures
        else
            echo "⚠ Trial file not found for page $page_num"
        fi
    fi
done

# Combine all results
echo ""
echo "Combining results..."
first_file=true
for result_file in output_combined/item_${ITEM_ID}_page_*_measures.csv; do
    if [ -f "$result_file" ]; then
        if [ "$first_file" = true ]; then
            cat "$result_file" > "output_combined/item_${ITEM_ID}_all_pages.csv"
            first_file=false
        else
            tail -n +2 "$result_file" >> "output_combined/item_${ITEM_ID}_all_pages.csv"
        fi
    fi
done

echo ""
echo "✓ Processing complete!"
echo "Results saved to: output_combined/item_${ITEM_ID}_all_pages.csv"
wc -l "output_combined/item_${ITEM_ID}_all_pages.csv"
