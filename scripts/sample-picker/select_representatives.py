#!/usr/bin/env python3
"""
Select Representative Specimens for Expert Analysis

This script filters BOLD bioscan analysis data to select representative specimens
for genomic analysis, organizing them by expert and taxonomic family.

USAGE:
    python select_representatives.py \\
        --plates path/to/nhm_plates.txt \\
        --samples path/to/bioscan_analysis.tsv \\
        --experts path/to/experts.tsv \\
        --output path/to/output_directory

INPUT FILES:
    --plates    TXT file with one plate ID per line (plates currently at NHM)
    --samples   TSV file from bioscan_analysis with columns:
                - sampleid: Sample identifier (format: PLATE_###_WELL)
                - processid: Process identifier for sorting
                - bin_uri: BOLD BIN identifier
                - family: Taxonomic family
                - gaps: TRUE/FALSE indicator for gap analysis
                (plus any other columns to include in output)
    --experts   TSV file with columns:
                - Order: Taxonomic order (not used for filtering)
                - Family: Taxonomic family
                - Expert: Expert name (format: First Last)
    --output    Directory where output files will be saved

OUTPUT:
    - One XLSX file per expert/family combination: {First}_{Last}_{Family}.xlsx
    - Files contain specimens grouped by BIN, sorted alphabetically
    - Additional columns for lab processing workflow
    - Log file: {input_filename}_log.log with summary statistics

FILTERING LOGIC:
    1. Specimens must be on plates at NHM (plate extracted from sampleid)
    2. Must have gaps = TRUE
    3. Must belong to family with available expert

AUTHOR: Ben Price
DATE: 2025-01-14
"""

import argparse
import pandas as pd
from pathlib import Path
import sys


def extract_plate_from_sampleid(sampleid):
    """
    Extract plate ID from sample ID.
    
    Plate is everything before the last underscore.
    Example: FACE_008_A1 -> FACE_008
    
    Args:
        sampleid (str): Sample identifier
        
    Returns:
        str: Plate identifier
    """
    if pd.isna(sampleid):
        return None
    parts = str(sampleid).rsplit('_', 1)
    return parts[0] if len(parts) > 1 else sampleid


def load_plates(plates_file):
    """
    Load list of NHM plate IDs.
    
    Args:
        plates_file (Path): Path to TXT file with plate IDs
        
    Returns:
        set: Set of plate IDs
    """
    with open(plates_file, 'r') as f:
        plates = {line.strip() for line in f if line.strip()}
    return plates


def load_experts(experts_file):
    """
    Load expert assignments by family.
    
    Args:
        experts_file (Path): Path to TSV with Family and Expert columns
        
    Returns:
        dict: Mapping of family -> expert name
    """
    experts_df = pd.read_csv(experts_file, sep='\t')
    # Create dictionary mapping family to expert
    family_expert_map = dict(zip(experts_df['Family'], experts_df['Expert']))
    return family_expert_map


def filter_samples(samples_df, nhm_plates, family_expert_map):
    """
    Filter samples based on criteria:
    1. Plate must be at NHM
    2. gaps must be TRUE
    3. Family must have an assigned expert
    
    Args:
        samples_df (pd.DataFrame): Input samples dataframe
        nhm_plates (set): Set of plate IDs at NHM
        family_expert_map (dict): Family to expert mapping
        
    Returns:
        pd.DataFrame: Filtered samples with expert column added
    """
    # Extract plate from sampleid
    samples_df['plate'] = samples_df['sampleid'].apply(extract_plate_from_sampleid)
    
    # Apply filters
    filtered = samples_df[
        (samples_df['plate'].isin(nhm_plates)) &
        (samples_df['gaps'] == True) &
        (samples_df['family'].isin(family_expert_map.keys()))
    ].copy()
    
    # Add expert column
    filtered['expert'] = filtered['family'].map(family_expert_map)
    
    # Remove temporary plate column
    filtered = filtered.drop(columns=['plate'])
    
    return filtered


def prepare_output_dataframe(group_df):
    """
    Prepare dataframe for output with proper sorting and numbering.
    
    Args:
        group_df (pd.DataFrame): Dataframe for single expert/family combination
        
    Returns:
        pd.DataFrame: Organized dataframe ready for Excel output
    """
    # Sort by BIN alphabetically, then by processid within each BIN
    sorted_df = group_df.sort_values(['bin_uri', 'processid']).copy()
    
    # Add sort_order column (1-based index for entire file)
    sorted_df.insert(0, 'sort_order', range(1, len(sorted_df) + 1))
    
    # Add representative_specimen number within each BIN
    sorted_df['representative_specimen'] = sorted_df.groupby('bin_uri').cumcount() + 1
    
    # Find position of bin_uri column to insert representative_specimen next to it
    bin_uri_pos = sorted_df.columns.get_loc('bin_uri')
    
    # Reorder columns to put representative_specimen next to bin_uri
    cols = sorted_df.columns.tolist()
    cols.remove('representative_specimen')
    cols.insert(bin_uri_pos + 1, 'representative_specimen')
    sorted_df = sorted_df[cols]
    
    # Add empty columns for lab processing
    sorted_df['fluidx_tube'] = ''
    sorted_df['fluidx_box_barcode'] = ''
    sorted_df['fluidx_box_position'] = ''
    sorted_df['processing_notes'] = ''
    
    # Remove temporary expert column used for grouping
    if 'expert' in sorted_df.columns:
        sorted_df = sorted_df.drop(columns=['expert'])
    
    return sorted_df


def sanitize_filename(text):
    """
    Replace spaces with underscores for filenames.
    
    Args:
        text (str): Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    return text.replace(' ', '_')


def write_output_files(filtered_df, output_dir, log_file):
    """
    Write Excel files for each expert/family combination and create log.
    
    Args:
        filtered_df (pd.DataFrame): Filtered samples with expert assignments
        output_dir (Path): Output directory
        log_file (Path): Path to log file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Track statistics for logging
    stats = {}
    files_created = []
    
    # Group by expert and family
    for (expert, family), group in filtered_df.groupby(['expert', 'family']):
        # Skip if no samples
        if len(group) == 0:
            stats[(expert, family)] = 0
            continue
        
        # Prepare output dataframe
        output_df = prepare_output_dataframe(group)
        
        # Generate filename
        expert_name = sanitize_filename(expert)
        family_name = sanitize_filename(family)
        filename = f"{expert_name}_{family_name}.xlsx"
        filepath = output_dir / filename
        
        # Write to Excel
        output_df.to_excel(filepath, index=False, engine='openpyxl')
        
        # Track stats
        stats[(expert, family)] = len(output_df)
        files_created.append(filename)
    
    # Write log file
    with open(log_file, 'w') as f:
        f.write("Representative Specimen Selection Summary\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Total files created: {len(files_created)}\n\n")
        
        f.write("Samples per Expert and Family:\n")
        f.write("-" * 60 + "\n")
        
        # Sort by expert, then family
        for (expert, family), count in sorted(stats.items()):
            status = f"{count} samples"
            if count == 0:
                status += " (no file created)"
            f.write(f"{expert:30} {family:20} {status}\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"Total specimens processed: {sum(stats.values())}\n")
        
        if files_created:
            f.write("\nFiles created:\n")
            for fname in sorted(files_created):
                f.write(f"  - {fname}\n")
    
    print(f"\nProcessing complete!")
    print(f"Files created: {len(files_created)}")
    print(f"Total specimens: {sum(stats.values())}")
    print(f"Log file: {log_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Select representative specimens for expert analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--plates',
        type=Path,
        required=True,
        help='Path to TXT file with list of NHM plate IDs'
    )
    
    parser.add_argument(
        '--samples',
        type=Path,
        required=True,
        help='Path to TSV file with bioscan_analysis output'
    )
    
    parser.add_argument(
        '--experts',
        type=Path,
        required=True,
        help='Path to TSV file mapping families to experts'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Directory for output files'
    )
    
    args = parser.parse_args()
    
    # Validate input files exist
    for file_arg, file_path in [
        ('--plates', args.plates),
        ('--samples', args.samples),
        ('--experts', args.experts)
    ]:
        if not file_path.exists():
            print(f"Error: {file_arg} file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
    
    print("Loading input files...")
    
    # Load plates
    nhm_plates = load_plates(args.plates)
    print(f"  Loaded {len(nhm_plates)} NHM plates")
    
    # Load experts
    family_expert_map = load_experts(args.experts)
    print(f"  Loaded {len(family_expert_map)} family-expert mappings")
    
    # Load samples
    samples_df = pd.read_csv(args.samples, sep='\t')
    print(f"  Loaded {len(samples_df)} samples")
    
    print("\nFiltering samples...")
    
    # Filter samples
    filtered_df = filter_samples(samples_df, nhm_plates, family_expert_map)
    print(f"  {len(filtered_df)} samples passed all filters")
    print(f"  {len(samples_df) - len(filtered_df)} samples excluded")
    
    if len(filtered_df) == 0:
        print("\nWarning: No samples passed filters. No output files will be created.")
        sys.exit(0)
    
    print(f"\nGenerating output files...")
    
    # Create log filename from input samples filename
    log_filename = args.samples.stem + "_log.log"
    log_file = args.output / log_filename
    
    # Write output files and log
    write_output_files(filtered_df, args.output, log_file)


if __name__ == '__main__':
    main()
