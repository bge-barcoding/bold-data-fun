# Gap Analysis for BOLD Library Curation

A Python script that performs comprehensive gap analysis for DNA barcode library curation by comparing target species lists against BOLD (Barcode of Life Data) database records and BAGS (Barcode, Audit & Grade System) assessments.

## Overview

This tool uses the output of the [BOLDetective](https://github.com/bge-barcoding/bold-library-curation) pipeline for analysing animal barcode data quality in BOLD. It identifies coverage gaps, taxonomic inconsistencies, and data quality issues by cross-referencing:

1. **Input species list** — Target species with optional synonyms
2. **Result output** — BOLD database records (`result_output.tsv`)
3. **BAGS assessment** — BIN grading data (`assessed_BAGS.tsv`)

## Features

- **Traffic light status system** — Assigns actionable status (Green/Amber/Red/Blue/Black) to each species
- **Species coverage analysis** — Identifies which target species have BOLD records
- **Synonym handling** — Tracks valid names and their synonyms, detecting when only synonyms have records
- **BIN concordance checking** — Flags taxonomic concerns when synonyms appear in different BINs
- **Intelligent categorisation** — Classifies species as Valid, Synonym, Extra species, or Extra BIN
- **BAGS grade E analysis** — Analyses BIN-sharing species for synonym status and Linnean name validity
- **Taxonomy inference** — Infers higher taxonomy for missing species from congeneric records
- **Record count aggregation** — Provides counts at taxonid, species, and BIN levels

## Installation

### Requirements

- Python 3.7+
- PyYAML

```bash
pip install pyyaml
```

### Dependencies

No additional dependencies beyond the Python standard library and PyYAML.

## Usage

### Basic Usage with Config File

```bash
python gap_analysis.py \
    --config config/config.yml \
    --result-output results/result_output.tsv \
    --assessed-bags results/assessed_BAGS.tsv \
    --output results/gap_analysis.tsv
```

### Using Custom Species List

```bash
python gap_analysis.py \
    --species-list custom_species.csv \
    --result-output results/result_output.tsv \
    --assessed-bags results/assessed_BAGS.tsv \
    --output results/gap_analysis.tsv
```

### Command Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--config` | No* | Path to config.yml (reads `FILTER_TAXA_LIST`) |
| `--species-list` | No* | Path to species list CSV (overrides config) |
| `--result-output` | Yes | Path to `result_output.tsv` from BOLD |
| `--assessed-bags` | Yes | Path to `assessed_BAGS.tsv` from BAGS pipeline |
| `--output` | Yes | Output path for gap analysis TSV |
| `--log-level` | No | Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO) |

*Either `--config` or `--species-list` must be provided.

## Input Files

### Species List Format

Plain text file with one species per line. Synonyms are semicolon-separated:

```
Gammarus pulex
Gammarus fossarum;Gammarus caparti
Chaetogaster diastrophus;Chaetogaster fluminis
```

### Result Output (`result_output.tsv`)

Tab-separated file from BOLD containing at minimum:
- `species` — Species name
- `subspecies` — Subspecies (optional)
- `taxonid` — BOLD taxon identifier
- `BIN` — Barcode Index Number(s), pipe-separated if multiple
- Taxonomy columns: `kingdom`, `phylum`, `class`, `order`, `family`, `genus`

### Assessed BAGS (`assessed_BAGS.tsv`)

Tab-separated BAGS assessment output containing:
- `taxonid` — BOLD taxon identifier
- `BAGS` — Grade (A, B, C, D, or E)
- `BIN` — Associated BIN URI(s)
- `sharers` — Pipe-separated list of species sharing the BIN (for grade E)

## Output

### Gap Analysis TSV

The script produces a comprehensive TSV file with 25 columns organised into logical groups:

#### Core Identification
| Column | Description |
|--------|-------------|
| `species` | Species name in binomial format |
| `species_status` | Traffic light status: Green, Amber, Red, Blue, Black, or N/A |
| `synonyms` | Pipe-separated list of synonyms from input |

#### Classification
| Column | Description |
|--------|-------------|
| `species_category` | Classification: Valid, Synonym, Extra species, or Extra BIN |
| `associated_input_species` | For "Extra BIN" category: input species sharing this BIN |

#### Record Counts
| Column | Description |
|--------|-------------|
| `total_record_count` | Number of BOLD records for this taxonid |

#### BAGS Assessment
| Column | Description |
|--------|-------------|
| `BAGS_grade` | BAGS grade (A-E) for this taxonid |
| `BIN_uri` | BIN URI(s) for this taxonid |
| `sharers` | Species sharing the BIN (BAGS grade E only) |

#### Synonym-BIN Analysis
| Column | Description |
|--------|-------------|
| `synonym_BIN_status` | Same BIN, Different BINs, Partial overlap, No data, or N/A |
| `synonym_BIN_details` | Detailed BIN information per synonym |

#### Name Representation
| Column | Description |
|--------|-------------|
| `name_representation` | Valid name only, Valid + synonym(s), Synonym only, No records, or N/A |
| `names_with_records` | Comma-separated list of names found in BOLD |
| `synonym_record_count` | Total records across all synonyms found in BOLD (0 if none) |
| `synonym_only_flag` | ⚠️ warning if only synonym has records |

#### BAGS Grade E Analysis
| Column | Description |
|--------|-------------|
| `BAGS_E_sharer_status` | All known synonyms, Mix, No known synonyms, or N/A |
| `BAGS_E_sharer_type` | All Linnean or Contains non-Linnean |

#### Taxonomy
| Column | Description |
|--------|-------------|
| `kingdom` | Taxonomic kingdom |
| `phylum` | Taxonomic phylum |
| `class` | Taxonomic class |
| `order` | Taxonomic order |
| `family` | Taxonomic family |
| `genus` | Taxonomic genus |
| `taxonomy_source` | Direct, Inferred from genus, Inconsistent, or No genus data |

## Species Categories Explained

The `species_category` column classifies each entry:

| Category | Description |
|----------|-------------|
| **Valid** | Species from your input list with BOLD records |
| **Synonym** | Name listed as a synonym in your input list |
| **Extra BIN** | Not on input list, but shares a BIN with an input species |
| **Extra species** | Not on input list and doesn't share BINs with input species |

## Species Status (Traffic Light System)

The `species_status` column provides an actionable assessment for each target species, using a traffic light system to prioritise curation efforts. Status is only assigned to Valid species from the input list; all other categories receive N/A.

| Status | Colour | Meaning | Criteria |
|--------|--------|---------|----------|
| **Green** | 🟢 | Clean, no issues | BAGS ≠ E, valid name present, no BIN conflicts |
| **Amber** | 🟡 | Known issues, needs work | BAGS E with known synonyms, partial BIN overlap, or both valid and synonym names present |
| **Red** | 🔴 | Needs investigation | BAGS E with unknown sharers, or synonyms in completely different BINs |
| **Blue** | 🔵 | Nomenclatural fix needed | Only synonym has records, valid name absent from BOLD |
| **Black** | ⚫ | No coverage | No records for valid name or any synonyms |
| **N/A** | — | Not assessed | Extra species, Extra BIN, or Synonym category |

### Priority Order

When multiple conditions apply, the worst status takes precedence:

**Black → Red → Amber → Blue → Green**

### Detailed Criteria

#### Green (Clean)
- BAGS grade is not E (or empty)
- Valid name has records
- No BIN conflicts with synonyms

#### Amber (Known Issues)
Any of:
- BAGS grade E, but all sharers are known synonyms from input list
- Synonyms have partial BIN overlap with valid species
- Both valid name and synonym(s) have records in BOLD

#### Red (Needs Investigation)
Any of:
- BAGS grade E with unknown species sharing the BIN
- BAGS grade E with mix of known synonyms and unknown species
- Synonyms are in completely different BINs than valid species (taxonomic concern)

#### Blue (Nomenclatural Fix)
- Only synonym name(s) have records
- Valid name is absent from BOLD
- Not triggered if Red conditions also apply

#### Black (No Coverage)
- Zero records for valid species name
- Zero records for all synonyms

## Key Analyses

### Synonym-BIN Concordance

Detects taxonomic red flags where synonyms appear in different BINs than the valid name:

- **Same BIN** — Synonyms share BIN(s) with valid name ✓
- **Different BINs** — Synonyms in completely separate BINs ⚠️
- **Partial overlap** — Some BINs shared, some different

### Name Representation

Identifies curation issues where the valid name is absent from BOLD:

- **Synonym only** ⚠️ — Only synonym has records, valid name absent
- **Valid + synonym(s)** — Both valid and synonym names have records
- **Valid name only** — Only the valid name has records

### Taxonomy Inference

For target species with zero BOLD records, taxonomy is inferred from congeneric species:

- Searches for other species of the same genus in BOLD
- Uses consensus taxonomy if all congenerics agree
- Flags inconsistencies if genus has conflicting taxonomies

## Example Output

```
species                 species_status    species_category    synonym_BIN_status    name_representation    BAGS_grade
Gammarus pulex          Amber             Valid               Same BIN              Valid + synonym(s)     C
Limnephilus rhombicus   Green             Valid               N/A                   Valid name only        B
Baetis rhodani          Red               Valid               Different BINs        Valid + synonym(s)     E
Ephemera danica         Blue              Valid               N/A                   Synonym only           C
Hydropsyche pellucidula Black             Valid               N/A                   No records             
Gammarus roeseli        N/A               Extra BIN           N/A                   N/A                    D
```

## Troubleshooting

### Encoding Issues

The script automatically handles both UTF-8 and Latin-1 encoded input files. If you encounter encoding errors, ensure your input files use one of these encodings.

### Large Files

For very large TSV files, the script automatically adjusts CSV field size limits. On Windows, this is capped at 2GB fields.

### Missing Species

Species on your input list with zero BOLD records will still appear in the output with:
- `total_record_count`: 0
- `BAGS_grade`: empty
- `taxonomy_source`: "Inferred from genus" (if congenerics exist)
