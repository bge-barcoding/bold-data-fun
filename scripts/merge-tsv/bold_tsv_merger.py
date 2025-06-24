#!/usr/bin/env python3
"""
TSV File Merger Script
Merges multiple TSV files in a folder based on Sample ID column.
Handles special case for merged_custom_fields.tsv with UUIDs in first row.
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

def read_tsv_file(file_path, logger):
    """
    Read a TSV file, handling the special case of merged_custom_fields.tsv.
    Returns DataFrame and any special metadata (like UUID row).
    """
    try:
        file_name = os.path.basename(file_path)
        logger.info(f"Reading file: {file_name}")
        
        if file_name == "merged_custom_fields.tsv":
            # Read first two rows to check structure
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
            
            # Read the file with headers in row 2 (index 1)
            df = pd.read_csv(file_path, sep='\t', header=1, dtype=str)
            
            # Store the UUID row for later use
            uuid_row = first_line.split('\t')
            logger.info(f"Found UUID row in {file_name} with {len(uuid_row)} columns")
            
            return df, uuid_row
        else:
            # Regular TSV file
            df = pd.read_csv(file_path, sep='\t', dtype=str)
            return df, None
            
    except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")
        return None, None

def standardize_sample_id_column(df, file_name, logger):
    """Standardize Sample ID column name and log the change."""
    sample_id_variants = ['Sample ID', 'SampleID', 'sample_id', 'sampleid']
    
    for variant in sample_id_variants:
        if variant in df.columns:
            if variant != 'Sample ID':
                df = df.rename(columns={variant: 'Sample ID'})
                logger.info(f"In {file_name}: Renamed '{variant}' to 'Sample ID'")
            return df
    
    logger.warning(f"No Sample ID column found in {file_name}. Available columns: {list(df.columns)}")
    return df

def merge_tsv_files(folder_path, output_file_path, log_file_path):
    """
    Main function to merge all TSV files in a folder.
    """
    logger = setup_logging(log_file_path)
    logger.info(f"Starting TSV merge process for folder: {folder_path}")
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
    
    # Define file processing order and file-to-category mapping
    file_order = ['voucher.tsv', 'taxonomy.tsv', 'specimen_details.tsv', 'collection_data.tsv', 
                  'merged_custom_fields.tsv', 'lab.tsv', 'tags.tsv']
    
    # Sort files according to desired order, putting unrecognized files at the end
    def get_file_priority(file_path):
        file_name = file_path.name.lower()
        if file_name in file_order:
            return file_order.index(file_name)
        return len(file_order)  # Put unrecognized files at the end
    
    tsv_files_sorted = sorted(tsv_files, key=get_file_priority)
    
    # Initialize variables
    merged_df = None
    uuid_row = None
    processed_files = []
    file_dataframes = {}  # Store each file's data for later column ordering
    
    # Process each TSV file
    for file_path in tsv_files_sorted:
        df, file_uuid_row = read_tsv_file(file_path, logger)
        
        if df is None:
            continue
        
        file_name = file_path.name
        logger.info(f"Processing {file_name}: {len(df)} rows, {len(df.columns)} columns")
        
        # Store UUID row if found (from merged_custom_fields.tsv)
        if file_uuid_row is not None:
            uuid_row = file_uuid_row
        
        # Standardize Sample ID column name
        df = standardize_sample_id_column(df, file_name, logger)
        
        # Check if Sample ID column exists
        if 'Sample ID' not in df.columns:
            logger.warning(f"Skipping {file_name}: No Sample ID column found")
            continue
        
        # Remove duplicates within the file
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['Sample ID'])
        if len(df) < initial_rows:
            logger.info(f"Removed {initial_rows - len(df)} duplicate Sample IDs from {file_name}")
        
        # Store the dataframe for this file
        file_dataframes[file_name] = df
        
        if merged_df is None:
            merged_df = df
            logger.info(f"Initialized merged dataset with {file_name}")
        else:
            # Merge on Sample ID
            before_merge = len(merged_df)
            merged_df = pd.merge(merged_df, df, on='Sample ID', how='outer', suffixes=('', f'_{file_name}'))
            after_merge = len(merged_df)
            logger.info(f"Merged {file_name}: {before_merge} -> {after_merge} rows")
        
        processed_files.append(file_name)
    
    if merged_df is None or merged_df.empty:
        logger.error("No data to merge - all files were skipped or empty")
        return False
    
    # Clean up unwanted columns and handle duplicates
    columns_to_remove = [
        'Source_File', 'Source_File_lab.tsv', 'Source_File_merged_custom_fields.tsv',
        'Source_File_specimen_details.tsv', 'Source_File_tags.tsv', 'Source_File_taxonomy.tsv',
        'Source_File_voucher.tsv'
    ]
    
    # Remove unwanted Source_File columns
    for col in columns_to_remove:
        if col in merged_df.columns:
            merged_df = merged_df.drop(columns=[col])
            logger.info(f"Removed column: {col}")
    
    # Handle duplicate fields - keep non-lab.tsv versions preferentially
    duplicate_fields = {
        'Collection Date': ['Collection Date_lab.tsv'],
        'Life Stage': ['Life Stage_specimen_details.tsv'],
        'Extra Info': ['Extra Info_specimen_details.tsv'],
        'Notes': ['Notes_specimen_details.tsv'],
        'Field ID': ['Field ID_voucher.tsv']
    }
    
    for base_field, duplicate_cols in duplicate_fields.items():
        available_versions = [col for col in merged_df.columns if col.startswith(base_field)]
        
        if len(available_versions) > 1:
            # Find the preferred version (not from lab.tsv)
            preferred_col = None
            for col in available_versions:
                if not col.endswith('_lab.tsv'):
                    preferred_col = col
                    break
            
            if preferred_col is None:
                # If only lab.tsv version exists, keep it but rename
                preferred_col = available_versions[0]
            
            # Remove all other versions and rename preferred to base name
            for col in available_versions:
                if col != preferred_col:
                    logger.info(f"Removing duplicate column: {col} (keeping {preferred_col})")
                    merged_df = merged_df.drop(columns=[col])
            
            # Rename the preferred column to the base name
            if preferred_col != base_field:
                merged_df = merged_df.rename(columns={preferred_col: base_field})
                logger.info(f"Renamed {preferred_col} to {base_field}")
    
    # Clean up remaining duplicate Sample ID columns
    sample_id_cols = [col for col in merged_df.columns if col.startswith('Sample ID_')]
    if sample_id_cols:
        logger.info(f"Removing duplicate Sample ID columns: {sample_id_cols}")
        merged_df = merged_df.drop(columns=sample_id_cols)
    
    # Reorder columns according to specified file order (preserving original column order within each file)
    logger.info("Reordering columns by file source...")
    ordered_columns = ['Sample ID']  # Always start with Sample ID
    
    # Add Process ID if it exists
    if 'Process ID' in merged_df.columns:
        ordered_columns.append('Process ID')
    
    # Use the original file order and preserve column order from each file
    file_order_keys = ['voucher', 'taxonomy', 'specimen_details', 'collection_data', 'merged_custom_fields', 'lab', 'tags']
    
    # For each file in order, add its columns in the order they appear in the merged dataframe
    for file_key in file_order_keys:
        file_suffix = f'_{file_key}.tsv'
        
        # Get columns from this file in the order they appear in the dataframe
        file_columns = []
        for col in merged_df.columns:
            if col in ['Sample ID', 'Process ID']:
                continue  # Already handled
            
            # Check if this column belongs to the current file
            if col.endswith(file_suffix):
                file_columns.append(col)
        
        # Add these columns in their natural order (not sorted)
        ordered_columns.extend(file_columns)
        if file_columns:
            logger.info(f"Added {len(file_columns)} columns from {file_key}.tsv")
    
    # Add any remaining columns that don't match the pattern
    remaining_columns = []
    for col in merged_df.columns:
        if col not in ordered_columns:
            remaining_columns.append(col)
    
    if remaining_columns:
        ordered_columns.extend(remaining_columns)
        logger.info(f"Added {len(remaining_columns)} remaining columns: {remaining_columns}")
    
    # Reorder the dataframe
    merged_df = merged_df[ordered_columns]
    logger.info(f"Final column order: {ordered_columns[:10]}..." if len(ordered_columns) > 10 else f"Final column order: {ordered_columns}")
    
    # Write the merged file
    try:
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file_path, 'w', encoding='utf-8', newline='') as f:
            # Write UUID row if we have one, aligned with current columns
            if uuid_row is not None:
                logger.info("Aligning UUID row with merged column structure...")
                
                # Create a mapping from original merged_custom_fields columns to UUIDs
                # We need to reconstruct this from the original file
                uuid_dict = {}
                try:
                    # Re-read the merged_custom_fields.tsv to get column-to-UUID mapping
                    mcf_file = folder / "merged_custom_fields.tsv"
                    if mcf_file.exists():
                        with open(mcf_file, 'r', encoding='utf-8') as mcf:
                            uuid_line = mcf.readline().strip().split('\t')
                            header_line = mcf.readline().strip().split('\t')
                            
                        # Create mapping from column name to UUID
                        for i, (uuid_val, header_val) in enumerate(zip(uuid_line, header_line)):
                            if header_val:  # Only map non-empty headers
                                uuid_dict[header_val] = uuid_val
                                # Also handle suffixed versions
                                uuid_dict[f"{header_val}_merged_custom_fields.tsv"] = uuid_val
                        
                        logger.info(f"Created UUID mapping for {len(uuid_dict)} columns")
                except Exception as e:
                    logger.warning(f"Could not create UUID mapping: {e}")
                
                # Build aligned UUID row for current column structure
                aligned_uuid_row = []
                for col in merged_df.columns:
                    if col in uuid_dict:
                        aligned_uuid_row.append(uuid_dict[col])
                    else:
                        aligned_uuid_row.append('')  # Empty for non-UUID columns
                
                f.write('\t'.join(aligned_uuid_row) + '\n')
                logger.info(f"Wrote aligned UUID row with {len(aligned_uuid_row)} columns")
            
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
        
        return True
        
    except Exception as e:
        logger.error(f"Error writing output file: {str(e)}")
        return False

def main():
    """Main execution function with command line argument parsing."""
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description='Merge multiple TSV files in a folder based on Sample ID column.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tsv_merger.py "C:\_claude_files\projects\bge_d43_report\bold_plants"
  python tsv_merger.py /path/to/tsv/folder --output custom_merged.tsv
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to folder containing TSV files to merge'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file name (default: merged_output.tsv in input folder)',
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
        output_file = folder_path / "merged_output.tsv"
    
    # Set up log file path
    if args.log:
        if os.path.isabs(args.log):
            log_file = args.log
        else:
            log_file = folder_path / args.log
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = folder_path / f"tsv_merge_log_{timestamp}.log"
    
    print(f"🔍 Input folder: {folder_path}")
    print(f"📁 Output file: {output_file}")
    print(f"📋 Log file: {log_file}")
    print()
    
    # Run the merge
    success = merge_tsv_files(str(folder_path), str(output_file), str(log_file))
    
    if success:
        print(f"\n✅ Merge completed successfully!")
        print(f"📁 Output file: {output_file}")
        print(f"📋 Log file: {log_file}")
    else:
        print(f"\n❌ Merge failed. Check log file for details: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()
