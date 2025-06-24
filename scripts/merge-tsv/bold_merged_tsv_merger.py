#!/usr/bin/env python3
"""
BOLD Output Files Merger Script
Merges multiple TSV output files from different datasets (e.g., plants, animals).
Handles different field sets and merges based on identical field names and machine-readable names.
"""

import os
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import sys
import argparse

def setup_logging(log_file_path):
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def read_tsv_with_uuid_row(file_path, logger):
    """
    Read a TSV file assuming machine-readable headers in row 1 and actual headers in row 2.
    Returns DataFrame, UUID row (if present), and column headers.
    """
    try:
        file_name = os.path.basename(file_path)
        logger.info(f"Reading file: {file_name}")
        
        # Always read assuming headers are in row 2 (index 1)
        df = pd.read_csv(file_path, sep='\t', header=1, dtype=str)
        
        # Read the first row as potential UUID row
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            second_line = f.readline().strip()
        
        first_line_parts = first_line.split('\t')
        second_line_parts = second_line.split('\t')
        
        # Check if first row actually contains UUIDs or machine-readable content
        uuid_count = sum(1 for part in first_line_parts 
                        if part.strip() and len(part.strip()) == 36 and part.count('-') == 4)
        
        if uuid_count > 0:
            logger.info(f"Found {uuid_count} UUIDs in first row - treating as machine-readable header")
            uuid_row = first_line_parts
        else:
            logger.info(f"No UUIDs detected in first row - no machine-readable headers")
            uuid_row = None
        
        actual_headers = second_line_parts
        logger.info(f"Successfully read: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"Headers: {[h for h in actual_headers[:5] if h.strip()]}")
        
        return df, uuid_row, actual_headers
            
    except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")
        return None, None, None

def standardize_sample_id_column(df, file_name, logger):
    """Standardize Sample ID column name and log the change."""
    sample_id_variants = ['Sample ID', 'SampleID', 'sample_id', 'sampleid', 'Process ID', 'ProcessID']
    
    for variant in sample_id_variants:
        if variant in df.columns:
            if variant != 'Sample ID':
                df = df.rename(columns={variant: 'Sample ID'})
                logger.info(f"In {file_name}: Renamed '{variant}' to 'Sample ID'")
            return df
    
    logger.warning(f"No Sample ID column found in {file_name}. Available columns: {list(df.columns)}")
    return df

def merge_column_mappings(uuid_mappings, logger):
    """
    Merge column mappings from multiple files, handling conflicts.
    Returns a unified mapping of column_name -> uuid.
    """
    unified_mapping = {}
    conflicts = {}
    
    for file_name, mapping in uuid_mappings.items():
        for col_name, uuid_val in mapping.items():
            if col_name in unified_mapping:
                if unified_mapping[col_name] != uuid_val and uuid_val.strip():
                    # Conflict detected
                    if col_name not in conflicts:
                        conflicts[col_name] = {}
                    conflicts[col_name][file_name] = uuid_val
                    logger.warning(f"UUID conflict for column '{col_name}': {file_name} has '{uuid_val}', previous had '{unified_mapping[col_name]}'")
            else:
                if uuid_val.strip():  # Only add non-empty UUIDs
                    unified_mapping[col_name] = uuid_val
    
    if conflicts:
        logger.info(f"Found {len(conflicts)} column(s) with UUID conflicts. Using first encountered value.")
    
    return unified_mapping

def merge_bold_outputs(folder_path, output_file_path, log_file_path):
    """
    Main function to merge all TSV output files in a folder.
    """
    logger = setup_logging(log_file_path)
    logger.info(f"Starting BOLD output merge process for folder: {folder_path}")
    logger.info(f"Output file: {output_file_path}")
    
    # Get all TSV files in the folder
    folder = Path(folder_path)
    if not folder.exists():
        logger.error(f"Folder does not exist: {folder_path}")
        return False
    
    tsv_files = list(folder.glob("*.tsv"))
    if not tsv_files:
        logger.error(f"No TSV files found in {folder_path}")
        return False
    
    logger.info(f"Found {len(tsv_files)} TSV files to merge")
    
    # Initialize variables
    merged_df = None
    uuid_mappings = {}  # Store UUID mappings from each file
    processed_files = []
    all_columns = set()  # Track all unique columns across files
    
    # First pass: collect all column information and UUID mappings
    file_data = {}
    for file_path in tsv_files:
        df, uuid_row, headers = read_tsv_with_uuid_row(file_path, logger)
        
        if df is None:
            continue
        
        file_name = file_path.name
        logger.info(f"Processing {file_name}: {len(df)} rows, {len(df.columns)} columns")
        
        # Check if Sample ID column exists (with fallback logic)
        if 'Sample ID' not in df.columns:
            # Fallback: maybe we misdetected the header structure
            logger.warning(f"No Sample ID found in {file_name}. Attempting fallback reading...")
            
            # Try reading with headers in first row instead
            try:
                df_fallback = pd.read_csv(file_path, sep='\t', header=0, dtype=str)
                df_fallback = standardize_sample_id_column(df_fallback, file_name, logger)
                
                if 'Sample ID' in df_fallback.columns:
                    logger.info(f"Fallback successful - found Sample ID in first row headers")
                    df = df_fallback
                    # Adjust UUID detection - no UUID row in this case
                    uuid_row = None
                    headers = df.columns.tolist()
                else:
                    logger.warning(f"Skipping {file_name}: No Sample ID column found even in fallback")
                    continue
            except Exception as e:
                logger.error(f"Fallback reading failed for {file_name}: {e}")
                continue
        else:
            # Standardize Sample ID column name
            df = standardize_sample_id_column(df, file_name, logger)
        
        # Remove duplicates within the file
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['Sample ID'])
        if len(df) < initial_rows:
            logger.info(f"Removed {initial_rows - len(df)} duplicate Sample IDs from {file_name}")
        
        # Store UUID mapping if present
        if uuid_row and len(uuid_row) == len(headers):
            file_uuid_mapping = {}
            for header, uuid_val in zip(headers, uuid_row):
                if header.strip() and uuid_val.strip():
                    file_uuid_mapping[header.strip()] = uuid_val.strip()
            uuid_mappings[file_name] = file_uuid_mapping
            logger.info(f"Stored UUID mapping for {len(file_uuid_mapping)} columns from {file_name}")
        
        # Store file data
        file_data[file_name] = df
        all_columns.update(df.columns)
        processed_files.append(file_name)
    
    if not file_data:
        logger.error("No valid data files to merge")
        return False
    
    logger.info(f"Total unique columns across all files: {len(all_columns)}")
    
    # Merge UUID mappings
    unified_uuid_mapping = merge_column_mappings(uuid_mappings, logger)
    logger.info(f"Created unified UUID mapping for {len(unified_uuid_mapping)} columns")
    
    # Second pass: merge the data
    for file_name, df in file_data.items():
        if merged_df is None:
            merged_df = df.copy()
            logger.info(f"Initialized merged dataset with {file_name}")
        else:
            # Merge on Sample ID using outer join to keep all records
            before_merge = len(merged_df)
            merged_df = pd.merge(merged_df, df, on='Sample ID', how='outer', suffixes=('', f'_DUPLICATE_FROM_{file_name}'))
            after_merge = len(merged_df)
            logger.info(f"Merged {file_name}: {before_merge} -> {after_merge} rows")
    
    # Handle duplicate columns (same field from multiple files)
    logger.info("Checking for and resolving duplicate columns...")
    duplicate_cols = [col for col in merged_df.columns if '_DUPLICATE_FROM_' in col]
    
    for dup_col in duplicate_cols:
        # Extract original column name
        base_col = dup_col.split('_DUPLICATE_FROM_')[0]
        
        if base_col in merged_df.columns:
            # Merge the duplicate column with the base column
            # Use the duplicate value where base is null/empty
            base_series = merged_df[base_col].fillna('')
            dup_series = merged_df[dup_col].fillna('')
            
            # Combine: use base value, fall back to duplicate if base is empty
            combined_series = base_series.where(base_series != '', dup_series)
            
            # Check for conflicts (both have different non-empty values)
            conflicts = ((base_series != '') & (dup_series != '') & (base_series != dup_series))
            if conflicts.any():
                conflict_count = conflicts.sum()
                logger.warning(f"Found {conflict_count} conflicts for column '{base_col}'. Keeping original values.")
                # Keep original values in case of conflict
                combined_series = base_series.where(base_series != '', dup_series)
            
            merged_df[base_col] = combined_series
            merged_df = merged_df.drop(columns=[dup_col])
            logger.info(f"Merged duplicate column: {dup_col} -> {base_col}")
    
    # Ensure Sample ID is first column
    columns = merged_df.columns.tolist()
    if 'Sample ID' in columns:
        columns.remove('Sample ID')
        columns.insert(0, 'Sample ID')
        merged_df = merged_df[columns]
    
    # Write the merged file
    try:
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file_path, 'w', encoding='utf-8', newline='') as f:
            # Write UUID row if we have mappings
            if unified_uuid_mapping:
                uuid_row_output = []
                for col in merged_df.columns:
                    uuid_val = unified_uuid_mapping.get(col, '')
                    uuid_row_output.append(uuid_val)
                
                f.write('\t'.join(uuid_row_output) + '\n')
                logger.info(f"Wrote unified UUID row with {len(uuid_row_output)} columns")
            
            # Write the merged data
            merged_df.to_csv(f, sep='\t', index=False)
        
        logger.info(f"Successfully wrote merged file: {output_file_path}")
        logger.info(f"Final dataset: {len(merged_df)} rows, {len(merged_df.columns)} columns")
        logger.info(f"Processed files: {', '.join(processed_files)}")
        
        # Summary statistics
        logger.info("=== MERGE SUMMARY ===")
        logger.info(f"Input files processed: {len(processed_files)}")
        logger.info(f"Total unique Sample IDs: {merged_df['Sample ID'].nunique()}")
        logger.info(f"Total rows in output: {len(merged_df)}")
        logger.info(f"Total columns in output: {len(merged_df.columns)}")
        logger.info(f"Columns with UUID mappings: {len(unified_uuid_mapping)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error writing output file: {str(e)}")
        return False

def main():
    """Main execution function with command line argument parsing."""
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Merge multiple BOLD TSV output files with different field sets.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  python bold_merger.py "C:\_claude_files\projects\bge_d43_report\bold_merged"
  python bold_merger.py /path/to/merged/folder --output final_merged.tsv
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to folder containing TSV files to merge'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file name (default: bold_final_merged.tsv in input folder)',
        default=None
    )
    
    parser.add_argument(
        '--log', '-l',
        help='Log file name (default: auto-generated timestamp in input folder)',
        default=None
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate input folder
    folder_path = Path(args.folder_path)
    if not folder_path.exists():
        print(f"❌ Error: Folder does not exist: {args.folder_path}")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"❌ Error: Path is not a directory: {args.folder_path}")
        sys.exit(1)
    
    # Set up output file path
    if args.output:
        if os.path.isabs(args.output):
            output_file = args.output
        else:
            output_file = folder_path / args.output
    else:
        output_file = folder_path / "bold_final_merged.tsv"
    
    # Set up log file path
    if args.log:
        if os.path.isabs(args.log):
            log_file = args.log
        else:
            log_file = folder_path / args.log
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = folder_path / f"bold_merge_log_{timestamp}.log"
    
    print(f"🔬 BOLD Output Merger")
    print(f"🔍 Input folder: {folder_path}")
    print(f"📁 Output file: {output_file}")
    print(f"📋 Log file: {log_file}")
    print()
    
    # Run the merge
    success = merge_bold_outputs(str(folder_path), str(output_file), str(log_file))
    
    if success:
        print(f"\n✅ BOLD merge completed successfully!")
        print(f"📁 Output file: {output_file}")
        print(f"📋 Log file: {log_file}")
    else:
        print(f"\n❌ BOLD merge failed. Check log file for details: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
