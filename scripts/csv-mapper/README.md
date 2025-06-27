# Sample Mapper - Advanced Choropleth Map Generator

A comprehensive Python script for creating professional choropleth maps from CSV data, showing counts by country with advanced label placement, customizable styling, and flexible data processing options.

## Features

- **Universal Country Mapping**: Works with any set of countries worldwide
- **Flexible Data Counting**: Count rows, all values, or unique values in any column
- **Smart Label Placement**: Hybrid positioning system with manual overrides for optimal readability
- **Multiple Color Schemes**: Choose from 10 predefined color palettes
- **Custom Map Boundaries**: Specify exact latitude/longitude bounds or auto-calculate from data
- **Professional Output**: Generates publication-quality PNG and SVG files
- **Robust Country Matching**: Handles various country name formats and variations
- **Advanced Visualization**: Logarithmic scaling, overlap prevention, clean design
- **French Guiana Handling**: Prevents French Guiana from being included as part of France

## Requirements

```bash
pip install pandas geopandas matplotlib numpy pathlib
```

## Quick Start

```bash
python sample_mapper.py data.csv output_directory --map-data path/to/shapefiles
```

## Complete Command Line Reference

### Required Arguments

| Argument | Description |
|----------|-------------|
| `input_csv` | Path to input CSV file |
| `output_dir` | Directory to save output files |
| `--map-data, -m` | Path to directory containing map data (shapefiles) |

### Optional Arguments

| Argument | Short | Default | Type | Description |
|----------|-------|---------|------|-------------|
| `--country-column` | `-c` | `"Country"` | String | Name of column containing country names |
| `--count-column` | `-cc` | `None` | String | Column to count values from (if not specified, counts rows) |
| `--unique-count` | `-u` | `False` | Flag | Count unique values only (default: count all values) |
| `--border-extension` | `-b` | `5.0` | Float | Degrees to extend map borders beyond data countries |
| `--title` | `-t` | `"Sample Distribution by Country"` | String | Map title |
| `--shapefile` | `-s` | `None` | String | Specific shapefile name (auto-detected if not provided) |
| `--colour` | `-col` | `"blue"` | Choice | Color scheme for the map |
| `--bounds` | `-bounds` | `None` | 4 Floats | Custom map boundaries: min_lon min_lat max_lon max_lat |

### Color Options

Available color schemes for `--colour`:
- `blue` (default) - Professional, general purpose
- `red` - Temperature data, alerts, critical metrics
- `green` - Environmental data, positive metrics, growth
- `purple` - Academic, research data, elegant presentations
- `orange` - Seasonal data, energy, warm themes
- `pink` - Demographics, social data, approachable themes
- `brown` - Earth sciences, geological data, natural materials
- `grey` - Neutral, black & white printing, formal documents
- `teal` - Ocean/water data, modern themes, technology
- `yellow` - Heat maps, intensity data, attention-grabbing

## Core Functions Overview

### Data Processing Functions

#### `load_and_process_data(csv_path, country_column, count_column, unique_count)`
- Loads CSV file and validates column existence
- Processes data based on counting mode:
  - **Row counting**: Counts records per country
  - **All values**: Counts non-null values in specified column
  - **Unique values**: Counts distinct values in specified column
- Returns sorted Series with country counts

#### `find_shapefile(map_data_dir, shapefile_name)`
- Automatically discovers shapefiles in directory
- Uses heuristics to select likely candidates
- Supports manual shapefile specification
- Validates file existence and accessibility

### Visualization Functions

#### `get_colormap(colour_name)`
- Maps color names to matplotlib colormaps
- Provides consistent color schemes across outputs
- Supports 10 predefined color options

#### `create_choropleth_map(country_counts, shapefile_path, output_dir, title, border_extension, colour, custom_bounds)`
- Main visualization function
- Creates choropleth map with logarithmic color scaling
- Applies smart label placement
- Generates PNG and SVG outputs
- Handles custom boundaries and styling

#### `create_fallback_charts(country_counts, output_dir, title, colour)`
- Generates bar charts if map creation fails
- Shows top 15 countries and log-scale overview
- Uses consistent color schemes

### Geographic Functions

#### `calculate_map_bounds(world_gdf, country_names, border_extension, custom_bounds)`
- Auto-calculates optimal map boundaries from data
- Supports custom boundary specification
- Applies configurable border extension
- Ensures valid latitude/longitude ranges

#### `create_country_mapping()`
- Comprehensive country name standardization
- Handles variations: "USA" → "United States of America"
- Supports historical and alternative names
- Enables fuzzy matching for data integration

### Label Placement System

#### `get_optimal_label_position(row, bounds)`
**Hybrid approach for professional label placement:**

1. **Manual Overrides** (Priority 1)
   - Pre-defined coordinates for 20+ problematic countries
   - France: Mainland France (not French Guiana)
   - Norway: Central mainland (not fjords)
   - Russia: European Russia (not Siberia)

2. **Representative Point** (Priority 2)
   - GeoPandas `representative_point()` method
   - Guaranteed inside country geometry
   - Handles complex coastlines automatically

3. **Largest Polygon Centroid** (Priority 3)
   - For MultiPolygon countries, uses main landmass
   - Eliminates overseas territory issues
   - Fallback for edge cases

#### `get_label_position_overrides()`
- Returns dictionary of manual position coordinates
- Covers major countries with problematic geometry
- Optimized for visual clarity and accuracy

#### `check_label_overlap(new_x, new_y, existing_positions, min_distance)`
- Prevents label clustering and overlap
- Configurable minimum distance (default: 1.5 degrees)
- Prioritizes high-value countries for placement

## Usage Examples

### Basic Usage Examples

#### 1. Simple Row Count Map
```bash
python sample_mapper.py museum_data.csv output \
    --map-data ne_110m_admin_0_countries \
    --country-column "Country/Ocean" \
    --title "Museum Records by Country"
```

#### 2. Count Unique Species (Biodiversity)
```bash
python sample_mapper.py biodiversity.csv species_map \
    --map-data ne_50m_admin_0_countries \
    --country-column "Country" \
    --count-column "Species" \
    --unique-count \
    --colour green \
    --title "Species Richness by Country"
```

#### 3. Count All Measurements with Custom Styling
```bash
python sample_mapper.py measurements.csv measurements_output \
    --map-data natural_earth_data \
    --country-column "Location" \
    --count-column "Measurement_ID" \
    --colour red \
    --border-extension 8 \
    --title "Total Measurements by Country"
```

### Advanced Usage Examples

#### 4. Custom Map Boundaries - Europe Focus
```bash
python sample_mapper.py europe_data.csv europe_output \
    --map-data ne_50m_admin_0_countries \
    --bounds -15 35 45 72 \
    --colour purple \
    --title "European Research Distribution" \
    --border-extension 0
```

#### 5. North America Regional Map
```bash
python sample_mapper.py north_america.csv na_output \
    --map-data ne_10m_admin_0_countries \
    --bounds -140 20 -50 80 \
    --country-column "Nation" \
    --count-column "Publications" \
    --colour teal \
    --title "Research Publications - North America"
```

#### 6. Asia-Pacific High Resolution
```bash
python sample_mapper.py asia_pacific.csv ap_output \
    --map-data ne_10m_admin_0_countries \
    --bounds 60 -50 180 80 \
    --count-column "Research_Sites" \
    --unique-count \
    --colour orange \
    --title "Unique Research Sites - Asia Pacific"
```

#### 7. Global Overview with Custom Shapefile
```bash
python sample_mapper.py global_data.csv world_output \
    --map-data /path/to/custom_shapefiles \
    --shapefile world_countries.shp \
    --count-column "Sample_ID" \
    --colour grey \
    --border-extension 10 \
    --title "Global Sample Distribution"
```

### Specialized Use Cases

#### 8. Climate Research Stations
```bash
python sample_mapper.py climate_stations.csv climate_map \
    --map-data ne_50m_admin_0_countries \
    --country-column "Host_Country" \
    --count-column "Station_ID" \
    --unique-count \
    --colour blue \
    --title "Climate Monitoring Stations" \
    --bounds -180 -60 180 85
```

#### 9. Marine Biodiversity Study
```bash
python sample_mapper.py marine_samples.csv marine_output \
    --map-data ne_50m_admin_0_countries \
    --country-column "Coastal_Nation" \
    --count-column "Marine_Species" \
    --unique-count \
    --colour teal \
    --title "Marine Species Diversity by Coastal Nation"
```

#### 10. Academic Collaboration Network
```bash
python sample_mapper.py collaborations.csv academic_map \
    --map-data ne_110m_admin_0_countries \
    --country-column "Institution_Country" \
    --count-column "Collaboration_ID" \
    --colour purple \
    --title "International Research Collaborations"
```

## Input Data Requirements

### CSV Structure
Your CSV file must contain:
- A country column (specified with `--country-column`)
- Optionally, a column to count values from (specified with `--count-column`)

### Example Data Structures

#### Research Dataset
```csv
Country,Species,Site_ID,Measurement_ID,Researcher,Publication_Year
USA,Quercus alba,SITE001,MEAS001,Dr. Smith,2023
USA,Acer rubrum,SITE001,MEAS002,Dr. Smith,2023
USA,Quercus alba,SITE002,MEAS003,Dr. Jones,2024
Canada,Acer rubrum,SITE003,MEAS004,Dr. Brown,2023
Canada,Betula nigra,SITE003,MEAS005,Dr. Brown,2024
```

#### Climate Data
```csv
Nation,Station_Name,Temperature,Precipitation,Year
Norway,Bergen_Station,12.5,150.2,2023
Norway,Oslo_Station,8.1,120.8,2023
Sweden,Stockholm_Station,9.8,95.4,2023
Denmark,Copenhagen_Station,11.2,88.9,2023
```

### Counting Examples
With the research dataset above:
- **Rows per country**: USA=3, Canada=2
- **Unique species per country**: USA=2, Canada=2  
- **All measurements per country**: USA=3, Canada=2
- **Unique sites per country**: USA=2, Canada=1
- **Unique researchers per country**: USA=2, Canada=1

## Map Data Requirements

### Shapefile Format
Requires Natural Earth or compatible shapefiles with:
- `.shp` (main shapefile)
- `.shx`, `.dbf`, `.prj` (supporting files)
- Country name fields: NAME, NAME_LONG, NAME_EN, or ADMIN

### Recommended Sources
- [Natural Earth Data](https://www.naturalearthdata.com/) - Free, public domain
- Resolution options: 110m (fast), 50m (balanced), 10m (detailed)
- Administrative countries datasets

### Auto-Detection Logic
1. Use `--shapefile` if specified
2. Search for files containing "countries", "admin", "ne_"
3. Default to first `.shp` file found

## Counting Modes Detailed

### 1. Row Counting (Default)
```bash
--country-column "Country"
# Counts: Number of records/samples per country
```

### 2. All Values Counting
```bash
--country-column "Country" --count-column "Measurements"
# Counts: All non-null values in specified column per country
```

### 3. Unique Values Counting
```bash
--country-column "Country" --count-column "Species" --unique-count
# Counts: Distinct values in specified column per country
```

## Output Files

Generated in the specified output directory:

| File | Format | Description | Use Case |
|------|--------|-------------|----------|
| `sample_map.png` | PNG (300 DPI) | High-resolution raster | Web display, presentations |
| `sample_map.svg` | SVG | Vector graphics | Publications, print media |
| `sample_charts.png` | PNG (300 DPI) | Fallback bar charts | If map creation fails |
| `sample_charts.svg` | SVG | Vector charts | Publication backup |

## Advanced Features

### Smart Label Placement
- **Overlap Prevention**: Minimum 1.5-degree spacing
- **Priority System**: Higher counts get placement priority
- **Boundary Validation**: Labels only within map bounds
- **Hybrid Positioning**: Manual overrides + automatic algorithms

### Geographic Intelligence
- **French Guiana Exclusion**: Separated from France for accurate labeling
- **Complex Coastlines**: Handles fjords, islands, inland water
- **MultiPolygon Support**: Focuses on main landmass for countries with territories
- **Projection Handling**: Works with various coordinate systems

### Visual Optimization
- **Logarithmic Scaling**: Automatic for wide value ranges
- **Clean Design**: No legend clutter, focus on data
- **Professional Styling**: Publication-ready output
- **Color Psychology**: Thematically appropriate color schemes

## Error Handling & Troubleshooting

### Common Issues and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Column not found" | Incorrect column name | Check CSV headers, use exact spelling |
| "No shapefiles found" | Wrong map data path | Verify directory contains .shp files |
| "No countries matched" | Country name mismatch | Check country names in CSV vs shapefile |
| "Empty results" | NaN values in data | Clean data or check column specifications |
| "Bounds error" | Invalid coordinates | Use proper lat/lon ranges (-180 to 180, -90 to 90) |

### Validation Features
- Pre-processing column validation
- Shapefile format verification
- Country name matching statistics
- Boundary constraint checking
- Output directory creation with error handling

### Performance Optimization
- **Large Datasets**: Use 110m resolution shapefiles
- **High Detail**: Use 10m resolution for regional maps
- **Memory Efficiency**: Automatic data filtering by bounds
- **Processing Speed**: Optimized country matching algorithms

## Boundary Specifications

### Common Regional Boundaries
```bash
# Europe (extended)
--bounds -15 35 45 72

# Europe (core)
--bounds -10 35 40 70

# North America
--bounds -140 20 -50 80

# South America
--bounds -85 -60 -30 15

# Africa
--bounds -20 -40 55 40

# Asia
--bounds 25 5 150 80

# Asia-Pacific
--bounds 60 -50 180 80

# Middle East
--bounds 25 10 65 45

# Caribbean
--bounds -90 10 -55 30

# Mediterranean
--bounds -10 30 40 50
```

### Custom Boundary Tips
- **Longitude**: -180 to 180 (West to East)
- **Latitude**: -90 to 90 (South to North)
- **Order**: min_lon min_lat max_lon max_lat
- **Extension**: Use `--border-extension 0` with custom bounds for exact framing

## Publication Guidelines

### Academic Papers
```bash
--colour grey --title "Clear Descriptive Title" --border-extension 3
```

### Presentations
```bash
--colour blue --title "Engaging Title" --border-extension 5
```

### Environmental Reports
```bash
--colour green --title "Conservation Data" --border-extension 4
```

### Web Content
```bash
--colour teal --title "Interactive Data Story" --border-extension 6
```

## Version History & Compatibility

- **Current Version**: Enhanced with hybrid label placement
- **Python**: 3.7+ required
- **Dependencies**: pandas, geopandas, matplotlib, numpy
- **Backward Compatibility**: Maintains original API
- **New Features**: Custom bounds, smart labeling, color schemes

## Contributing

When extending the script:
- Maintain existing argument compatibility
- Add comprehensive error handling
- Update country mapping dictionary as needed
- Test with various data formats and map projections
- Document new features with examples

This script provides enterprise-grade choropleth mapping capabilities suitable for academic research, business intelligence, and professional publications.
