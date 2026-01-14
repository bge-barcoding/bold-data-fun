#!/usr/bin/env python3
"""
GBIF Name Processor

Processes GBIF species match output files against a rules matrix to determine
whether to use original names or GBIF-matched names for ENA taxonomy submissions.

Workflow Context:
    1. Specimen names are matched against the GBIF backbone taxonomy
    2. This script applies rules based on match status, match type, and name similarity
    3. Output files are generated for downstream ENA submission or further validation

Input Requirements:
    - Input CSV must contain columns: ID, scientificName, type_status, gbif_status,
      gbif_matchType, gbif_species, gbif_genus, gbif_family, gbif_order, gbif_class,
      gbif_phylum, gbif_speciesKey, gbif_genusKey
    - Rules CSV must contain columns:
        Required: status, matchType, 'GBIF species value', 'GBIF genus value',
                  'Type specimen', 'name to use'
        Optional: 'text to add to \'description\' column of taxononmy_request.tsv',
                  'check ENA with GBIF name?', 'manual verification needed'

Decision Logic:
    The script compares the original scientific name against GBIF's matched name:
    - Species epithet comparison (same/different)
    - Genus comparison (same/different)
    - Type specimen status (yes/no)
    These factors, combined with GBIF's status and matchType, determine which
    name to use according to the rules matrix.

Output Files:
    1. {basename}_request_taxid.tsv
       Names where the original should be used, formatted for ENA taxonomy requests.
       Columns: proposed_name, name_type, host, project_id, description
       Notes:
         - Deduplicated by proposed_name (unique species names only)
         - Description contains GBIF URL; falls back to gbif_genusKey if
           gbif_speciesKey is empty/NOT_FOUND (these rows are also added to
           manually_verify.csv)
         - Type specimens are annotated with "| TYPE" appended to description

    2. {basename}_check_ENA.csv
       Names where the GBIF name should be used, requiring ENA validation.
       Columns: ID, scientificName, genus, family, order, class, phylum

    3. {basename}_annotated.csv
       Complete input data with decision columns appended for review.
       Additional columns: name_to_use, description_text, check_ENA_with_GBIF,
       manual_verification_needed

    4. {basename}_manually_verify.csv
       Rows flagged for manual verification, containing all original input columns.

    5. {basename}.log
       Log file containing processing summary (same as terminal output).

Usage:
    python gbif_name_processor.py -i INPUT_FILE -r RULES_FILE [-o OUTPUT_DIR] [-p PROJECT_ID]

Examples:
    # Basic usage with default project ID (BGE)
    python gbif_name_processor.py -i gbif_results.csv -r gbif_rules.csv

    # Specify output directory and custom project ID
    python gbif_name_processor.py -i gbif_results.csv -r gbif_rules.csv -o ./output -p UKBOL

"""

import argparse
import csv
import os
import sys
from pathlib import Path


def load_rules(rules_file: str) -> dict:
    """
    Load the rules CSV into a dictionary keyed by (status, matchType, species_match, genus_match, is_type).
    """
    rules = {}
    with open(rules_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                row['status'].strip().upper(),
                row['matchType'].strip().upper(),
                row['GBIF species value'].strip().lower(),
                row['GBIF genus value'].strip().lower(),
                row['Type specimen'].strip().upper() == 'YES'
            )
            rules[key] = {
                'name_to_use': row['name to use'].strip().lower(),
                'description_text': row.get('text to add to \'description\' column of taxononmy_request.tsv', '').strip(),
                'check_ena': row.get('check ENA with GBIF name?', '').strip().lower() == 'yes',
                'manual_verification': row.get('manual verification needed', '').strip().lower() == 'yes'
            }
    return rules


def extract_species_epithet(binomial: str) -> str:
    """Extract the species epithet (second word) from a binomial name."""
    if not binomial:
        return ''
    parts = binomial.strip().split()
    return parts[1] if len(parts) >= 2 else ''


def extract_genus(binomial: str) -> str:
    """Extract the genus (first word) from a binomial name."""
    if not binomial:
        return ''
    parts = binomial.strip().split()
    return parts[0] if parts else ''


def is_type_specimen(type_status: str) -> bool:
    """Check if 'type' is present in the type_status column (case-insensitive)."""
    if not type_status:
        return False
    return 'type' in type_status.lower()


def compare_names(original: str, gbif: str) -> str:
    """
    Compare two name components and return 'same' or 'different'.
    Handles case-insensitive comparison.
    """
    if not original or not gbif:
        return 'different'
    return 'same' if original.strip().lower() == gbif.strip().lower() else 'different'


def process_row(row: dict, rules: dict) -> dict:
    """
    Process a single row from the input file and determine the appropriate action.
    
    Returns a dictionary with the rule outcome and additional metadata.
    """
    # Extract values from input row
    status = row.get('gbif_status', '').strip().upper()
    match_type = row.get('gbif_matchType', '').strip().upper()
    type_status = row.get('type_status', '')
    verbatim_name = row.get('scientificName', '').strip()
    gbif_species = row.get('gbif_species', '').strip()
    gbif_genus = row.get('gbif_genus', '').strip()
    gbif_family = row.get('gbif_family', '').strip()
    gbif_key = row.get('gbif_speciesKey', '').strip()
    gbif_genus_key = row.get('gbif_genusKey', '').strip()
    sample_id = row.get('ID', '').strip()
    
    # Determine if type specimen
    is_type = is_type_specimen(type_status)
    
    # Extract species epithets for comparison
    original_species_epithet = extract_species_epithet(verbatim_name)
    gbif_species_epithet = extract_species_epithet(gbif_species)
    
    # Extract genera for comparison
    original_genus = extract_genus(verbatim_name)
    
    # Compare species and genus
    species_match = compare_names(original_species_epithet, gbif_species_epithet)
    genus_match = compare_names(original_genus, gbif_genus)
    
    # Build the rule key
    rule_key = (status, match_type, species_match, genus_match, is_type)
    
    # Look up the rule
    if rule_key in rules:
        rule = rules[rule_key]
    else:
        # No matching rule found
        rule = {
            'name_to_use': 'unknown',
            'description_text': '',
            'check_ena': False,
            'manual_verification': True
        }
    
    # Format description text (replace [original] placeholder)
    description_text = rule['description_text']
    if '[original]' in description_text:
        description_text = description_text.replace('[original]', verbatim_name)
    
    return {
        'name_to_use': rule['name_to_use'],
        'description_text': description_text,
        'check_ena': 'yes' if rule['check_ena'] else '',
        'manual_verification': 'yes' if rule['manual_verification'] else '',
        'gbif_key': gbif_key,
        'gbif_genus_key': gbif_genus_key,
        'verbatim_name': verbatim_name,
        'gbif_species': gbif_species,
        'gbif_genus': gbif_genus,
        'gbif_family': gbif_family,
        'gbif_order': row.get('gbif_order', '').strip(),
        'gbif_class': row.get('gbif_class', '').strip(),
        'gbif_phylum': row.get('gbif_phylum', '').strip(),
        'species_match': species_match,
        'genus_match': genus_match,
        'is_type': is_type,
        'status': status,
        'match_type': match_type,
        'sample_id': sample_id
    }


def process_file(input_file: str, rules_file: str, output_dir: str = None, project_id: str = 'BGE'):
    """
    Process the input file and generate output files.
    
    Outputs:
    1. {basename}_request_taxid.tsv - For 'original' names (proposed_name, name_type, host, project_id, description)
    2. {basename}_check_ENA.csv - For 'GBIF' names (ID, scientificName, genus, family, order, class, phylum)
    3. {basename}_annotated.csv - Copy of input with additional columns
    4. {basename}_manually_verify.csv - Rows needing manual verification (all input columns)
    """
    # Set up paths
    input_path = Path(input_file)
    basename = input_path.stem
    
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = input_path.parent
    
    # Load rules
    rules = load_rules(rules_file)
    
    # Prepare output files
    request_taxid_file = out_path / f"{basename}_request_taxid.tsv"
    check_ena_file = out_path / f"{basename}_check_ENA.csv"
    annotated_file = out_path / f"{basename}_annotated.csv"
    manually_verify_file = out_path / f"{basename}_manually_verify.csv"
    
    # Read input and process
    original_names = {}  # Dict keyed by proposed_name: {'gbif_key': str, 'is_type': bool}
    gbif_rows = []      # For check_ENA.csv
    annotated_rows = [] # For annotated.csv
    manually_verify_rows = []  # For manually_verify.csv
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames.copy()
        
        for row in reader:
            result = process_row(row, rules)
            
            # Build annotated row
            annotated_row = row.copy()
            annotated_row['name_to_use'] = result['name_to_use']
            annotated_row['description_text'] = result['description_text']
            annotated_row['check_ENA_with_GBIF'] = result['check_ena']
            annotated_row['manual_verification_needed'] = result['manual_verification']
            annotated_rows.append(annotated_row)
            
            # Route to appropriate output
            if result['name_to_use'] == 'original':
                proposed_name = result['verbatim_name']
                
                # Determine which key to use for URL (species key with genus key fallback)
                gbif_key = result['gbif_key']
                needs_manual_verify_for_fallback = False
                if not gbif_key or gbif_key.upper() == 'NOT_FOUND':
                    gbif_key = result['gbif_genus_key']
                    needs_manual_verify_for_fallback = True
                    # Also check if genus key is valid
                    if not gbif_key or gbif_key.upper() == 'NOT_FOUND':
                        gbif_key = ''
                
                # Track unique names and whether any instance is a type specimen
                if proposed_name in original_names:
                    # Update is_type to True if this instance is a type
                    if result['is_type']:
                        original_names[proposed_name]['is_type'] = True
                    # Update needs_manual_verify if this instance needs it
                    if needs_manual_verify_for_fallback:
                        original_names[proposed_name]['needs_manual_verify'] = True
                else:
                    original_names[proposed_name] = {
                        'gbif_key': gbif_key,
                        'is_type': result['is_type'],
                        'needs_manual_verify': needs_manual_verify_for_fallback
                    }
                
                # Add to manual verification if using genus key fallback AND not already flagged
                if needs_manual_verify_for_fallback and result['manual_verification'] != 'yes':
                    manually_verify_rows.append(row.copy())
            elif result['name_to_use'] == 'gbif':
                gbif_rows.append({
                    'ID': result['sample_id'],
                    'scientificName': result['gbif_species'],
                    'genus': result['gbif_genus'],
                    'family': result['gbif_family'],
                    'order': result['gbif_order'],
                    'class': result['gbif_class'],
                    'phylum': result['gbif_phylum']
                })
            
            # Collect rows needing manual verification
            if result['manual_verification'] == 'yes':
                manually_verify_rows.append(row.copy())
    
    # Build deduplicated original_rows list with TYPE annotation
    original_rows = []
    for proposed_name, info in original_names.items():
        gbif_link = f"https://www.gbif.org/species/{info['gbif_key']}" if info['gbif_key'] else ''
        if info['is_type']:
            description = f"{gbif_link} | TYPE" if gbif_link else "TYPE"
        else:
            description = gbif_link
        original_rows.append({
            'proposed_name': proposed_name,
            'name_type': 'published_name',
            'host': '',
            'project_id': project_id,
            'description': description
        })
    
    # Prepare log file
    log_file = out_path / f"{basename}.log"
    log_lines = []
    
    # Write request_taxid.tsv
    with open(request_taxid_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['proposed_name', 'name_type', 'host', 'project_id', 'description'], delimiter='\t')
        writer.writeheader()
        writer.writerows(original_rows)
    msg = f"Created: {request_taxid_file} ({len(original_rows)} rows)"
    print(msg)
    log_lines.append(msg)
    
    # Write check_ENA.csv
    with open(check_ena_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', 'scientificName', 'genus', 'family', 'order', 'class', 'phylum'])
        writer.writeheader()
        writer.writerows(gbif_rows)
    msg = f"Created: {check_ena_file} ({len(gbif_rows)} rows)"
    print(msg)
    log_lines.append(msg)
    
    # Write annotated.csv
    new_fieldnames = fieldnames + ['name_to_use', 'description_text', 'check_ENA_with_GBIF', 'manual_verification_needed']
    with open(annotated_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(annotated_rows)
    msg = f"Created: {annotated_file} ({len(annotated_rows)} rows)"
    print(msg)
    log_lines.append(msg)
    
    # Write manually_verify.csv
    with open(manually_verify_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manually_verify_rows)
    msg = f"Created: {manually_verify_file} ({len(manually_verify_rows)} rows)"
    print(msg)
    log_lines.append(msg)
    
    # Print summary
    not_possible = sum(1 for r in annotated_rows if r['name_to_use'] == 'not a possible combination')
    unknown = sum(1 for r in annotated_rows if r['name_to_use'] == 'unknown')
    total_original_records = sum(1 for r in annotated_rows if r['name_to_use'] == 'original')
    
    summary_lines = [
        "",
        "Summary:",
        f"  Original: {len(original_rows)} unique names ({total_original_records} total records)",
        f"  GBIF: {len(gbif_rows)}",
        f"  Manual verification: {len(manually_verify_rows)}",
        f"  Not possible: {not_possible}",
        f"  Unknown (no matching rule): {unknown}"
    ]
    
    for line in summary_lines:
        print(line)
        log_lines.append(line)
    
    # Write log file
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines) + '\n')
    print(f"\nLog saved: {log_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Process GBIF species match output against rules matrix.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Outputs:
  {input_basename}_request_taxid.tsv  - Names to use as original (with GBIF hyperlinks)
  {input_basename}_check_ENA.csv      - Names to check in ENA with GBIF name
  {input_basename}_annotated.csv      - Full input with decision columns added
  {input_basename}_manually_verify.csv - Rows needing manual verification

Example:
  python gbif_name_processor.py -i XE-4013_output.csv -r gbif_rules.csv -p BGE
        """
    )
    parser.add_argument('-i', '--input', required=True, help='Input CSV file (GBIF match output)')
    parser.add_argument('-r', '--rules', required=True, help='Rules CSV file')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: same as input)')
    parser.add_argument('-p', '--project-id', default='BGE', help='Project ID for taxonomy requests (default: BGE)')
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not os.path.isfile(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(args.rules):
        print(f"Error: Rules file not found: {args.rules}", file=sys.stderr)
        sys.exit(1)
    
    # Create output directory if specified and doesn't exist
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
    
    process_file(args.input, args.rules, args.output_dir, args.project_id)


if __name__ == '__main__':
    main()
