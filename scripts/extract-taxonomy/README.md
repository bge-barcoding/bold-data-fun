# BOLD Taxonomy Extraction Script

This package contains scripts to extract taxonomy information from BOLD project TSV files based on plate IDs.

## Files

1. **extract_taxonomy.py** - Main extraction script
2. **run_extraction.py** - Example script with predefined plate IDs
3. **README.md** - This documentation file

## Usage

### Basic Usage
```bash
python extract_taxonomy.py plate_id1 plate_id2 plate_id3 ...
```

### With Options
```bash
python extract_taxonomy.py BGE_00688 BGE_00647 --base-dir "C:\_claude_files\projects\bold-extract-taxonomy" --output my_results.tsv
```

### Using the Example Script
```bash
python run_extraction.py
```

## Command Line Arguments

- `plate_ids` (required): One or more plate IDs to extract
- `--base-dir`: Base directory to search for TSV files (default: current directory)
- `--output`: Output file name (default: extracted_taxonomy.tsv)

## How It Works

The script searches through all subdirectories in the base directory looking for:
- `merged_custom_fields.tsv` - Contains sample information including Plate ID and Well Position
- `taxonomy.tsv` - Contains taxonomic classification information
- `lab.tsv` - Contains Process ID and other lab-related information

### Matching Logic

For each record in merged_custom_fields.tsv with a matching Plate ID:

1. **Primary Match**: Try to match `SampleID` (from merged_custom_fields) with `Sample ID` (from taxonomy)
2. **Secondary Match**: If no primary match, try to match `Plate_ID_WellPosition` format (e.g., "BGE_00647_A08") with `Sample ID` (from taxonomy)
3. **Lab Data**: Once a taxonomy match is found, locate the corresponding `Process ID` from lab.tsv using the same `Sample ID`

### Output Format

The output TSV file contains:
- `Process ID`: The Process ID from the lab.tsv file
- `Plate_Well`: Combined Plate ID and Well Position (e.g., "BGE_00688_A01")
- `Sample ID`: The Sample ID from the taxonomy file
- All remaining taxonomy columns: Phylum, Class, Order, Family, etc.

## Example Plate IDs
- BGE_00536, BGE_00537, BGE_00538, BGE_00539, BGE_00540

## Requirements

- Python 3.6+
- pandas library (`pip install pandas`)

## File Structure Expected

```
base_directory/
├── subdirectory1/
│   ├── merged_custom_fields.tsv
│   ├── taxonomy.tsv
│   └── lab.tsv
├── subdirectory2/
│   ├── merged_custom_fields.tsv
│   ├── taxonomy.tsv
│   └── lab.tsv
└── ...
```

## Error Handling

- The script handles encoding issues (tries UTF-8, falls back to latin-1)
- Skips directories that don't have all three required TSV files
- Reports the number of matching records found in each directory
- Continues processing even if individual files fail to load
- If no Process ID is found in lab.tsv for a sample, the field will be empty
