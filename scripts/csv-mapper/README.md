# Sample Mapper - Choropleth Map Generator

A flexible Python script for creating choropleth maps from CSV data showing counts by country. Originally designed for museum specimen data, it now supports any dataset with country information and various counting methods.

## Features

- **Universal Country Mapping**: Works with any set of countries worldwide, not just Europe
- **Flexible Data Counting**: Count rows, all values, or unique values in any column
- **Multiple Color Schemes**: Choose from 10 predefined color palettes
- **Automatic Map Bounds**: Calculates optimal map boundaries based on your data
- **Professional Output**: Generates high-quality PNG and SVG files
- **Robust Country Matching**: Handles various country name formats and variations
- **Scalable Visualization**: Uses logarithmic scaling for wide data ranges

## Requirements

```bash
pip install pandas geopandas matplotlib numpy pathlib
```

## Quick Start

```bash
python sample_mapper.py data.csv output_directory --map-data path/to/shapefiles
```

## Command Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `input_csv` | Path to input CSV file |
| `output_dir` | Directory to save output files |
| `--map-data, -m` | Path to directory containing map data (shapefiles) |

### Optional Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--country-column` | `-c` | `"Country"` | Name of column containing country names |
| `--count-column` | `-cc` | `None` | Column to count values from (if not specified, counts rows) |
| `--unique-count` | `-u` | `False` | Count unique values only (default: count all values) |
| `--border-extension` | `-b` | `5.0` | Degrees to extend map borders beyond data countries |
| `--title` | `-t` | `"Sample Distribution by Country"` | Map title |
| `--shapefile` | `-s` | `None` | Specific shapefile name (auto-detected if not provided) |
| `--colour` | `-col` | `"blue"` | Color scheme for the map |
| `--bounds` | `-bounds` | `None` | Custom map boundaries: min_lon min_lat max_lon max_lat |

### Color Options

Available color schemes for `--colour`:
- `blue` (default) - Professional, general purpose
- `red` - Temperature data, alerts
- `green` - Environmental data, positive metrics
- `purple` - Academic, research data
- `orange` - Seasonal data, energy
- `pink` - Demographics, social data
- `brown` - Earth sciences, geological data
- `grey` - Neutral, black & white printing
- `teal` - Ocean/water data, modern themes
- `yellow` - Heat maps, intensity data

## Usage Examples

### Basic Usage - Count Rows
```bash
python sample_mapper.py museum_data.csv output \
    --map-data ne_110m_admin_0_countries \
    --country-column "Country/Ocean"
```

### Count Unique Species per Country
```bash
python sample_mapper.py biodiversity.csv species_map \
    --map-data ne_50m_admin_0_countries \
    --country-column "Country" \
    --count-column "Species" \
    --unique-count \
    --colour green \
    --title "Species Richness by Country"
```

### Count All Measurements with Custom Styling
```bash
python sample_mapper.py measurements.csv measurements_output \
    --map-data natural_earth_data \
    --country-column "Location" \
    --count-column "Measurement_ID" \
    --colour red \
    --border-extension 8 \
    --title "Total Measurements by Country"
```

### Custom Map Boundaries
```bash
python sample_mapper.py europe_data.csv custom_output \
    --map-data ne_50m_admin_0_countries \
    --bounds -10 35 40 70 \
    --colour teal \
    --title "European Region"
```

### World Map with Minimal Setup
```bash
python sample_mapper.py data.csv world_output \
    --map-data shapefiles \
    --colour purple \
    --border-extension 15
```

## Input Data Requirements

### CSV Structure
Your CSV file must contain:
- A country column (specified with `--country-column`)
- Optionally, a column to count values from (specified with `--count-column`)

### Example Data
```csv
Country,Species,Site_ID,Measurement_ID,Researcher
USA,Quercus alba,SITE001,MEAS001,Dr. Smith
USA,Acer rubrum,SITE001,MEAS002,Dr. Smith  
USA,Quercus alba,SITE002,MEAS003,Dr. Jones
Canada,Acer rubrum,SITE003,MEAS004,Dr. Brown
Canada,Betula nigra,SITE003,MEAS005,Dr. Brown
```

### Counting Examples
With the above data:
- **Rows per country**: USA=3, Canada=2
- **Unique species per country**: USA=2, Canada=2  
- **All measurements per country**: USA=3, Canada=2
- **Unique sites per country**: USA=2, Canada=1

## Map Data Requirements

### Shapefile Format
The script requires Natural Earth or similar shapefiles containing country boundaries. The `--map-data` argument should point to a directory containing:
- `.shp` files (main shapefile)
- `.shx`, `.dbf`, `.prj` files (supporting files)

### Recommended Sources
- [Natural Earth Data](https://www.naturalearthdata.com/) - Free, public domain map data
- Administrative countries datasets (110m, 50m, or 10m resolution)

### Auto-Detection
If multiple shapefiles exist in the directory, the script will:
1. Use the file specified by `--shapefile` if provided
2. Automatically select likely candidates (containing "countries", "admin", etc.)
3. Default to the first `.shp` file found

## Counting Modes

### 1. Row Counting (Default)
```bash
--country-column "Country"
```
Counts the number of rows/records per country.

### 2. All Values Counting
```bash
--country-column "Country" --count-column "Measurements"
```
Counts all non-null values in the specified column per country.

### 3. Unique Values Counting
```bash
--country-column "Country" --count-column "Species" --unique-count
```
Counts distinct values in the specified column per country.

## Output Files

The script generates several output files in the specified output directory:

| File | Description |
|------|-------------|
| `sample_map.png` | High-resolution (300 DPI) choropleth map |
| `sample_map.svg` | Vector format map for publications |
| `sample_charts.png` | Fallback bar charts (if map creation fails) |
| `sample_charts.svg` | Vector format charts |

## Map Features

### Visual Elements
- **Color Coding**: Countries colored by count values using logarithmic scale
- **Country Labels**: Small, non-overlapping count numbers displayed on countries
- **Clean Design**: No legend clutter - just the map and data
- **No-Data Regions**: Countries without data shown in light grey
- **Clean Borders**: White country boundaries for clarity

### Automatic Enhancements
- **Optimal Bounds**: Map boundaries calculated from your data countries or custom bounds
- **Border Extension**: Configurable zoom-out level around data regions
- **Log Scaling**: Automatic logarithmic color scaling for wide value ranges
- **Country Matching**: Fuzzy matching handles name variations
- **French Guiana Exclusion**: Prevents French Guiana from being included in France
- **Smart Label Placement**: Prevents overlapping labels, prioritizes high-value countries

## Country Name Handling

The script includes comprehensive country name mapping to handle variations:

### Supported Variations
- Standard names: "Germany", "France", "United Kingdom"
- Hyphenated forms: "United-Kingdom", "North-Macedonia"
- Alternative names: "USA" → "United States of America"
- Historical names: "Turkiye" → "Turkey"
- Abbreviated forms: "UK" → "United Kingdom"

### Matching Process
1. **Direct Mapping**: Exact matches using built-in country dictionary
2. **Fuzzy Matching**: Partial string matching for close variations
3. **Multiple Columns**: Searches NAME, NAME_LONG, NAME_EN, ADMIN fields in shapefiles

## Error Handling

### Common Issues and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Column not found" | Incorrect column name | Check CSV headers, use exact spelling |
| "No shapefiles found" | Incorrect map data path | Verify directory contains .shp files |
| "No countries matched" | Country name mismatch | Check country names in CSV vs shapefile |
| "Empty results" | NaN values in data | Clean data or check column specifications |

### Validation Features
- Column name validation before processing
- Shapefile existence and format checking
- Output directory creation with error handling
- Detailed progress reporting and matching statistics

## Advanced Usage

### Custom Map Boundaries
You can specify exact map boundaries instead of using automatic calculation:

```bash
# Europe region
python sample_mapper.py data.csv europe_output \
    --map-data shapefiles \
    --bounds -10 35 40 70 \
    --title "European Focus"

# North America
python sample_mapper.py data.csv north_america \
    --map-data shapefiles \
    --bounds -140 20 -50 80 \
    --colour green

# Asia-Pacific  
python sample_mapper.py data.csv asia_pacific \
    --map-data shapefiles \
    --bounds 60 -50 180 80 \
    --colour red
```

Boundaries format: `min_longitude min_latitude max_longitude max_latitude`

### Multiple Maps for Comparison
```bash
# Different counting methods
python sample_mapper.py data.csv output_rows --map-data shapefiles --title "Total Records"
python sample_mapper.py data.csv output_unique --map-data shapefiles --count-column Species --unique-count --title "Unique Species"
```

### Different Resolutions
```bash
# High detail for small regions
python sample_mapper.py data.csv output_hd --map-data ne_10m_admin_0_countries --border-extension 2

# Fast processing for large datasets
python sample_mapper.py data.csv output_fast --map-data ne_110m_admin_0_countries
```

### Publication-Ready Output
```bash
python sample_mapper.py data.csv publication \
    --map-data ne_50m_admin_0_countries \
    --colour grey \
    --title "Research Distribution by Country" \
    --border-extension 3
```

## Performance Tips

- Use 110m resolution shapefiles for faster processing of large datasets
- Use 10m resolution for detailed regional maps
- Unique counting operations are slower than row counting
- PNG files are smaller; SVG files are better for publications

## Troubleshooting

### Map Creation Issues
If map creation fails, the script automatically generates fallback bar charts showing:
- Top 15 countries with highest counts
- All countries on logarithmic scale

### Memory Issues
For very large datasets:
- Use lower resolution shapefiles (110m instead of 10m)
- Filter your CSV data before processing
- Consider processing data in chunks

## License

This script is provided as-is for research and educational purposes. Natural Earth data is public domain. Ensure you have appropriate rights for any other map data used.

## Contributing

When modifying the script:
- Maintain backward compatibility
- Add appropriate error handling
- Update documentation for new features
- Test with various country name formats

## Version History

- **Enhanced Version**: Added flexible counting, color schemes, universal country support
- **Original Version**: Europe-focused museum specimen mapping
