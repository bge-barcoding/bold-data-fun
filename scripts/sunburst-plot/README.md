# Sunburst Chart Generator

A powerful Python script that creates hierarchical sunburst charts from CSV data, supporting up to 5 levels of hierarchy with excellent colour discrimination, professional formatting, and advanced visualization controls.

## Scripts in This Directory

### 1. `sunburst_script.py` - Main Chart Generator (Recommended)

The primary, feature-rich script for general use. Provides full command-line interface with extensive customization options.

### 2. `create_species_sunburst.py` - Custom Template Script

A specialized wrapper demonstrating how to create sunburst charts with custom center labels and hardcoded configurations.

---

## Quick Start

```bash
# Basic usage with defaults
python sunburst_script.py data.csv

# Taxonomic hierarchy example
python sunburst_script.py data.csv --level1 Phylum --level2 Class --level3 Order --sample-id Species

# Clean chart with top-N grouping
python sunburst_script.py data.csv --top-n 10 --label-style full --line-width 0.3
```

---

## Command Line Arguments

### Required Argument

| Argument | Description |
|----------|-------------|
| `csv_file` | Path to input CSV file |

### Data Column Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--sample-id` | `Sample-ID` | Column name for counting samples/unique values |
| `--level1` | `Partner_sub` | Column for hierarchy level 1 (innermost ring) |
| `--level2` | `partner` | Column for hierarchy level 2 |
| `--level3` | `Project-Code` | Column for hierarchy level 3 |
| `--level4` | `None` | Column for hierarchy level 4 (optional) |
| `--level5` | `None` | Column for hierarchy level 5 (optional, outermost ring) |

### Counting Mode

| Argument | Default | Description |
|----------|---------|-------------|
| `--count-unique` | `False` (flag) | Count unique values in sample-id column instead of all records |

### Grouping & Aggregation Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--top-n` | `None` | Keep only top N items per level, aggregate rest into "Other". `None` or `0` = show all items (no limit) |
| `--threshold` | `0.0` | Percentage threshold (0-100) for aggregating small slices into "Other". `0` = no aggregation |
| `--threshold-mode` | `local` | How threshold is calculated: `local` = percentage of level total, `global` = percentage of grand total |
| `--other-label` | `Other` | Label text for aggregated small items |

### Label Formatting Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--label-style` | `name-count` | Label format style (see table below) |
| `--show-percent` | `False` (flag) | Add percentage to labels (works with `name-count` style) |
| `--label-threshold` | `5.0` | Minimum segment angle in degrees for showing labels. Segments smaller than this get no label |

**Label Style Options:**

| Style | Example Output | Description |
|-------|----------------|-------------|
| `name-count` | `Diptera`<br>`730` | Name and count (default) |
| `name-only` | `Diptera` | Name only, no numbers |
| `name-percent` | `Diptera`<br>`38.3%` | Name and percentage of total |
| `full` | `Diptera`<br>`730 (38.3%)` | Name, count, and percentage |

### Colour Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--color-inherit-level` | `1` | Level from which colours are inherited (1-5). Level 1 = each top-level category gets unique colour, descendants inherit variations |
| `--color-mode` | `variations` | Colour inheritance mode: `variations` = progressive shading for child segments, `same` = identical colours for all inherited levels |

### Visual Styling Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--line-width` | `0.5` | Width of lines between segments. Range: `0.1` (ultra-thin) to `2.0+` (bold) |
| `--no-adaptive-font` | `False` (flag) | Disable adaptive font sizing (use legacy fixed sizing instead) |

### Output Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--output` | `sunburst_chart.png` | Output filename with extension |
| `--title` | `None` | Chart title (default: no title displayed) |
| `--width` | `18` | Figure width in inches |
| `--height` | `18` | Figure height in inches |
| `--no-auto-formats` | `False` (flag) | Skip automatic generation of SVG and PDF versions |

**Supported Output Formats:** PNG, JPG, PDF, SVG, EPS, TIFF

By default, the script automatically generates SVG and PDF versions alongside the primary output for editing and printing.

---

## Examples

### Basic Examples

```bash
# Simple 3-level chart with defaults
python sunburst_script.py data.csv

# Custom column names
python sunburst_script.py data.csv --level1 Kingdom --level2 Phylum --level3 Class

# Count unique species instead of records
python sunburst_script.py data.csv --sample-id Species --count-unique

# 5-level deep hierarchy
python sunburst_script.py data.csv --level1 Kingdom --level2 Phylum --level3 Class --level4 Order --level5 Family
```

### Grouping Examples

```bash
# Keep top 10 items per level, group rest into "Other"
python sunburst_script.py data.csv --top-n 10

# Group items smaller than 5% of their level
python sunburst_script.py data.csv --threshold 5.0

# Group items smaller than 2% of total dataset
python sunburst_script.py data.csv --threshold 2.0 --threshold-mode global

# Combined: top 8 items, then filter out <1% globally
python sunburst_script.py data.csv --top-n 8 --threshold 1.0 --threshold-mode global

# Custom label for grouped items
python sunburst_script.py data.csv --top-n 10 --other-label "Minor taxa"
```

### Label Formatting Examples

```bash
# Names only (no counts)
python sunburst_script.py data.csv --label-style name-only

# Names with percentages
python sunburst_script.py data.csv --label-style name-percent

# Full labels: name, count, and percentage
python sunburst_script.py data.csv --label-style full

# Add percentage to default name-count style
python sunburst_script.py data.csv --show-percent

# Show labels on smaller segments (lower threshold)
python sunburst_script.py data.csv --label-threshold 2.0

# Show labels on all segments
python sunburst_script.py data.csv --label-threshold 0
```

### Visual Styling Examples

```bash
# Ultra-thin segment borders
python sunburst_script.py data.csv --line-width 0.1

# Thicker borders
python sunburst_script.py data.csv --line-width 1.5

# Disable adaptive font sizing
python sunburst_script.py data.csv --no-adaptive-font

# Large figure for detailed viewing
python sunburst_script.py data.csv --width 24 --height 24
```

### Colour Examples

```bash
# Default: Level 1 inherits with colour variations
python sunburst_script.py data.csv --color-inherit-level 1 --color-mode variations

# Same colours for all descendants (no shading)
python sunburst_script.py data.csv --color-inherit-level 1 --color-mode same

# Levels 1-2 get unique colours, level 3+ inherit from level 2
python sunburst_script.py data.csv --color-inherit-level 2
```

### Output Examples

```bash
# SVG for vector editing
python sunburst_script.py data.csv --output chart.svg

# PDF for publications
python sunburst_script.py data.csv --output chart.pdf

# PNG only, skip auto SVG/PDF
python sunburst_script.py data.csv --output chart.png --no-auto-formats

# Custom title (no title shown by default)
python sunburst_script.py data.csv --title "Biodiversity Analysis 2024"
```

### Complete Real-World Example

```bash
# Taxonomic sunburst with professional styling
python sunburst_script.py biodiversity.csv \
    --sample-id Species \
    --count-unique \
    --level1 Phylum \
    --level2 Class \
    --level3 Order \
    --top-n 12 \
    --threshold 1.0 \
    --threshold-mode global \
    --label-style full \
    --label-threshold 3.0 \
    --line-width 0.3 \
    --title "Species Diversity by Taxonomic Group" \
    --output taxonomy_sunburst.png
```

---

## Features

### Adaptive Font Sizing

Enabled by default. Font size scales based on:
- **Segment angular size** — larger segments get larger text
- **Ring width** — wider rings allow larger text  
- **Hierarchy level** — deeper levels get slightly smaller text

Disable with `--no-adaptive-font` to use legacy fixed sizing.

### Colour Palette

The script uses a hand-picked palette of 20 distinct colours, ordered with blues first:

1. Dark blue, Medium blue, Light blue
2. Greens and teals
3. Yellows and oranges  
4. Reds and purples
5. Greys

Colours are assigned in order of segment size (largest gets first colour). For more than 20 categories, matplotlib colormaps are used.

### Colour Inheritance

The `--color-inherit-level` controls how child segments are coloured:

- **Level 1** (default): Each top-level category gets a unique colour. All descendants inherit variations/shades of their ancestor's colour.
- **Level 2**: Levels 1 and 2 both get unique colours. Level 3+ inherit from their level 2 parent.
- **Level N**: Levels 1 through N get unique colours, deeper levels inherit.

The `--color-mode` controls inheritance style:
- **variations** (default): Progressive shading — children are lighter/darker versions
- **same**: Identical colours — all descendants use exact same colour as parent

---

## CSV Data Requirements

Your CSV must contain:
1. **Sample ID column** — for counting (default: `Sample-ID`)
2. **Hierarchy columns** — 3-5 columns defining the hierarchy levels

### Example CSV Structure

```csv
Sample-ID,Kingdom,Phylum,Class,Order,Family,Species
BGE_001,Animalia,Arthropoda,Insecta,Diptera,Chironomidae,Chironomus riparius
BGE_002,Animalia,Arthropoda,Insecta,Coleoptera,Dytiscidae,Agabus bipustulatus
BGE_003,Animalia,Chordata,Actinopteri,Cypriniformes,Cyprinidae,Rutilus rutilus
```

### Data Processing

- Rows with missing values in hierarchy columns are automatically removed
- String values are trimmed of whitespace
- Segments are sorted by size (largest first) within each level

---

## Output Files

By default, three files are generated:
1. **Primary output** — your specified format (e.g., `chart.png`)
2. **SVG version** — `chart.svg` for vector editing in Illustrator/Inkscape
3. **PDF version** — `chart.pdf` for high-quality printing

Use `--no-auto-formats` to generate only the primary output.

---

## Counting Modes

| Mode | Flag | Behaviour | Use Case |
|------|------|-----------|----------|
| Record counting | (default) | Counts every row in dataset | Sampling effort, specimen counts |
| Unique counting | `--count-unique` | Counts unique values in sample-id column | Species diversity, distinct items |

---

## Troubleshooting

### "Column not found" Error
Check your column names match exactly (case-sensitive). Use `--level1`, `--level2`, etc. to specify correct names.

### Missing Labels on Large Segments
Lower the `--label-threshold` value (default is 5.0 degrees). Try `--label-threshold 2.0` or `--label-threshold 0`.

### Too Many Small Segments
Use `--top-n` to keep only the largest N items, or `--threshold` to group small items into "Other".

### Colours Not as Expected
The palette assigns colours by size order. With more than 20 categories at level 1, matplotlib colormaps are used instead of the hand-picked palette.

### Text Overlap
Increase `--label-threshold` to hide labels on small segments, or use `--label-style name-only` for shorter labels.

---

## Installation

```bash
pip install pandas matplotlib numpy
```

---

## License

This script is provided as-is for research and educational purposes.
