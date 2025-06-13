#!/usr/bin/env python3
"""
Script to extract taxonomy information based on plate IDs.

Usage: python extract_taxonomy.py plate_id1 plate_id2 plate_id3 ...

The script searches through subdirectories for merged_custom_fields.tsv, taxonomy.tsv, and lab.tsv files,
matches records based on SampleID or Plate_Well format, and outputs combined data including Process ID.
"""

import sys
import os
import pandas as pd
from pathlib import Path
import argparse


def find_tsv_files(base_dir):
    """Find all required TSV files in subdirectories."""
    base_path = Path(base_dir)
    file_triplets = []
    
    for subdir in base_path.iterdir():
        if subdir.is_dir():
            merged_file = subdir / "merged_custom_fields.tsv"
            taxonomy_file = subdir / "taxonomy.tsv"
            lab_file = subdir / "lab.tsv"
            
            if merged_file.exists() and taxonomy_file.exists() and lab_file.exists():
                file_triplets.append((str(merged_file), str(taxonomy_file), str(lab_file)))
    
    return file_triplets


def load_and_process_files(merged_file, taxonomy_file, lab_file):
    """Load and process the TSV files, handling potential encoding issues."""
    try:
        # Try UTF-8 first, then fallback to latin-1 if needed
        try:
            # Skip the first row if it contains "Machine readable" for merged_custom_fields
            # Add low_memory=False to suppress dtype warnings
            merged_df = pd.read_csv(merged_file, sep='\t', encoding='utf-8', skiprows=1, low_memory=False)
            taxonomy_df = pd.read_csv(taxonomy_file, sep='\t', encoding='utf-8', low_memory=False)
            lab_df = pd.read_csv(lab_file, sep='\t', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            merged_df = pd.read_csv(merged_file, sep='\t', encoding='latin-1', skiprows=1, low_memory=False)
            taxonomy_df = pd.read_csv(taxonomy_file, sep='\t', encoding='latin-1', low_memory=False)
            lab_df = pd.read_csv(lab_file, sep='\t', encoding='latin-1', low_memory=False)
        
        return merged_df, taxonomy_df, lab_df
    except Exception as e:
        print(f"Error loading files {merged_file}, {taxonomy_file}, and {lab_file}: {e}")
        return None, None, None


def create_plate_well_id(plate_id, well_position):
    """Create the Plate_Well format: e.g., BGE_00647_A08"""
    return f"{plate_id}_{well_position}"


def extract_plate_id_from_sample_id(sample_id):
    """Extract plate ID from sample ID format like BGE_00841_A1 -> BGE_00841"""
    if pd.isna(sample_id) or sample_id == '':
        return None
    
    # Split by underscore and take first two parts for BGE format
    parts = str(sample_id).split('_')
    if len(parts) >= 2 and parts[0] == 'BGE':
        return f"{parts[0]}_{parts[1]}"
    return None


def match_records(merged_df, taxonomy_df, lab_df, target_plate_ids):
    """Match records between merged_custom_fields, taxonomy, and lab files based on linking criteria."""
    results = []
    
    # Handle two different data formats:
    # Format 1: Plate ID column is populated (original format)
    # Format 2: Plate ID column is empty, but SampleID contains full identifier like BGE_00841_A1
    
    # Check if Plate ID column exists and has non-empty values
    if 'Plate ID' in merged_df.columns and not merged_df['Plate ID'].isna().all():
        # Format 1: Use Plate ID column
        target_merged = merged_df[merged_df['Plate ID'].isin(target_plate_ids)].copy()
        
        if not target_merged.empty:
            # Create Plate_Well column for matching
            target_merged['Plate_Well'] = target_merged.apply(
                lambda row: create_plate_well_id(row['Plate ID'], row['Well Position']), axis=1
            )
    else:
        # Format 2: Extract plate ID from SampleID
        merged_df['Extracted_Plate_ID'] = merged_df['SampleID'].apply(extract_plate_id_from_sample_id)
        target_merged = merged_df[merged_df['Extracted_Plate_ID'].isin(target_plate_ids)].copy()
        
        if not target_merged.empty:
            # For this format, SampleID is already in the Plate_Well format (e.g., BGE_00841_A1)
            target_merged['Plate_Well'] = target_merged['SampleID']
    
    if target_merged.empty:
        return results
    
    for _, merged_row in target_merged.iterrows():
        sample_id = merged_row['SampleID']
        plate_well = merged_row['Plate_Well']
        
        # Try matching method 1: SampleID = Sample ID
        taxonomy_match = taxonomy_df[taxonomy_df['Sample ID'] == sample_id]
        
        # If no match, try matching method 2: Plate_Well = Sample ID
        if taxonomy_match.empty:
            taxonomy_match = taxonomy_df[taxonomy_df['Sample ID'] == plate_well]
        
        # If we found a taxonomy match, look for corresponding lab data
        if not taxonomy_match.empty:
            # Take the first match if multiple exist
            taxonomy_row = taxonomy_match.iloc[0]
            taxonomy_sample_id = taxonomy_row['Sample ID']
            
            # Look for matching lab record using the same Sample ID from taxonomy
            lab_match = lab_df[lab_df['Sample ID'] == taxonomy_sample_id]
            
            # Create result row
            result_row = {
                'Process ID': lab_match.iloc[0]['Process ID'] if not lab_match.empty else '',
                'Plate_Well': plate_well,
                'Sample ID': taxonomy_sample_id
            }
            
            # Add all taxonomy columns except 'Sample ID' (already added)
            for col in taxonomy_df.columns:
                if col != 'Sample ID':
                    result_row[col] = taxonomy_row[col]
            
            results.append(result_row)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Extract taxonomy information based on plate IDs')
    parser.add_argument('plate_ids', nargs='+', help='List of plate IDs to extract')
    parser.add_argument('--base-dir', default='.', help='Base directory to search for TSV files (default: current directory)')
    parser.add_argument('--output', default='extracted_taxonomy.tsv', help='Output file name (default: extracted_taxonomy.tsv)')
    
    args = parser.parse_args()
    
    plate_ids = args.plate_ids
    base_dir = args.base_dir
    output_file = args.output
    
    print(f"Searching for plate IDs: {plate_ids}")
    print(f"Base directory: {base_dir}")
    
    # Find all TSV file triplets
    file_triplets = find_tsv_files(base_dir)
    print(f"Found {len(file_triplets)} directories with all three required TSV files")
    
    if not file_triplets:
        print("No directories found with merged_custom_fields.tsv, taxonomy.tsv, and lab.tsv files")
        return
    
    all_results = []
    
    # Process each directory
    for merged_file, taxonomy_file, lab_file in file_triplets:
        print(f"Processing: {os.path.dirname(merged_file)}")
        
        merged_df, taxonomy_df, lab_df = load_and_process_files(merged_file, taxonomy_file, lab_file)
        
        if merged_df is None or taxonomy_df is None or lab_df is None:
            continue
        
        # Match records for target plate IDs
        results = match_records(merged_df, taxonomy_df, lab_df, plate_ids)
        all_results.extend(results)
        
        if results:
            print(f"  Found {len(results)} matching records")
    
    # Create output DataFrame
    if all_results:
        output_df = pd.DataFrame(all_results)
        
        # Reorder columns to put Process ID, Plate_Well and Sample ID first
        columns = ['Process ID', 'Plate_Well', 'Sample ID']
        other_columns = [col for col in output_df.columns if col not in columns]
        output_df = output_df[columns + other_columns]
        
        # Save to file
        output_df.to_csv(output_file, sep='\t', index=False)
        print(f"\nExtracted {len(output_df)} total records to {output_file}")
        
        # Display summary
        print(f"Columns in output: {list(output_df.columns)}")
        print(f"Unique plate IDs found: {sorted(set([pw.split('_')[0] + '_' + pw.split('_')[1] for pw in output_df['Plate_Well']]))}")
    else:
        print(f"\nNo matching records found for plate IDs: {plate_ids}")


if __name__ == "__main__":
    main()
