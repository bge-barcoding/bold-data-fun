#!/usr/bin/env python3
"""
Gap analysis for BOLD library curation workflow.

This script performs a gap analysis by comparing:
1. Input species list (from config FILTER_TAXA_LIST or --species-list)
   - Supports simple CSV format: species;synonym1;synonym2
   - Supports TSV format with headers (auto-detected by .tsv extension)
2. Result output data (result_output.tsv)
3. BAGS assessment data (assessed_BAGS.tsv)

The script identifies:
- Species from the input list and their coverage
- Additional species found in results but not in input list (missed species)
- BAGS grades and BIN information for all species
- Record counts per taxonid

Output: A comprehensive TSV file with gap analysis results.
When using TSV input, all input columns are preserved in the output.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import yaml

# Increase CSV field size limit to handle large TSV files
# Use a large but safe value for Windows compatibility
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # Windows workaround
    csv.field_size_limit(2147483647)


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_config(config_path: Path) -> Dict:
    """Load configuration from YAML file."""
    logging.info(f"Loading configuration from {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        sys.exit(1)


def format_species_name(species_lower: str) -> str:
    """
    Format species name to proper binomial nomenclature: Genus species
    (capitalize only the first word/genus, keep species lowercase)
    
    Examples:
        'anax parthenope' -> 'Anax parthenope'
        'acisoma inflatum' -> 'Acisoma inflatum'
    """
    parts = species_lower.split()
    if len(parts) >= 2:
        # Capitalize first word (genus), keep rest lowercase
        return parts[0].capitalize() + ' ' + ' '.join(parts[1:])
    elif len(parts) == 1:
        # Just genus name
        return parts[0].capitalize()
    return species_lower


def is_linnean_name(name: str) -> bool:
    """
    Determine if a species name is a proper Linnean binomial.
    
    Returns True if:
    - Format is "Genus species" or "Genus species subspecies"
    - No: sp., cf., aff., numbers, DNAS codes, BOLD codes
    - No: extra punctuation beyond standard binomial
    - Genus capitalized, species epithet lowercase
    
    Returns False for:
    - "Gammarus sp."
    - "Gammarus cf. fossarum"
    - "Enallagma sp. DNAS-283-223485"
    - "Gammarus sp. 2118c"
    - Genus-only names
    
    Args:
        name: Species name to check
        
    Returns:
        bool: True if proper Linnean binomial, False otherwise
    """
    if not name or not name.strip():
        return False
    
    name = name.strip()
    
    # Check for non-Linnean indicators
    non_linnean_patterns = [
        'sp.', 'sp ', ' sp', 
        'cf.', 'cf ', ' cf',
        'aff.', 'aff ', ' aff',
        'DNAS', 'BOLD:',
    ]
    
    for pattern in non_linnean_patterns:
        if pattern in name:
            return False
    
    # Check for numbers (but allow Roman numerals in author names)
    # We'll be conservative: any digit is non-Linnean
    if any(char.isdigit() for char in name):
        return False
    
    # Split into parts
    parts = name.split()
    
    # Must have at least 2 parts (Genus species) or 3 (Genus species subspecies)
    if len(parts) < 2:
        return False
    
    # Too many parts suggests non-Linnean (codes, identifiers, etc.)
    if len(parts) > 3:
        return False
    
    # First part (genus) should be capitalized
    genus = parts[0]
    if not genus[0].isupper():
        return False
    
    # Species epithet should be lowercase (and subspecies if present)
    for epithet in parts[1:]:
        if not epithet[0].islower():
            return False
    
    return True


def infer_taxonomy_from_genus(species_name: str, genus_to_taxonomy: Dict[str, List[Dict]]) -> Dict:
    """
    Infer higher taxonomy for a species by finding congeneric species in BOLD data.
    
    Args:
        species_name: Species binomial (e.g., "trocheta pseudodina" - lowercase)
        genus_to_taxonomy: Pre-built dict mapping genus -> list of taxonomy dicts
    
    Returns:
        Dict with:
        - taxonomy: Dict[str, str] - kingdom, phylum, class, order, family, genus
        - source: str - "Inferred from genus" | "Inconsistent genus taxonomy" | "No genus data"
        - genus_species_found: List[str] - Which species were used for inference (max 5)
    """
    # Extract genus (first word)
    genus = species_name.split()[0] if ' ' in species_name else species_name
    
    # Look up genus in pre-built mapping
    if genus not in genus_to_taxonomy or not genus_to_taxonomy[genus]:
        return {
            'taxonomy': {
                'kingdom': '',
                'phylum': '',
                'class': '',
                'order': '',
                'family': '',
                'genus': genus
            },
            'source': 'No genus data',
            'genus_species_found': []
        }
    
    taxonomy_list = genus_to_taxonomy[genus]
    
    # Check for consensus - all taxonomies should be identical
    first_tax = taxonomy_list[0]
    
    all_same = all(
        tax['kingdom'] == first_tax['kingdom'] and
        tax['phylum'] == first_tax['phylum'] and
        tax['class'] == first_tax['class'] and
        tax['order'] == first_tax['order'] and
        tax['family'] == first_tax['family']
        for tax in taxonomy_list
    )
    
    species_found = [tax['species'] for tax in taxonomy_list]
    
    if all_same:
        return {
            'taxonomy': {
                'kingdom': first_tax['kingdom'],
                'phylum': first_tax['phylum'],
                'class': first_tax['class'],
                'order': first_tax['order'],
                'family': first_tax['family'],
                'genus': genus
            },
            'source': 'Inferred from genus',
            'genus_species_found': species_found[:5]  # Limit to first 5 for brevity
        }
    else:
        # Inconsistent - use first found but flag it
        return {
            'taxonomy': {
                'kingdom': first_tax['kingdom'],
                'phylum': first_tax['phylum'],
                'class': first_tax['class'],
                'order': first_tax['order'],
                'family': first_tax['family'],
                'genus': genus
            },
            'source': 'Inconsistent genus taxonomy',
            'genus_species_found': species_found[:5]
        }


def analyze_synonym_bin_distribution(
    valid_species: str,
    synonyms: List[str],
    species_to_bins: Dict[str, Set[str]]
) -> Dict:
    """
    Analyze BIN distribution for valid species vs synonyms.
    
    Checks if synonyms are in the same BINs as the valid species, or in different BINs
    (which would be a taxonomic red flag).
    
    Args:
        valid_species: Valid species name (lowercase)
        synonyms: List of synonym names (original case)
        species_to_bins: Dict mapping species (lowercase) -> set of BIN_uris
    
    Returns:
        Dict with:
        - status: str - "Same BIN" | "Different BINs" | "Partial overlap" | 
                       "No synonym data" | "No valid data" | "N/A"
        - details: str - Formatted BIN details (e.g., "Syn1:BIN1|BIN2; Syn2:BIN3")
    """
    # Check if species has no synonyms
    if not synonyms or len(synonyms) == 0:
        return {
            'status': 'N/A',
            'details': ''
        }
    
    # Get BINs for valid species
    valid_bins = species_to_bins.get(valid_species.lower(), set())
    
    if not valid_bins:
        return {
            'status': 'No valid data',
            'details': ''
        }
    
    # Analyze each synonym
    synonym_bin_info = []
    all_synonym_bins = set()
    synonyms_with_data = 0
    synonyms_in_same_bins = 0
    synonyms_in_different_bins = 0
    synonyms_with_overlap = 0
    
    for synonym in synonyms:
        synonym_lower = synonym.lower()
        synonym_bins = species_to_bins.get(synonym_lower, set())
        
        if not synonym_bins:
            # Synonym not found in data
            continue
        
        synonyms_with_data += 1
        all_synonym_bins.update(synonym_bins)
        
        # Check overlap with valid species BINs
        shared_bins = valid_bins.intersection(synonym_bins)
        unique_bins = synonym_bins.difference(valid_bins)
        
        if shared_bins and not unique_bins:
            # All synonym BINs are shared with valid species
            synonyms_in_same_bins += 1
        elif unique_bins and not shared_bins:
            # Synonym in completely different BINs
            synonyms_in_different_bins += 1
        else:
            # Partial overlap
            synonyms_with_overlap += 1
        
        # Format BIN details for this synonym
        bin_list = sorted(list(synonym_bins))
        synonym_bin_info.append(f"{synonym}:{' | '.join(bin_list)}")
    
    # If no synonyms found in data
    if synonyms_with_data == 0:
        return {
            'status': 'No synonym data',
            'details': ''
        }
    
    # Determine overall status
    details = '; '.join(synonym_bin_info)
    
    if synonyms_in_different_bins > 0 or synonyms_with_overlap > 0:
        # ANY synonym in different or partially overlapping BINs = concern
        if synonyms_in_different_bins > 0 and synonyms_with_overlap == 0:
            status = 'Different BINs'
        elif synonyms_with_overlap > 0 and synonyms_in_different_bins == 0:
            status = 'Partial overlap'
        else:
            status = 'Different BINs'  # If both types exist, use most severe
    else:
        # All synonyms in same BINs as valid species
        status = 'Same BIN'
    
    return {
        'status': status,
        'details': details
    }


def check_name_representation(
    valid_species: str,
    synonyms: List[str],
    all_species_in_results: Set[str],
    species_taxonid_map: Dict,
    taxonid_record_count: Dict
) -> Dict:
    """
    Check whether valid name and/or synonyms appear in dataset.
    
    Identifies cases where a species is only represented by its synonym names
    (valid name absent), which is a curation concern.
    
    Args:
        valid_species: Valid species name (lowercase)
        synonyms: List of synonym names (original case)
        all_species_in_results: Set of all species names (lowercase) found in results
        species_taxonid_map: Dict mapping species (lowercase) -> list of (taxonid, taxonomy_dict)
        taxonid_record_count: Dict mapping taxonid -> count of records
    
    Returns:
        Dict with:
        - representation: str - "Valid name only" | "Valid + synonym(s)" | 
                               "Synonym only" | "No records" | "N/A - no synonyms"
        - names_with_records: str - Comma-separated list of names found
        - synonym_record_count: int - Total records across all found synonyms (0 if none)
        - synonym_only_flag: str - "⚠️" if synonym-only, else ""
    """
    # Check if species has no synonyms
    if not synonyms or len(synonyms) == 0:
        # No synonyms to check
        if valid_species in all_species_in_results:
            return {
                'representation': 'N/A - no synonyms',
                'names_with_records': format_species_name(valid_species),
                'synonym_record_count': 0,
                'synonym_only_flag': ''
            }
        else:
            return {
                'representation': 'N/A - no synonyms',
                'names_with_records': '',
                'synonym_record_count': 0,
                'synonym_only_flag': ''
            }
    
    # Check which names are found
    valid_found = valid_species in all_species_in_results
    
    synonyms_found = []
    synonym_record_count = 0
    for syn in synonyms:
        syn_lower = syn.lower()
        if syn_lower in all_species_in_results:
            synonyms_found.append(syn)
            # Sum records across all taxonids for this synonym
            if syn_lower in species_taxonid_map:
                for taxonid, _ in species_taxonid_map[syn_lower]:
                    synonym_record_count += taxonid_record_count.get(taxonid, 0)
    
    # Determine representation status
    if valid_found and synonyms_found:
        # Both valid and synonym(s) have records
        all_names = [format_species_name(valid_species)] + synonyms_found
        return {
            'representation': 'Valid + synonym(s)',
            'names_with_records': ','.join(all_names),
            'synonym_record_count': synonym_record_count,
            'synonym_only_flag': ''
        }
    elif valid_found and not synonyms_found:
        # Only valid name has records
        return {
            'representation': 'Valid name only',
            'names_with_records': format_species_name(valid_species),
            'synonym_record_count': synonym_record_count,
            'synonym_only_flag': ''
        }
    elif not valid_found and synonyms_found:
        # PROBLEM: Only synonym(s) have records, valid name absent
        return {
            'representation': 'Synonym only',
            'names_with_records': ','.join(synonyms_found),
            'synonym_record_count': synonym_record_count,
            'synonym_only_flag': '⚠️'
        }
    else:
        # Neither valid nor synonyms found
        return {
            'representation': 'No records',
            'names_with_records': '',
            'synonym_record_count': synonym_record_count,
            'synonym_only_flag': ''
        }


def determine_species_category(
    species: str,
    taxonid_bins: Set[str],
    valid_species_set: Set[str],
    synonym_to_valid: Dict[str, str],
    all_input_species_bins: Set[str],
    bin_to_species: Dict[str, Set[str]]
) -> Dict:
    """
    Categorize species and find associated input species if applicable.
    
    Determines whether a species is:
    - Valid (from input list)
    - Synonym (from input list)
    - Extra species (not on list, doesn't share BIN with input species)
    - Extra BIN (shares BIN with input species)
    
    Args:
        species: Species name (lowercase)
        taxonid_bins: Set of BIN URIs for this specific taxonid
        valid_species_set: Set of valid species names (original case) from input
        synonym_to_valid: Dict mapping synonym (lowercase) -> valid species (lowercase)
        all_input_species_bins: Set of all BIN URIs associated with input species
        bin_to_species: Dict mapping BIN_uri -> set of species (lowercase)
    
    Returns:
        Dict with:
        - category: str - "Valid" | "Synonym" | "Extra species" | "Extra BIN"
        - associated_input_species: str - Comma-separated list of input species sharing BINs
    """
    species_lower = species.lower()
    
    # Check if species is a valid species from input list (case-insensitive)
    valid_species_lower = {v.lower() for v in valid_species_set}
    if species_lower in valid_species_lower:
        return {
            'category': 'Valid',
            'associated_input_species': ''
        }
    
    # Check if species is a synonym from input list
    if species_lower in synonym_to_valid:
        return {
            'category': 'Synonym',
            'associated_input_species': ''
        }
    
    # Not on input list - check if it shares BINs with input species
    if not taxonid_bins:
        # No BINs for this taxonid
        return {
            'category': 'Extra species',
            'associated_input_species': ''
        }
    
    # Check if any of this species' BINs overlap with input species BINs
    shared_bins = taxonid_bins.intersection(all_input_species_bins)
    
    if shared_bins:
        # This species shares BINs with input species
        # Find which input species share these BINs
        associated_species = set()
        
        for bin_uri in shared_bins:
            # Get all species in this BIN
            species_in_bin = bin_to_species.get(bin_uri, set())
            
            # Filter to only input species (valid or synonym)
            for sp in species_in_bin:
                # Check if this is a valid species or synonym from input
                if sp in valid_species_set or sp.lower() in [v.lower() for v in valid_species_set]:
                    associated_species.add(format_species_name(sp))
                elif sp in synonym_to_valid:
                    # Add the valid species this synonym maps to
                    valid_sp = synonym_to_valid[sp]
                    associated_species.add(format_species_name(valid_sp))
        
        return {
            'category': 'Extra BIN',
            'associated_input_species': ','.join(sorted(associated_species))
        }
    else:
        # Doesn't share any BINs with input species
        return {
            'category': 'Extra species',
            'associated_input_species': ''
        }


def analyze_sharer_names(
    sharers: str,
    focal_species: str,
    species_synonyms: Dict[str, List[str]],
    synonym_to_valid: Dict[str, str]
) -> Dict:
    """
    Analyze sharers for BAGS E assessment.
    
    For BAGS grade E (multiple species sharing a BIN), this analyzes:
    1. Whether sharers are known synonyms from the input list
    2. Whether sharer names are proper Linnean binomials
    
    Args:
        sharers: Pipe-separated list of species names sharing the BIN
        focal_species: The species being analyzed (lowercase)
        species_synonyms: Dict mapping valid species (lowercase) -> list of synonyms
        synonym_to_valid: Dict mapping synonym (lowercase) -> valid species (lowercase)
    
    Returns:
        Dict with:
        - sharer_status: str - "All known synonyms" | "Mix (synonyms + extras)" | 
                              "No known synonyms" | "N/A - not on list"
        - sharer_type: str - "All Linnean" | "Contains non-Linnean"
    """
    if not sharers or sharers.strip() == '':
        return {
            'sharer_status': '',
            'sharer_type': ''
        }
    
    # Split sharers - handle both pipe and comma separators
    # First split on pipe, then split each part on comma
    sharer_list = []
    for part in sharers.split('|'):
        part = part.strip()
        if part:
            # Split on comma and add each individual sharer
            for sharer in part.split(','):
                sharer = sharer.strip()
                if sharer:
                    sharer_list.append(sharer)
    
    if not sharer_list:
        return {
            'sharer_status': '',
            'sharer_type': ''
        }
    
    # Check if focal species is on the input list
    focal_on_list = (focal_species in species_synonyms or 
                     focal_species in synonym_to_valid)
    
    if not focal_on_list:
        # Cannot assess synonym status if focal species not on input list
        sharer_status = 'N/A - not on list'
    else:
        # Analyze synonym status
        known_synonyms = 0
        unknown_species = 0
        
        # Get all synonyms from input list (for any valid species)
        all_input_synonyms = set()
        for valid_sp, syn_list in species_synonyms.items():
            all_input_synonyms.update([s.lower() for s in syn_list])
        
        for sharer in sharer_list:
            sharer_lower = sharer.lower()
            
            # Check if this sharer is a known synonym or valid species from input
            if (sharer_lower in all_input_synonyms or 
                sharer_lower in species_synonyms):
                known_synonyms += 1
            else:
                unknown_species += 1
        
        # Determine status
        if known_synonyms > 0 and unknown_species == 0:
            sharer_status = 'All known synonyms'
        elif known_synonyms > 0 and unknown_species > 0:
            sharer_status = 'Mix (synonyms + extras)'
        else:
            sharer_status = 'No known synonyms'
    
    # Analyze Linnean name format
    all_linnean = True
    for sharer in sharer_list:
        if not is_linnean_name(sharer):
            all_linnean = False
            break
    
    if all_linnean:
        sharer_type = 'All Linnean'
    else:
        sharer_type = 'Contains non-Linnean'
    
    return {
        'sharer_status': sharer_status,
        'sharer_type': sharer_type
    }


def determine_species_status(
    species_category: str,
    total_record_count: int,
    synonym_record_count: int,
    bags_grade: str,
    bags_e_sharer_status: str,
    synonym_bin_status: str,
    name_representation: str
) -> str:
    """
    Determine traffic light status for a species based on data quality indicators.
    
    Priority order (worst to best): Black → Red → Amber → Blue → Green
    
    Args:
        species_category: Valid, Synonym, Extra species, or Extra BIN
        total_record_count: Number of BOLD records for valid species
        synonym_record_count: Total records across all synonyms
        bags_grade: BAGS grade (A-E) or empty
        bags_e_sharer_status: For BAGS E - All known synonyms, Mix, No known synonyms, or N/A
        synonym_bin_status: Same BIN, Different BINs, Partial overlap, No data, or N/A
        name_representation: Valid name only, Valid + synonym(s), Synonym only, No records, or N/A
    
    Returns:
        str: Species status - Green, Amber, Red, Blue, Black, or N/A
    """
    # N/A - Not a target species from input list
    if species_category in ('Extra BIN', 'Extra species', 'Synonym'):
        return 'N/A'
    
    # BLACK - No coverage at all
    if total_record_count == 0 and synonym_record_count == 0:
        return 'Black'
    
    # RED - Serious issues requiring investigation
    # BAGS E with unknown or mixed sharers
    if bags_grade == 'E' and bags_e_sharer_status in ('No known synonyms', 'Mix (synonyms + extras)'):
        return 'Red'
    # Synonyms in completely different BINs (taxonomic concern)
    if synonym_bin_status == 'Different BINs':
        return 'Red'
    
    # AMBER - Known issues, synonymy/taxonomy needs work
    # BAGS E but all sharers are known synonyms
    if bags_grade == 'E' and bags_e_sharer_status == 'All known synonyms':
        return 'Amber'
    # Partial BIN overlap between valid and synonyms
    if synonym_bin_status == 'Partial overlap':
        return 'Amber'
    # Both valid name and synonym(s) have records
    if name_representation == 'Valid + synonym(s)':
        return 'Amber'
    
    # BLUE - Nomenclatural issue (valid name absent)
    if name_representation == 'Synonym only':
        return 'Blue'
    
    # GREEN - Clean, no issues
    return 'Green'


def get_all_input_species_bins(
    species_synonyms: Dict[str, List[str]],
    species_to_bins: Dict[str, Set[str]]
) -> Set[str]:
    """
    Get all BINs associated with input species list (valid species + synonyms).
    
    This is used to identify "Extra BIN" category - species not on the input list
    but sharing BINs with species that are on the list.
    
    Args:
        species_synonyms: Dict mapping valid species (lowercase) -> list of synonyms
        species_to_bins: Dict mapping species (lowercase) -> set of BIN_uris
    
    Returns:
        Set[str]: All BIN URIs associated with input species
    """
    all_bins = set()
    
    # Get BINs for all valid species
    for valid_species in species_synonyms.keys():
        bins = species_to_bins.get(valid_species, set())
        all_bins.update(bins)
    
    # Get BINs for all synonyms
    for valid_species, synonyms in species_synonyms.items():
        for synonym in synonyms:
            synonym_lower = synonym.lower()
            bins = species_to_bins.get(synonym_lower, set())
            all_bins.update(bins)
    
    return all_bins


def parse_species_list_simple(species_file: Path) -> Tuple[Dict[str, List[str]], Set[str], Dict[str, str], Dict[str, Dict], List[str]]:
    """
    Parse simple species list format (one species per line, semicolon-separated synonyms).
    
    Format: valid_species OR valid_species;synonym1;synonym2;etc
    
    Returns:
        Tuple of:
        - Dictionary mapping valid species (lowercase) to list of synonyms
        - Set of all valid species names (original case)
        - Dictionary mapping synonym (lowercase) to valid species (lowercase)
        - Dictionary mapping valid species (lowercase) to input row data (empty for simple format)
        - List of input column names (empty for simple format)
    """
    logging.info(f"Loading simple species list from {species_file}")
    species_synonyms = {}  # lowercase valid species -> list of synonyms
    valid_species_set = set()  # original case valid species
    synonym_to_valid = {}  # lowercase synonym -> lowercase valid species
    species_input_data = {}  # No additional data for simple format
    input_columns = []  # No columns for simple format
    
    try:
        with open(species_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(';')
                valid_species = parts[0].strip()
                
                if not valid_species:
                    logging.warning(f"Line {line_num}: Empty species name, skipping")
                    continue
                
                # Store with lowercase key for case-insensitive matching
                key = valid_species.lower()
                
                # Get synonyms (if any)
                synonyms = [s.strip() for s in parts[1:] if s.strip()]
                
                if key in species_synonyms:
                    logging.warning(f"Duplicate species found: {valid_species}")
                
                species_synonyms[key] = synonyms
                valid_species_set.add(valid_species)
                species_input_data[key] = {}  # Empty dict for simple format
                
                # Build synonym to valid species mapping
                for syn in synonyms:
                    synonym_to_valid[syn.lower()] = key
        
        logging.info(f"Loaded {len(species_synonyms)} species from simple input list")
        total_synonyms = sum(len(syns) for syns in species_synonyms.values())
        logging.info(f"Total synonyms: {total_synonyms}")
        
        return species_synonyms, valid_species_set, synonym_to_valid, species_input_data, input_columns
        
    except Exception as e:
        logging.error(f"Failed to load species list: {e}")
        sys.exit(1)


def parse_species_list_tsv(species_file: Path) -> Tuple[Dict[str, List[str]], Set[str], Dict[str, str], Dict[str, Dict], List[str]]:
    """
    Parse TSV species list format with headers.
    
    Expected columns:
    - 'species': Full binomial species name (required)
    - 'synonyms': Semicolon-separated synonyms (optional, can be empty)
    - Any additional columns are preserved in output
    
    Returns:
        Tuple of:
        - Dictionary mapping valid species (lowercase) to list of synonyms
        - Set of all valid species names (original case)
        - Dictionary mapping synonym (lowercase) to valid species (lowercase)
        - Dictionary mapping valid species (lowercase) to full input row data
        - List of input column names (preserves order)
    """
    logging.info(f"Loading TSV species list from {species_file}")
    species_synonyms = {}  # lowercase valid species -> list of synonyms
    valid_species_set = set()  # original case valid species
    synonym_to_valid = {}  # lowercase synonym -> lowercase valid species
    species_input_data = {}  # lowercase valid species -> dict of all input columns
    input_columns = []  # Ordered list of input column names
    
    # Try UTF-8 first, fall back to Latin-1 if decoding fails
    for encoding in ['utf-8', 'latin-1']:
        try:
            with open(species_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                # Capture column names from header (preserves order)
                input_columns = list(reader.fieldnames) if reader.fieldnames else []
                
                if 'species' not in input_columns:
                    logging.error("TSV file must have a 'species' column")
                    sys.exit(1)
                
                logging.info(f"Found {len(input_columns)} columns in TSV: {', '.join(input_columns)}")
                
                for row_num, row in enumerate(reader, 2):  # Start at 2 (header is row 1)
                    valid_species = row.get('species', '').strip()
                    
                    if not valid_species:
                        logging.warning(f"Row {row_num}: Empty species name, skipping")
                        continue
                    
                    # Store with lowercase key for case-insensitive matching
                    key = valid_species.lower()
                    
                    # Get synonyms from 'synonyms' column (semicolon-separated)
                    synonyms_field = row.get('synonyms', '').strip()
                    synonyms = [s.strip() for s in synonyms_field.split(';') if s.strip()]
                    
                    if key in species_synonyms:
                        logging.warning(f"Duplicate species found: {valid_species}")
                    
                    species_synonyms[key] = synonyms
                    valid_species_set.add(valid_species)
                    
                    # Store ALL input columns for this species
                    species_input_data[key] = {col: row.get(col, '').strip() for col in input_columns}
                    
                    # Build synonym to valid species mapping
                    for syn in synonyms:
                        synonym_to_valid[syn.lower()] = key
            
            # If we successfully read the file, log success and return
            if encoding == 'latin-1':
                logging.info(f"Successfully read file using {encoding} encoding")
            logging.info(f"Loaded {len(species_synonyms)} species from TSV input list")
            total_synonyms = sum(len(syns) for syns in species_synonyms.values())
            logging.info(f"Total synonyms: {total_synonyms}")
            
            return species_synonyms, valid_species_set, synonym_to_valid, species_input_data, input_columns
            
        except UnicodeDecodeError as e:
            if encoding == 'utf-8':
                logging.warning(f"UTF-8 decoding failed, trying Latin-1 encoding")
                # Reset for retry
                species_synonyms = {}
                valid_species_set = set()
                synonym_to_valid = {}
                species_input_data = {}
                input_columns = []
                continue
            else:
                logging.error(f"Failed to load TSV with Latin-1 encoding: {e}")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to load TSV species list: {e}")
            sys.exit(1)
    
    # Should never reach here
    logging.error("Failed to load TSV species list with any supported encoding")
    sys.exit(1)


def parse_species_list(species_file: Path) -> Tuple[Dict[str, List[str]], Set[str], Dict[str, str], Dict[str, Dict], List[str]]:
    """
    Parse species list, auto-detecting format based on file extension.
    
    - .tsv files: Parsed as TSV with headers
    - Other files (.csv, .txt, no extension): Parsed as simple format
    
    Returns:
        Tuple of:
        - Dictionary mapping valid species (lowercase) to list of synonyms
        - Set of all valid species names (original case)
        - Dictionary mapping synonym (lowercase) to valid species (lowercase)
        - Dictionary mapping valid species (lowercase) to input row data
        - List of input column names
    """
    suffix = species_file.suffix.lower()
    
    if suffix == '.tsv':
        logging.info("Detected TSV format based on file extension")
        return parse_species_list_tsv(species_file)
    else:
        logging.info("Using simple format (not .tsv extension)")
        return parse_species_list_simple(species_file)


def load_assessed_bags(bags_file: Path) -> Dict[str, Dict]:
    """
    Load BAGS assessment data.
    
    Handles both UTF-8 and Latin-1 encoded files automatically.
    Supports both 'taxonid' (BOLD format) and 'taxid' (MIDORI format) column names.
    Supports both 'BIN' (BOLD format) and 'OTU_ID' (MIDORI format) for identifiers.
    
    Returns dictionary: taxonid -> {BAGS: grade, BIN: uri, sharers: list}
    """
    logging.info(f"Loading BAGS assessments from {bags_file}")
    bags_data = {}
    
    # Try UTF-8 first, fall back to Latin-1 if decoding fails
    for encoding in ['utf-8', 'latin-1']:
        try:
            with open(bags_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                # Detect column names from header
                fieldnames = reader.fieldnames or []
                taxon_col = 'taxonid' if 'taxonid' in fieldnames else 'taxid'
                bin_col = 'BIN' if 'BIN' in fieldnames else 'OTU_ID'
                
                logging.info(f"BAGS file using taxon column: '{taxon_col}', identifier column: '{bin_col}'")
                
                for row in reader:
                    taxonid = row.get(taxon_col, '').strip()
                    if not taxonid:
                        continue
                    
                    bags_data[taxonid] = {
                        'BAGS': row.get('BAGS', '').strip(),
                        'BIN': row.get(bin_col, '').strip(),
                        'sharers': row.get('sharers', '').strip()
                    }
            
            # If we successfully read the file, log and return
            if encoding == 'latin-1':
                logging.info(f"Successfully read file using {encoding} encoding")
            logging.info(f"Loaded BAGS data for {len(bags_data)} taxonids")
            return bags_data
            
        except UnicodeDecodeError as e:
            if encoding == 'utf-8':
                logging.warning(f"UTF-8 decoding failed for BAGS file, trying Latin-1 encoding")
                bags_data = {}  # Reset for retry
                continue
            else:
                logging.error(f"Failed to load BAGS data with Latin-1 encoding: {e}")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to load BAGS data: {e}")
            sys.exit(1)
    
    # Should never reach here
    logging.error("Failed to load BAGS data with any supported encoding")
    sys.exit(1)


def load_result_output(result_file: Path) -> Tuple[Dict, Dict, Dict, Dict, Set, Dict]:
    """
    Load result_output.tsv and extract species information with enhanced data structures.
    
    Includes subspecies in the full species name (e.g., "Genus species subspecies")
    
    Handles both UTF-8 and Latin-1 encoded files automatically.
    Supports both 'taxonid' (BOLD format) and 'taxid' (MIDORI format) column names.
    Supports both 'bin_uri' (BOLD format) and 'OTU_ID' (MIDORI format) for identifiers.
    
    Returns:
        Tuple of:
        - species_taxonid_map: dict mapping species (lowercase) -> list of (taxonid, taxonomy_dict)
        - taxonid_record_count: dict mapping taxonid -> count of records
        - species_to_bins: dict mapping species (lowercase) -> set of BIN_uris/OTU_IDs
        - bin_to_species: dict mapping BIN_uri/OTU_ID -> set of species (lowercase)
        - all_species_in_results: set of all species names (lowercase) found in results
        - genus_to_taxonomy: dict mapping genus -> list of taxonomy dicts
    """
    logging.info(f"Loading result output from {result_file}")
    
    species_taxonid_map = defaultdict(list)
    taxonid_record_count = defaultdict(int)
    species_to_bins = defaultdict(set)
    bin_to_species = defaultdict(set)
    all_species_in_results = set()
    genus_to_taxonomy = defaultdict(list)
    subspecies_count = 0
    
    # Try UTF-8 first, fall back to Latin-1 if decoding fails
    for encoding in ['utf-8', 'latin-1']:
        try:
            with open(result_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                # Detect column names from header
                fieldnames = reader.fieldnames or []
                taxon_col = 'taxonid' if 'taxonid' in fieldnames else 'taxid'
                bin_col = 'bin_uri' if 'bin_uri' in fieldnames else 'OTU_ID'
                
                logging.info(f"Result file using taxon column: '{taxon_col}', identifier column: '{bin_col}'")
                
                for row in reader:
                    species_full = row.get('species', '').strip()
                    subspecies = row.get('subspecies', '').strip()
                    taxonid = row.get(taxon_col, '').strip()
                    bin_field = row.get(bin_col, '').strip()
                    
                    if not species_full or not taxonid:
                        continue
                    
                    # If subspecies exists, include it in the full species name
                    if subspecies and subspecies.lower() not in ['none', 'null', '']:
                        # Subspecies field may contain full trinomial (e.g., "Genus species subspecies")
                        # Extract just the subspecies epithet (last word)
                        subspecies_parts = subspecies.split()
                        if len(subspecies_parts) >= 3:
                            # Full trinomial provided, take the last word
                            subspecies_epithet = subspecies_parts[-1]
                        else:
                            # Just subspecies epithet provided
                            subspecies_epithet = subspecies
                        
                        # Create full trinomial: "Genus species subspecies"
                        species = f"{species_full} {subspecies_epithet}"
                        subspecies_count += 1
                    else:
                        species = species_full
                    
                    species_lower = species.lower()
                    
                    # Count records per taxonid
                    taxonid_record_count[taxonid] += 1
                    
                    # Track all species names in results
                    all_species_in_results.add(species_lower)
                    
                    # Parse BIN URIs (may be pipe-separated)
                    bin_uris = []
                    if bin_field:
                        # Split on pipe and clean up each BIN
                        bin_uris = [b.strip() for b in bin_field.split('|') if b.strip()]
                    
                    # Build species-BIN mappings
                    for bin_uri in bin_uris:
                        species_to_bins[species_lower].add(bin_uri)
                        bin_to_species[bin_uri].add(species_lower)
                    
                    # Extract taxonomy (only add once per species-taxonid combo)
                    existing_taxonids = [t for t, _ in species_taxonid_map[species_lower]]
                    if taxonid not in existing_taxonids:
                        taxonomy = {
                            'kingdom': row.get('kingdom', '').strip(),
                            'phylum': row.get('phylum', '').strip(),
                            'class': row.get('class', '').strip(),
                            'order': row.get('order', '').strip(),
                            'family': row.get('family', '').strip(),
                            'genus': row.get('genus', '').strip()
                        }
                        species_taxonid_map[species_lower].append((taxonid, taxonomy))
                        
                        # Build genus-to-taxonomy mapping for inference
                        genus = species_lower.split()[0] if ' ' in species_lower else species_lower
                        
                        # Check if this taxonomy already exists for this genus
                        tax_dict = {
                            'species': species_lower,
                            'kingdom': taxonomy.get('kingdom', ''),
                            'phylum': taxonomy.get('phylum', ''),
                            'class': taxonomy.get('class', ''),
                            'order': taxonomy.get('order', ''),
                            'family': taxonomy.get('family', '')
                        }
                        
                        # Only add if not already present (same taxonomy)
                        if not any(
                            existing['kingdom'] == tax_dict['kingdom'] and
                            existing['phylum'] == tax_dict['phylum'] and
                            existing['class'] == tax_dict['class'] and
                            existing['order'] == tax_dict['order'] and
                            existing['family'] == tax_dict['family']
                            for existing in genus_to_taxonomy[genus]
                        ):
                            genus_to_taxonomy[genus].append(tax_dict)
            
            # If we successfully read the file, log success and return
            if encoding == 'latin-1':
                logging.info(f"Successfully read file using {encoding} encoding")
            logging.info(f"Loaded {len(species_taxonid_map)} unique species from result output")
            logging.info(f"Found {subspecies_count} subspecies records")
            logging.info(f"Processed {sum(taxonid_record_count.values())} total records")
            logging.info(f"Found {len(taxonid_record_count)} unique taxonids")
            logging.info(f"Built genus-to-taxonomy mapping for {len(genus_to_taxonomy)} genera")
            logging.info(f"Tracked {len(all_species_in_results)} unique species names")
            
            return (
                dict(species_taxonid_map),
                dict(taxonid_record_count),
                dict(species_to_bins),
                dict(bin_to_species),
                all_species_in_results,
                dict(genus_to_taxonomy)
            )
            
        except UnicodeDecodeError as e:
            if encoding == 'utf-8':
                logging.warning(f"UTF-8 decoding failed at position {e.start}, trying Latin-1 encoding")
                # Reset counters for retry
                species_taxonid_map = defaultdict(list)
                taxonid_record_count = defaultdict(int)
                subspecies_count = 0
                continue
            else:
                # Latin-1 should handle any byte sequence, so this shouldn't happen
                logging.error(f"Failed to load result output with Latin-1 encoding: {e}")
                sys.exit(1)
        except Exception as e:
            logging.error(f"Failed to load result output: {e}")
            sys.exit(1)
    
    # Should never reach here
    logging.error("Failed to load result output with any supported encoding")
    sys.exit(1)


def perform_gap_analysis(
    species_synonyms: Dict[str, List[str]],
    valid_species_set: Set[str],
    synonym_to_valid: Dict[str, str],
    species_taxonid_map: Dict,
    taxonid_record_count: Dict,
    bags_data: Dict,
    species_to_bins: Dict,
    bin_to_species: Dict,
    all_species_in_results: Set,
    genus_to_taxonomy: Dict,
    species_input_data: Dict[str, Dict],
    input_columns: List[str]
) -> Tuple[List[Dict], List[str]]:
    """
    Perform gap analysis by merging all data sources.
    
    Returns:
        Tuple of:
        - List of dictionaries, one per unique species-taxonid combination
        - List of output column names (input columns first, then analysis columns)
    """
    logging.info("Performing gap analysis...")
    
    # Pre-compute all BINs associated with input species (for Extra BIN detection)
    all_input_species_bins = get_all_input_species_bins(species_synonyms, species_to_bins)
    logging.info(f"Found {len(all_input_species_bins)} unique BINs associated with input species")
    
    results = []
    processed_species = set()
    
    # Process species from input list
    for species_lower, synonyms in species_synonyms.items():
        processed_species.add(species_lower)
        
        # Get input data for this species (if TSV format was used)
        input_data = species_input_data.get(species_lower, {})
        
        # Find matching species in result output
        if species_lower in species_taxonid_map:
            # Species found in results
            for taxonid, taxonomy in species_taxonid_map[species_lower]:
                # Get BAGS data for this taxonid
                bags_info = bags_data.get(taxonid, {})
                
                # Get BINs for this taxonid
                bin_field = bags_info.get('BIN', '')
                taxonid_bins = set([b.strip() for b in bin_field.split('|') if b.strip()]) if bin_field else set()
                
                # Analyze synonym-BIN distribution
                syn_analysis = analyze_synonym_bin_distribution(
                    species_lower, synonyms, species_to_bins
                )
                
                # Check name representation
                name_rep = check_name_representation(
                    species_lower, synonyms, all_species_in_results,
                    species_taxonid_map, taxonid_record_count
                )
                
                # Determine species category
                category_info = determine_species_category(
                    species_lower, taxonid_bins, valid_species_set,
                    synonym_to_valid, all_input_species_bins, bin_to_species
                )
                
                # Analyze BAGS E sharers (only if BAGS grade E)
                if bags_info.get('BAGS', '') == 'E':
                    sharer_analysis = analyze_sharer_names(
                        bags_info.get('sharers', ''),
                        species_lower,
                        species_synonyms,
                        synonym_to_valid
                    )
                else:
                    sharer_analysis = {'sharer_status': '', 'sharer_type': ''}
                
                # Build result dictionary - start with input columns if available
                result = {}
                
                # Add all input columns first (preserves order)
                for col in input_columns:
                    result[col] = input_data.get(col, '')
                
                # Override species with formatted version (in case of case differences)
                result['species'] = format_species_name(species_lower)
                
                # Override synonyms column with pipe-separated format for consistency
                result['synonyms'] = '|'.join(synonyms) if synonyms else ''
                
                # Add analysis columns
                result.update({
                    'species_status': determine_species_status(
                        category_info['category'],
                        taxonid_record_count.get(taxonid, 0),
                        name_rep['synonym_record_count'],
                        bags_info.get('BAGS', ''),
                        sharer_analysis['sharer_status'],
                        syn_analysis['status'],
                        name_rep['representation']
                    ),
                    'species_category': category_info['category'],
                    'associated_input_species': category_info['associated_input_species'],
                    'total_record_count': taxonid_record_count.get(taxonid, 0),
                    'BAGS_grade': bags_info.get('BAGS', ''),
                    'BIN_uri': bin_field,
                    'sharers': bags_info.get('sharers', ''),
                    'synonym_BIN_status': syn_analysis['status'],
                    'synonym_BIN_details': syn_analysis['details'],
                    'name_representation': name_rep['representation'],
                    'names_with_records': name_rep['names_with_records'],
                    'synonym_record_count': name_rep['synonym_record_count'],
                    'synonym_only_flag': name_rep['synonym_only_flag'],
                    'BAGS_E_sharer_status': sharer_analysis['sharer_status'],
                    'BAGS_E_sharer_type': sharer_analysis['sharer_type'],
                    'taxonomy_source': 'Input' if input_data else 'Direct'
                })
                
                # Only add BOLD taxonomy columns if no input taxonomy was provided
                if not input_columns or 'kingdom' not in input_columns:
                    result.update({
                        'kingdom': taxonomy.get('kingdom', ''),
                        'phylum': taxonomy.get('phylum', ''),
                        'class': taxonomy.get('class', ''),
                        'order': taxonomy.get('order', ''),
                        'family': taxonomy.get('family', ''),
                        'genus': taxonomy.get('genus', ''),
                    })
                
                results.append(result)
        else:
            # Species in input list but NOT in results (0 records)
            # Infer taxonomy from genus (only if no input taxonomy)
            inferred = infer_taxonomy_from_genus(species_lower, genus_to_taxonomy)
            
            # For species with 0 records, analyze what we can
            syn_analysis = analyze_synonym_bin_distribution(
                species_lower, synonyms, species_to_bins
            )
            
            name_rep = check_name_representation(
                species_lower, synonyms, all_species_in_results,
                species_taxonid_map, taxonid_record_count
            )
            
            # Build result dictionary - start with input columns if available
            result = {}
            
            # Add all input columns first (preserves order)
            for col in input_columns:
                result[col] = input_data.get(col, '')
            
            # Override species with formatted version
            result['species'] = format_species_name(species_lower)
            
            # Override synonyms column with pipe-separated format
            result['synonyms'] = '|'.join(synonyms) if synonyms else ''
            
            # Add analysis columns
            result.update({
                'species_status': determine_species_status(
                    'Valid',
                    0,
                    name_rep['synonym_record_count'],
                    '',
                    '',
                    syn_analysis['status'],
                    name_rep['representation']
                ),
                'species_category': 'Valid',
                'associated_input_species': '',
                'total_record_count': 0,
                'BAGS_grade': '',
                'BIN_uri': '',
                'sharers': '',
                'synonym_BIN_status': syn_analysis['status'],
                'synonym_BIN_details': syn_analysis['details'],
                'name_representation': name_rep['representation'],
                'names_with_records': name_rep['names_with_records'],
                'synonym_record_count': name_rep['synonym_record_count'],
                'synonym_only_flag': name_rep['synonym_only_flag'],
                'BAGS_E_sharer_status': '',
                'BAGS_E_sharer_type': '',
            })
            
            # Handle taxonomy source
            if input_columns and 'kingdom' in input_columns:
                # Use input taxonomy (already in result from input_data)
                result['taxonomy_source'] = 'Input'
            else:
                # Use inferred taxonomy
                result.update({
                    'kingdom': inferred['taxonomy'].get('kingdom', ''),
                    'phylum': inferred['taxonomy'].get('phylum', ''),
                    'class': inferred['taxonomy'].get('class', ''),
                    'order': inferred['taxonomy'].get('order', ''),
                    'family': inferred['taxonomy'].get('family', ''),
                    'genus': inferred['taxonomy'].get('genus', ''),
                    'taxonomy_source': inferred['source']
                })
            
            results.append(result)
    
    # Process species found in results but NOT in input list (Extra species or synonyms)
    for species_lower, taxonid_list in species_taxonid_map.items():
        if species_lower not in processed_species:
            
            for taxonid, taxonomy in taxonid_list:
                bags_info = bags_data.get(taxonid, {})
                
                # Get BINs for this taxonid
                bin_field = bags_info.get('BIN', '')
                taxonid_bins = set([b.strip() for b in bin_field.split('|') if b.strip()]) if bin_field else set()
                
                # Determine species category (Valid/Synonym/Extra species/Extra BIN)
                category_info = determine_species_category(
                    species_lower, taxonid_bins, valid_species_set,
                    synonym_to_valid, all_input_species_bins, bin_to_species
                )
                
                # Analyze BAGS E sharers (only if BAGS grade E)
                if bags_info.get('BAGS', '') == 'E':
                    sharer_analysis = analyze_sharer_names(
                        bags_info.get('sharers', ''),
                        species_lower,
                        species_synonyms,
                        synonym_to_valid
                    )
                else:
                    sharer_analysis = {'sharer_status': '', 'sharer_type': ''}
                
                # Build result dictionary
                result = {}
                
                # For extra species, initialize all input columns as empty
                for col in input_columns:
                    result[col] = ''
                
                # Set species name
                result['species'] = format_species_name(species_lower)
                result['synonyms'] = ''  # Extra species don't have synonyms listed
                
                # Add analysis columns
                result.update({
                    'species_status': determine_species_status(
                        category_info['category'],
                        taxonid_record_count.get(taxonid, 0),
                        0,
                        bags_info.get('BAGS', ''),
                        sharer_analysis['sharer_status'],
                        'N/A',
                        'N/A'
                    ),
                    'species_category': category_info['category'],
                    'associated_input_species': category_info['associated_input_species'],
                    'total_record_count': taxonid_record_count.get(taxonid, 0),
                    'BAGS_grade': bags_info.get('BAGS', ''),
                    'BIN_uri': bin_field,
                    'sharers': bags_info.get('sharers', ''),
                    'synonym_BIN_status': 'N/A',
                    'synonym_BIN_details': '',
                    'name_representation': 'N/A',
                    'names_with_records': format_species_name(species_lower),
                    'synonym_record_count': 0,
                    'synonym_only_flag': '',
                    'BAGS_E_sharer_status': sharer_analysis['sharer_status'],
                    'BAGS_E_sharer_type': sharer_analysis['sharer_type'],
                    'taxonomy_source': 'Direct'
                })
                
                # Add BOLD taxonomy for extra species (if not already in input columns)
                if not input_columns or 'kingdom' not in input_columns:
                    result.update({
                        'kingdom': taxonomy.get('kingdom', ''),
                        'phylum': taxonomy.get('phylum', ''),
                        'class': taxonomy.get('class', ''),
                        'order': taxonomy.get('order', ''),
                        'family': taxonomy.get('family', ''),
                        'genus': taxonomy.get('genus', ''),
                    })
                
                results.append(result)
    
    logging.info(f"Gap analysis complete: {len(results)} total entries")
    
    # Summary statistics (using species_category column)
    valid_species_count = len([r for r in results if r['species_category'] == 'Valid'])
    synonym_species_count = len([r for r in results if r['species_category'] == 'Synonym'])
    extra_species_count = len([r for r in results if r['species_category'] == 'Extra species'])
    extra_bin_count = len([r for r in results if r['species_category'] == 'Extra BIN'])
    species_with_bags = len([r for r in results if r['BAGS_grade']])
    
    logging.info(f"  - Valid species (from input list): {valid_species_count}")
    logging.info(f"  - Synonym species (from input list): {synonym_species_count}")
    logging.info(f"  - Extra species (not on list): {extra_species_count}")
    logging.info(f"  - Extra BIN (shares BIN with input species): {extra_bin_count}")
    logging.info(f"  - Species with BAGS assessment: {species_with_bags}")
    
    # Species status summary (traffic light system)
    green_count = len([r for r in results if r['species_status'] == 'Green'])
    amber_count = len([r for r in results if r['species_status'] == 'Amber'])
    red_count = len([r for r in results if r['species_status'] == 'Red'])
    blue_count = len([r for r in results if r['species_status'] == 'Blue'])
    black_count = len([r for r in results if r['species_status'] == 'Black'])
    
    logging.info(f"  Species status summary:")
    logging.info(f"    - Green (clean): {green_count}")
    logging.info(f"    - Amber (known issues): {amber_count}")
    logging.info(f"    - Red (needs investigation): {red_count}")
    logging.info(f"    - Blue (nomenclatural fix): {blue_count}")
    logging.info(f"    - Black (no coverage): {black_count}")
    
    # Build output column order: input columns first, then analysis columns
    analysis_columns = [
        'species_status',
        'species_category',
        'associated_input_species',
        'total_record_count',
        'BAGS_grade',
        'BIN_uri',
        'sharers',
        'synonym_BIN_status',
        'synonym_BIN_details',
        'name_representation',
        'names_with_records',
        'synonym_record_count',
        'synonym_only_flag',
        'BAGS_E_sharer_status',
        'BAGS_E_sharer_type',
        'taxonomy_source'
    ]
    
    # Add BOLD taxonomy columns if not using TSV input with taxonomy
    if not input_columns or 'kingdom' not in input_columns:
        analysis_columns.extend(['kingdom', 'phylum', 'class', 'order', 'family', 'genus'])
    
    # Build final column order
    if input_columns:
        # Input columns first (excluding species and synonyms which are already there)
        output_columns = list(input_columns)
        # Add analysis columns that aren't already in input
        for col in analysis_columns:
            if col not in output_columns:
                output_columns.append(col)
    else:
        # Simple format: use standard output columns
        output_columns = ['species', 'synonyms'] + analysis_columns
    
    return results, output_columns


def write_gap_analysis(results: List[Dict], output_file: Path, fieldnames: List[str]) -> None:
    """Write gap analysis results to TSV file."""
    logging.info(f"Writing gap analysis to {output_file}")
    logging.info(f"Output columns: {len(fieldnames)}")
    
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        
        logging.info(f"Successfully wrote {len(results)} entries to {output_file}")
        
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")
        sys.exit(1)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Perform gap analysis for BOLD library curation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using config file (reads FILTER_TAXA_LIST from config)
  python gap_analysis.py --config config/config.yml \\
      --result-output results/result_output.tsv \\
      --assessed-bags results/assessed_BAGS.tsv \\
      --output results/gap_analysis.tsv
  
  # Using simple species list (CSV format)
  python gap_analysis.py --species-list species.csv \\
      --result-output results/result_output.tsv \\
      --assessed-bags results/assessed_BAGS.tsv \\
      --output results/gap_analysis.tsv
  
  # Using TSV species list with additional columns
  python gap_analysis.py --species-list species.tsv \\
      --result-output results/result_output.tsv \\
      --assessed-bags results/assessed_BAGS.tsv \\
      --output results/gap_analysis.tsv

Input file formats:
  - Simple format (.csv, .txt): One species per line, synonyms semicolon-separated
    Example: Gammarus pulex;Gammarus fossarum
  
  - TSV format (.tsv): Tab-separated with headers
    Required columns: species, synonyms (semicolon-separated)
    All additional columns are preserved in output
        """
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to config.yml file (to read FILTER_TAXA_LIST)'
    )
    
    parser.add_argument(
        '--species-list',
        type=Path,
        help='Path to species list file (CSV or TSV, overrides config FILTER_TAXA_LIST)'
    )
    
    parser.add_argument(
        '--result-output',
        type=Path,
        required=True,
        help='Path to result_output.tsv file'
    )
    
    parser.add_argument(
        '--assessed-bags',
        type=Path,
        required=True,
        help='Path to assessed_BAGS.tsv file'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Path to output gap analysis TSV file'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logging.info("=" * 80)
    logging.info("BOLD Library Curation - Gap Analysis")
    logging.info("=" * 80)
    
    # Determine species list source
    species_list_path = None
    
    if args.species_list:
        species_list_path = args.species_list
        logging.info(f"Using species list from CLI argument: {species_list_path}")
    elif args.config:
        config = load_config(args.config)
        filter_taxa_list = config.get('FILTER_TAXA_LIST')
        if filter_taxa_list:
            species_list_path = Path(filter_taxa_list)
            logging.info(f"Using species list from config: {species_list_path}")
        else:
            logging.error("FILTER_TAXA_LIST not found in config file")
            sys.exit(1)
    else:
        logging.error("Must provide either --config or --species-list")
        parser.print_help()
        sys.exit(1)
    
    # Validate input files exist
    if not species_list_path.exists():
        logging.error(f"Species list file not found: {species_list_path}")
        sys.exit(1)
    
    if not args.result_output.exists():
        logging.error(f"Result output file not found: {args.result_output}")
        sys.exit(1)
    
    if not args.assessed_bags.exists():
        logging.error(f"Assessed BAGS file not found: {args.assessed_bags}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Load all data
    species_synonyms, valid_species_set, synonym_to_valid, species_input_data, input_columns = parse_species_list(species_list_path)
    bags_data = load_assessed_bags(args.assessed_bags)
    (species_taxonid_map, taxonid_record_count,
     species_to_bins, bin_to_species,
     all_species_in_results, genus_to_taxonomy) = load_result_output(args.result_output)
    
    # Perform gap analysis
    results, output_columns = perform_gap_analysis(
        species_synonyms,
        valid_species_set,
        synonym_to_valid,
        species_taxonid_map,
        taxonid_record_count,
        bags_data,
        species_to_bins,
        bin_to_species,
        all_species_in_results,
        genus_to_taxonomy,
        species_input_data,
        input_columns
    )
    
    # Write output
    write_gap_analysis(results, args.output, output_columns)
    
    logging.info("=" * 80)
    logging.info("Gap analysis complete!")
    logging.info("=" * 80)


if __name__ == '__main__':
    main()
