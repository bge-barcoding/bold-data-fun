# BOLD TSV Merger Tools

This directory contains two Python scripts for merging TSV files from BOLD (Barcode of Life Data System) exports. These tools are designed to work in sequence, handling the complex structure of BOLD data exports with their multi-file format and UUID-based field mapping.

## Scripts Overview

### 1. `bold_tsv_merger.py` - Individual Dataset Merger
Merges multiple TSV files from a single BOLD dataset export into one consolidated file.

### 2. `bold_merged_tsv_merger.py` - Multi-Dataset Merger  
Combines multiple merged files (created by the first script) from different BOLD datasets into a single unified file.

## Workflow

```
BOLD Dataset 1/        BOLD Dataset 2/        BOLD Dataset 3/
├── voucher.tsv        ├── voucher.tsv        ├── voucher.tsv
├── taxonomy.tsv   →   ├── taxonomy.tsv   →   ├── taxonomy.tsv
├── specimen_details   ├── specimen_details   ├── specimen_details
├── collection_data    ├── collection_data    ├── collection_data
└── ...               └── ...               └── ...
     │                     │                     │
     ▼                     ▼                     ▼
merged_output.tsv    merged_output.tsv    merged_output.tsv
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           ▼
              bold_final_merged.tsv
```

## Prerequisites

- Python 3.6 or higher
- pandas library
- pathlib (included in Python 3.4+)

Install dependencies:
```bash
pip install pandas
```

## Script 1: bold_tsv_merger.py

### Purpose
Merges multiple TSV files from a single BOLD dataset export based on Sample ID columns. Handles the special structure of BOLD exports including:
- Multiple related TSV files (voucher.tsv, taxonomy.tsv, specimen_details.tsv, etc.)
- UUID rows in merged_custom_fields.tsv for field mapping
- Duplicate column handling and cleanup
- Standardized column ordering

### Usage

```bash
# Basic usage
python bold_tsv_merger.py "path/to/bold/dataset/folder"

# With custom output file
python bold_tsv_merger.py "path/to/bold/dataset/folder" --output custom_name.tsv

# With custom log file
python bold_tsv_merger.py "path/to/bold/dataset/folder" --log custom_log.log
```

### Examples

```bash
# Merge BOLD plant dataset
python bold_tsv_merger.py "C:\BOLD_exports\plants_dataset"

# Merge with custom output name
python bold_tsv_merger.py "/home/user/bold_data/animals" --output animals_merged.tsv

# Specify both output and log files  
python bold_tsv_merger.py "D:\Research\BOLD\fungi" -o fungi_complete.tsv -l fungi_merge.log
```

### Input Structure
Expected input folder structure:
```
bold_dataset_folder/
├── voucher.tsv
├── taxonomy.tsv  
├── specimen_details.tsv
├── collection_data.tsv
├── merged_custom_fields.tsv  # Contains UUID row for field mapping
├── lab.tsv
└── tags.tsv
```

### Output
- `merged_output.tsv` (or custom name): Consolidated TSV file with all data merged by Sample ID
- `tsv_merge_log_YYYYMMDD_HHMMSS.log`: Detailed log of the merge process

### Features
- **Smart Column Ordering**: Preserves logical order based on file importance
- **Duplicate Handling**: Resolves duplicate fields, preferring non-lab.tsv versions
- **UUID Preservation**: Maintains UUID field mappings from merged_custom_fields.tsv
- **Data Validation**: Removes duplicate Sample IDs within and across files
- **Comprehensive Logging**: Detailed logs for troubleshooting and verification

## Script 2: bold_merged_tsv_merger.py

### Purpose
Combines multiple merged TSV files (created by `bold_tsv_merger.py`) from different BOLD datasets into a single unified file. Handles:
- Different field sets across datasets
- UUID field mapping conflicts
- Intelligent column merging based on identical field names
- Fallback reading for different file structures

### Usage

```bash
# Basic usage
python bold_merged_tsv_merger.py "path/to/folder/with/merged/files"

# With custom output file
python bold_merged_tsv_merger.py "path/to/merged/folder" --output final_dataset.tsv

# With custom log file  
python bold_merged_tsv_merger.py "path/to/merged/folder" --log final_merge.log
```

### Examples

```bash
# Combine plant and animal datasets
python bold_merged_tsv_merger.py "C:\Research\BOLD_merged_datasets"

# Create final dataset with custom name
python bold_merged_tsv_merger.py "/data/bold/merged" --output complete_biodiversity.tsv

# Full custom specification
python bold_merged_tsv_merger.py "D:\BOLD\final" -o ecosystem_data.tsv -l final_log.log
```

### Input Structure
Expected input folder structure:
```
merged_datasets_folder/
├── plants_merged_output.tsv      # From bold_tsv_merger.py
├── animals_merged_output.tsv     # From bold_tsv_merger.py  
├── fungi_merged_output.tsv       # From bold_tsv_merger.py
└── bacteria_merged_output.tsv    # From bold_tsv_merger.py
```

### Output
- `bold_final_merged.tsv` (or custom name): Final unified TSV file
- `bold_merge_log_YYYYMMDD_HHMMSS.log`: Detailed log of the merge process

### Features
- **Multi-Dataset Integration**: Combines datasets with different field sets
- **UUID Conflict Resolution**: Handles conflicting field mappings intelligently  
- **Duplicate Column Merging**: Merges identical fields from different datasets
- **Flexible Header Detection**: Handles files with or without UUID rows
- **Data Completeness**: Uses outer joins to preserve all records

## Complete Workflow Example

### Step 1: Prepare individual datasets
```bash
# Merge plants dataset
python bold_tsv_merger.py "C:\BOLD_exports\plants" --output plants_merged.tsv

# Merge animals dataset  
python bold_tsv_merger.py "C:\BOLD_exports\animals" --output animals_merged.tsv

# Merge fungi dataset
python bold_tsv_merger.py "C:\BOLD_exports\fungi" --output fungi_merged.tsv
```

### Step 2: Move merged files to common folder
```bash
mkdir "C:\BOLD_exports\final_merge"
move "C:\BOLD_exports\plants\plants_merged.tsv" "C:\BOLD_exports\final_merge\"
move "C:\BOLD_exports\animals\animals_merged.tsv" "C:\BOLD_exports\final_merge\"  
move "C:\BOLD_exports\fungi\fungi_merged.tsv" "C:\BOLD_exports\final_merge\"
```

### Step 3: Create final merged dataset
```bash
python bold_merged_tsv_merger.py "C:\BOLD_exports\final_merge" --output biodiversity_complete.tsv
```

## Data Processing Notes

### Sample ID Handling
Both scripts use Sample ID as the primary key for merging. They automatically handle variants like:
- `Sample ID`
- `SampleID` 
- `sample_id`
- `Process ID` (as fallback)

### UUID Field Mapping
BOLD exports include machine-readable UUIDs in the first row of some files (especially merged_custom_fields.tsv). These scripts:
- Detect and preserve UUID mappings
- Align UUIDs with merged column structure
- Resolve conflicts when merging multiple datasets

### Column Ordering Priority
Files are processed in this order to maintain logical data structure:
1. voucher.tsv
2. taxonomy.tsv  
3. specimen_details.tsv
4. collection_data.tsv
5. merged_custom_fields.tsv
6. lab.tsv
7. tags.tsv

### Duplicate Resolution
When duplicate fields exist:
- Non-lab.tsv versions are preferred
- Conflicts are logged for review
- Empty values are filled from alternate sources

## Troubleshooting

### Common Issues

**No Sample ID column found**
- Check that input files are from BOLD exports
- Verify TSV format and column headers
- Check log files for column name variations

**UUID mapping conflicts**  
- Review log files for specific conflicts
- Consider if different datasets use different field definitions
- Check if files have been modified after export

**Memory issues with large datasets**
- Process datasets in smaller batches
- Ensure sufficient RAM (pandas loads entire datasets)
- Consider using `chunksize` parameter for very large files

### Log Files
Both scripts generate detailed log files that include:
- File processing status
- Column mapping information  
- Duplicate detection and resolution
- Error messages and warnings
- Final merge statistics

## Output Validation

After running either script, verify the output by checking:
- Row counts match expected totals
- Sample ID uniqueness
- Column completeness across merged datasets
- UUID field alignment (if applicable)
- Log file summary statistics

## License

These scripts are provided as-is for processing BOLD data exports. Ensure compliance with BOLD data usage policies when working with downloaded datasets.