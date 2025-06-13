# BOLD Taxonomy Extraction Script

This package contains scripts to extract taxonomy information from BOLD project TSV files based on plate IDs. The script automatically handles multiple BOLD data formats and provides robust error handling.

## Files

1. **extract_taxonomy.py** - Main extraction script
2. **README.md** - This documentation file

## Usage

### Basic Usage
```bash
python extract_taxonomy.py plate_id1 plate_id2 plate_id3 ...
```

### With Options
```bash
python extract_taxonomy.py BGE_00688 BGE_00647 --base-dir "path\to\base-directory" --output my_results.tsv
```

### Real Examples
```bash
# Single format dataset
python extract_taxonomy.py BGE_00688 --output single_plate.tsv

# Multiple plates from mixed formats
python extract_taxonomy.py BGE_00273 BGE_00841 BGE_00842 --base-dir ".\bold_bge_20250613" --output mixed_formats.tsv

# Large extraction across multiple directories
python extract_taxonomy.py BGE_00536 BGE_00537 BGE_00538 BGE_00688 BGE_00841 --output large_extraction.tsv
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

### Data Format Support

The script automatically detects and handles two different BOLD data formats:

**Format 1 (Original)**: 
- `Plate ID` and `Well Position` columns are populated separately
- Example: Plate ID = "BGE_00688", Well Position = "A01"
- Used in datasets like BGE_0688, ILECA, INVBG

**Format 2 (Alternative)**: 
- `Plate ID` and `Well Position` columns are empty
- `SampleID` contains the full identifier (e.g., "BGE_00841_A1")
- Used in datasets like bold_musba
- Script automatically extracts plate ID from SampleID format

### Matching Logic

For each record in merged_custom_fields.tsv with a matching Plate ID:

1. **Auto-format Detection**: Script determines data format by checking if `Plate ID` column has values
2. **Primary Match**: Try to match `SampleID` (from merged_custom_fields) with `Sample ID` (from taxonomy)
3. **Secondary Match**: If no primary match, try to match `Plate_ID_WellPosition` format (e.g., "BGE_00647_A08") with `Sample ID` (from taxonomy)
4. **Lab Data**: Once a taxonomy match is found, locate the corresponding `Process ID` from lab.tsv using the same `Sample ID`

### Output Format

The output TSV file contains:
- `Process ID`: The Process ID from the lab.tsv file
- `Plate_Well`: Combined Plate ID and Well Position (e.g., "BGE_00688_A01")
- `Sample ID`: The Sample ID from the taxonomy file
- All remaining taxonomy columns: Phylum, Class, Order, Family, etc.

## Example Plate IDs

The script has been tested with various plate ID formats:
- **Standard format**: BGE_00536, BGE_00537, BGE_00538, BGE_00539, BGE_00540
- **Mixed datasets**: BGE_00688 (ILECA), BGE_00841 (bold_musba), BGE_00842 (bold_musba)
- **Large extractions**: Successfully processed 1,330+ records across multiple plate IDs

## Requirements

- Python 3.6+
- pandas library (`pip install pandas`)

## File Structure Expected

The script works with various BOLD data directory structures:

### Format 1 (Original Structure)
```
base_directory/
├── BGE_0688/
│   ├── merged_custom_fields.tsv  # Has populated Plate ID & Well Position columns
│   ├── taxonomy.tsv
│   └── lab.tsv
├── ILECA/
│   ├── merged_custom_fields.tsv
│   ├── taxonomy.tsv
│   └── lab.tsv
└── ...
```

### Format 2 (Alternative Structure)
```
base_directory/
├── bold_musba/
│   ├── merged_custom_fields.tsv  # Empty Plate ID column, full ID in SampleID
│   ├── taxonomy.tsv
│   └── lab.tsv
├── data/
│   ├── merged_custom_fields.tsv
│   ├── taxonomy.tsv
│   └── lab.tsv
└── ...
```

### Mixed Environments
The script automatically handles directories with different formats in the same base directory, making it suitable for processing diverse BOLD datasets without manual intervention.

## Error Handling & Performance

### Robust Data Processing
- **Encoding Support**: Handles encoding issues (tries UTF-8, falls back to latin-1)
- **DataFrame Optimization**: Uses `low_memory=False` to suppress dtype warnings for mixed column types
- **Format Auto-detection**: Automatically detects and handles different BOLD data formats
- **Missing Data**: Gracefully handles empty `Plate ID` columns by extracting from `SampleID`

### Error Recovery
- Skips directories that don't have all three required TSV files
- Reports the number of matching records found in each directory
- Continues processing even if individual files fail to load
- If no Process ID is found in lab.tsv for a sample, the field will be empty
- Provides detailed progress reporting and error messages

### Performance Features
- Processes large datasets efficiently (tested with 1,330+ records)
- Handles mixed data types in TSV files without warnings
- Memory-efficient processing with pandas optimizations
