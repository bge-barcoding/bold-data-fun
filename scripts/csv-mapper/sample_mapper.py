#!/usr/bin/env python3
"""
Script to create a choropleth map showing counts by country.

"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import os
import warnings
import argparse
import sys
from pathlib import Path
warnings.filterwarnings('ignore')

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create choropleth map from CSV data')
    
    parser.add_argument('input_csv', 
                       help='Path to input CSV file')
    parser.add_argument('output_dir', 
                       help='Directory to save output files')
    parser.add_argument('--map-data', '-m',
                       required=True,
                       help='Path to directory containing map data (shapefiles)')
    parser.add_argument('--country-column', '-c',
                       default='Country',
                       help='Name of column containing country names (default: Country)')
    parser.add_argument('--count-column', '-cc',
                       help='Column to count values from (if not specified, counts rows per country)')
    parser.add_argument('--unique-count', '-u',
                       action='store_true',
                       help='Count unique values only (default: count all values)')
    parser.add_argument('--border-extension', '-b',
                       type=float,
                       default=5.0,
                       help='Degrees to extend map borders beyond data countries (default: 5.0)')
    parser.add_argument('--title', '-t',
                       default='Sample Distribution by Country',
                       help='Map title (default: "Sample Distribution by Country")')
    parser.add_argument('--shapefile', '-s',
                       help='Specific shapefile name (if not provided, will search for .shp files)')
    parser.add_argument('--colour', '-col',
                       default='blue',
                       choices=['blue', 'red', 'green', 'purple', 'orange', 'pink', 'brown', 'grey', 'teal', 'yellow'],
                       help='Color scheme for the map (default: blue)')
    parser.add_argument('--bounds', '-bounds',
                       nargs=4,
                       type=float,
                       metavar=('MIN_LON', 'MIN_LAT', 'MAX_LON', 'MAX_LAT'),
                       help='Map boundaries as: min_longitude min_latitude max_longitude max_latitude')
    
    return parser.parse_args()

def find_shapefile(map_data_dir, shapefile_name=None):
    """Find shapefile in the map data directory."""
    map_data_path = Path(map_data_dir)
    
    if not map_data_path.exists():
        print(f"Error: Map data directory does not exist: {map_data_dir}")
        return None
    
    if shapefile_name:
        # Use specific shapefile
        shapefile_path = map_data_path / shapefile_name
        if not shapefile_path.exists():
            print(f"Error: Specified shapefile does not exist: {shapefile_path}")
            return None
        return str(shapefile_path)
    
    # Search for shapefiles
    shapefiles = list(map_data_path.rglob("*.shp"))
    
    if not shapefiles:
        print(f"Error: No shapefiles found in {map_data_dir}")
        return None
    
    if len(shapefiles) == 1:
        print(f"Found shapefile: {shapefiles[0]}")
        return str(shapefiles[0])
    
    # Multiple shapefiles found, let user choose or use heuristics
    print(f"Multiple shapefiles found in {map_data_dir}:")
    for i, sf in enumerate(shapefiles):
        print(f"  {i+1}. {sf.name}")
    
    # Try to find a likely candidate (countries, admin, etc.)
    likely_names = ['countries', 'admin', 'ne_', 'world']
    for shapefile in shapefiles:
        for name in likely_names:
            if name.lower() in shapefile.name.lower():
                print(f"Using likely candidate: {shapefile.name}")
                return str(shapefile)
    
    # Default to first one
    print(f"Using first shapefile: {shapefiles[0].name}")
    return str(shapefiles[0])

def load_and_process_data(csv_path, country_column, count_column=None, unique_count=False):
    """Load CSV data and count values per country."""
    print("Loading CSV data...")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return None
    
    if country_column not in df.columns:
        print(f"Error: Column '{country_column}' not found in CSV file.")
        print(f"Available columns: {list(df.columns)}")
        return None
    
    if count_column and count_column not in df.columns:
        print(f"Error: Count column '{count_column}' not found in CSV file.")
        print(f"Available columns: {list(df.columns)}")
        return None
    
    print(f"Total rows in dataset: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Remove rows where country column is NaN
    df_clean = df.dropna(subset=[country_column])
    print(f"Rows after removing NaN countries: {len(df_clean)}")
    
    if count_column:
        # Count values in the specified column per country
        if unique_count:
            print(f"Counting unique values in '{count_column}' per country...")
            # Group by country and count unique values in count_column
            country_counts = df_clean.groupby(country_column)[count_column].nunique()
            count_type = "unique values"
        else:
            print(f"Counting all non-null values in '{count_column}' per country...")
            # Group by country and count non-null values in count_column
            country_counts = df_clean.groupby(country_column)[count_column].count()
            count_type = "values"
        
        # Convert to Series with same interface as value_counts()
        country_counts = country_counts.sort_values(ascending=False)
        print(f"\n{count_type.title()} in '{count_column}' by country:")
        
    else:
        # Count rows (samples) per country
        print("Counting rows (samples) per country...")
        country_counts = df_clean[country_column].value_counts()
        count_type = "rows"
        print(f"\nRow counts by country:")
    
    print(country_counts.head(10))  # Show top 10
    if len(country_counts) > 10:
        print(f"... and {len(country_counts)-10} more countries")
    
    print(f"\nCount type: {count_type}")
    if count_column:
        print(f"Count column: {count_column}")
    print(f"Country column: {country_column}")
    
    return country_counts

def get_colormap(colour_name):
    """Get matplotlib colormap based on colour name."""
    colour_maps = {
        'blue': 'Blues',
        'red': 'Reds', 
        'green': 'Greens',
        'purple': 'Purples',
        'orange': 'Oranges',
        'pink': 'RdPu',  # Red-Purple for pink effect
        'brown': 'copper',  # Copper gives brown tones
        'grey': 'Greys',
        'teal': 'GnBu',  # Green-Blue for teal
        'yellow': 'YlOrRd'  # Yellow-Orange-Red for yellow base
    }
    
    return colour_maps.get(colour_name, 'Blues')

def check_label_overlap(new_x, new_y, existing_positions, min_distance=1.5):
    """Check if a new label position would overlap with existing labels."""
    for existing_x, existing_y in existing_positions:
        distance = ((new_x - existing_x)**2 + (new_y - existing_y)**2)**0.5
        if distance < min_distance:
            return True
    return False

def create_country_mapping():
    """Create mapping between data country names and Natural Earth country names."""
    return {
        # Direct matches
        'Greece': 'Greece',
        'Italy': 'Italy', 
        'Spain': 'Spain',
        'Norway': 'Norway',
        'Germany': 'Germany',
        'France': 'France',
        'Portugal': 'Portugal',
        'Switzerland': 'Switzerland',
        'Austria': 'Austria',
        'Belgium': 'Belgium',
        'Netherlands': 'Netherlands',
        'Denmark': 'Denmark',
        'Sweden': 'Sweden',
        'Finland': 'Finland',
        'Poland': 'Poland',
        'Hungary': 'Hungary',
        'Romania': 'Romania',
        'Bulgaria': 'Bulgaria',
        'Croatia': 'Croatia',
        'Slovenia': 'Slovenia',
        'Slovakia': 'Slovakia',
        'Estonia': 'Estonia',
        'Latvia': 'Latvia',
        'Lithuania': 'Lithuania',
        'Ireland': 'Ireland',
        'Iceland': 'Iceland',
        'Cyprus': 'Cyprus',
        'Malta': 'Malta',
        'Luxembourg': 'Luxembourg',
        'Moldova': 'Moldova',
        'Ukraine': 'Ukraine',
        'Belarus': 'Belarus',
        'Serbia': 'Serbia',
        'Montenegro': 'Montenegro',
        'Albania': 'Albania',
        'San Marino': 'San Marino',
        # Special mappings for variations
        'United Kingdom': 'United Kingdom',
        'United-Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'North-Macedonia': 'North Macedonia',
        'Bosnia-Herzegovina': 'Bosnia and Herz.',  # Natural Earth uses abbreviated form
        'Czech Republic': 'Czechia',  # Natural Earth uses "Czechia"
        'North Macedonia': 'North Macedonia',
        'Bosnia and Herzegovina': 'Bosnia and Herz.',
        'Turkiye': 'Turkey',  # Handle Turkey name variation
        'Turkey': 'Turkey',
        # Additional common mappings
        'USA': 'United States of America',
        'United States': 'United States of America',
        'US': 'United States of America',
        'Russia': 'Russia',
        'Russian Federation': 'Russia',
        'China': 'China',
        'India': 'India',
        'Canada': 'Canada',
        'Australia': 'Australia',
        'Brazil': 'Brazil',
        'Mexico': 'Mexico',
        'Japan': 'Japan',
        'South Korea': 'South Korea',
        'Korea': 'South Korea',
        'New Zealand': 'New Zealand',
        'South Africa': 'South Africa',
        'Egypt': 'Egypt',
        'Morocco': 'Morocco',
        'Argentina': 'Argentina',
        'Chile': 'Chile',
        'Peru': 'Peru',
        'Colombia': 'Colombia',
        'Venezuela': 'Venezuela',
        'Iran': 'Iran',
        'Iraq': 'Iraq',
        'Israel': 'Israel',
        'Saudi Arabia': 'Saudi Arabia',
        'Thailand': 'Thailand',
        'Indonesia': 'Indonesia',
        'Philippines': 'Philippines',
        'Malaysia': 'Malaysia',
        'Singapore': 'Singapore',
        'Vietnam': 'Vietnam',
    }

def calculate_map_bounds(world_gdf, country_names, border_extension, custom_bounds=None):
    """Calculate map bounds based on countries in the data with extension or use custom bounds."""
    
    if custom_bounds:
        min_lon, min_lat, max_lon, max_lat = custom_bounds
        print(f"Using custom map bounds: {min_lon}, {min_lat}, {max_lon}, {max_lat}")
        return {
            'min_lon': min_lon,
            'max_lon': max_lon,
            'min_lat': min_lat,
            'max_lat': max_lat
        }
    
    # Get country mapping
    country_mapping = create_country_mapping()
    
    # Find matching countries in the world data
    matched_countries = []
    
    for country in country_names:
        matched = False
        
        # Try direct mapping first
        mapped_name = country_mapping.get(country, country)
        
        # Try multiple name columns
        for name_col in ['NAME', 'NAME_LONG', 'NAME_EN', 'ADMIN']:
            if name_col in world_gdf.columns:
                mask = world_gdf[name_col] == mapped_name
                if mask.any():
                    matched_countries.extend(world_gdf[mask].index.tolist())
                    matched = True
                    break
        
        # If no direct mapping, try fuzzy matching
        if not matched:
            for name_col in ['NAME', 'NAME_LONG', 'NAME_EN', 'ADMIN']:
                if name_col in world_gdf.columns:
                    mask = world_gdf[name_col].astype(str).str.contains(country, case=False, na=False)
                    if mask.any():
                        matched_countries.extend(world_gdf[mask].index.tolist())
                        matched = True
                        break
    
    if not matched_countries:
        print("Warning: No countries matched in map data. Using world bounds.")
        bounds = world_gdf.total_bounds
    else:
        # Get bounds of matched countries
        matched_gdf = world_gdf.loc[matched_countries]
        bounds = matched_gdf.total_bounds
    
    # Extend bounds
    min_lon, min_lat, max_lon, max_lat = bounds
    min_lon -= border_extension
    max_lon += border_extension
    min_lat -= border_extension
    max_lat += border_extension
    
    # Ensure bounds are within valid ranges
    min_lon = max(min_lon, -180)
    max_lon = min(max_lon, 180)
    min_lat = max(min_lat, -90)
    max_lat = min(max_lat, 90)
    
    return {
        'min_lon': min_lon,
        'max_lon': max_lon,
        'min_lat': min_lat,
        'max_lat': max_lat
    }

def create_choropleth_map(country_counts, shapefile_path, output_dir, title, border_extension, colour, custom_bounds=None):
    """Create choropleth map with sample counts."""
    print(f"\nCreating choropleth map with {colour} color scheme...")
    
    try:
        world = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"Error reading shapefile: {e}")
        return None
    
    print(f"Loaded world data with {len(world)} features")
    
    # Filter out French Guiana from France if it exists as a separate feature
    # French Guiana often has NAME="French Guiana" or similar
    if 'NAME' in world.columns:
        world = world[~world['NAME'].str.contains('French Guiana', case=False, na=False)]
    if 'NAME_EN' in world.columns:
        world = world[~world['NAME_EN'].str.contains('French Guiana', case=False, na=False)]
    
    # Calculate map bounds based on countries in data or use custom bounds
    bounds = calculate_map_bounds(world, country_counts.index, border_extension, custom_bounds)
    print(f"Map bounds: {bounds}")
    
    # Filter countries within bounds
    try:
        map_region = world.cx[bounds['min_lon']:bounds['max_lon'], 
                             bounds['min_lat']:bounds['max_lat']].copy()
    except Exception as e:
        print(f"Error filtering by bounds, using full world data: {e}")
        map_region = world.copy()
    
    print(f"Found {len(map_region)} countries in map region")
    
    # Get country mapping
    country_mapping = create_country_mapping()
    
    # Add sample counts to the map data
    map_region['sample_count'] = 0
    
    # Map the sample counts
    matched_countries = 0
    unmatched_countries = []
    
    for data_country, count in country_counts.items():
        matched = False
        
        # First try direct mapping
        mapped_name = country_mapping.get(data_country, data_country)
        
        # Try multiple name columns
        for name_col in ['NAME', 'NAME_LONG', 'NAME_EN', 'ADMIN']:
            if name_col in map_region.columns:
                mask = map_region[name_col] == mapped_name
                if mask.any():
                    map_region.loc[mask, 'sample_count'] = count
                    matched_countries += 1
                    matched = True
                    print(f"Matched: {data_country} -> {mapped_name} ({count} counts)")
                    break
        
        # If no direct mapping, try fuzzy matching
        if not matched:
            for name_col in ['NAME', 'NAME_LONG', 'NAME_EN', 'ADMIN']:
                if name_col in map_region.columns:
                    # Try partial matching
                    mask = map_region[name_col].astype(str).str.contains(data_country, case=False, na=False)
                    if mask.any():
                        map_region.loc[mask, 'sample_count'] = count
                        matched_countries += 1
                        matched = True
                        matched_to = map_region.loc[mask, name_col].iloc[0]
                        print(f"Fuzzy matched: {data_country} -> {matched_to} ({count} counts)")
                        break
        
        if not matched:
            unmatched_countries.append(f"{data_country} ({count})")
    
    print(f"\nMatched {matched_countries} countries out of {len(country_counts)} in dataset")
    if unmatched_countries:
        print(f"Unmatched countries: {', '.join(unmatched_countries[:10])}")  # Show first 10
    
    # Create the map
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    
    # Get the colormap for the selected colour
    cmap_name = get_colormap(colour)
    
    # Define color scheme - using a better colormap for the data range
    max_counts = country_counts.max()
    min_counts = 1
    
    # Use log scale for better visualization since there's a large range
    map_region['log_count'] = np.log10(map_region['sample_count'] + 1)  # +1 to handle 0 values
    
    # Plot countries without data in light gray
    no_data = map_region[map_region['sample_count'] == 0]
    no_data.plot(ax=ax, color='#f0f0f0', edgecolor='white', linewidth=0.5)
    
    # Plot countries with data using color scale
    with_data = map_region[map_region['sample_count'] > 0]
    if len(with_data) > 0:
        with_data.plot(column='log_count', 
                      ax=ax, 
                      cmap=cmap_name,
                      legend=False,  # Remove legend
                      edgecolor='white',
                      linewidth=0.5)
    
    # Customize the map
    ax.set_xlim(bounds['min_lon'], bounds['max_lon'])
    ax.set_ylim(bounds['min_lat'], bounds['max_lat'])
    ax.set_title(title, fontsize=22, fontweight='bold', pad=30)
    
    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Add count labels for countries with data (with overlap prevention)
    label_positions = []  # Track label positions to prevent overlap
    
    # Sort countries by count (highest first) so important labels get priority
    countries_with_data = map_region[map_region['sample_count'] > 0].copy()
    countries_with_data = countries_with_data.sort_values('sample_count', ascending=False)
    
    for idx, row in countries_with_data.iterrows():
        try:
            centroid = row.geometry.centroid
            centroid_x = centroid.x
            centroid_y = centroid.y
            
            # Only add label if centroid is within bounds
            if (bounds['min_lon'] <= centroid_x <= bounds['max_lon'] and 
                bounds['min_lat'] <= centroid_y <= bounds['max_lat']):
                
                # Check for overlap with existing labels
                if not check_label_overlap(centroid_x, centroid_y, label_positions):
                    ax.annotate(f"{int(row['sample_count']):,}",
                               xy=(centroid_x, centroid_y),
                               ha='center', va='center',
                               fontsize=10,  # Smaller font size
                               fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.2',  # Smaller padding
                                       facecolor='white', 
                                       alpha=0.9,
                                       edgecolor='black',
                                       linewidth=0.3))  # Thinner border
                    
                    # Record this position
                    label_positions.append((centroid_x, centroid_y))
        except:
            continue  # Skip if centroid calculation fails
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save as PNG
    png_path = os.path.join(output_dir, "sample_map.png")
    plt.savefig(png_path, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"Map saved as PNG: {png_path}")
    
    # Save as SVG
    svg_path = os.path.join(output_dir, "sample_map.svg")
    plt.savefig(svg_path, format='svg', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"Map saved as SVG: {svg_path}")
    
    plt.show()
    
    return fig, ax

def create_fallback_charts(country_counts, output_dir, title, colour):
    """Create fallback charts if map creation fails."""
    print(f"Creating fallback charts with {colour} color scheme...")
    
    # Get colormap for charts
    cmap_name = get_colormap(colour)
    
    # Create figure with subplots for better layout
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Chart 1: Top 15 countries
    top_15 = country_counts.head(15)
    bars1 = ax1.barh(range(len(top_15)), top_15.values[::-1])
    ax1.set_yticks(range(len(top_15)))
    ax1.set_yticklabels(top_15.index[::-1])
    ax1.set_xlabel('Number of Samples', fontsize=12)
    ax1.set_title(f'Top 15 Countries - {title}', fontsize=14, fontweight='bold')
    
    # Color bars with gradient using selected colormap
    colors1 = plt.cm.get_cmap(cmap_name)(np.linspace(0.3, 1, len(top_15)))
    for bar, color in zip(bars1, colors1):
        bar.set_color(color)
    
    # Add value labels
    for i, count in enumerate(top_15.values[::-1]):
        ax1.text(count + max(top_15.values) * 0.01, i, 
                f'{count:,}', va='center', ha='left', fontsize=9)
    
    ax1.grid(axis='x', alpha=0.3)
    
    # Chart 2: All countries (log scale)
    all_counts_log = np.log10(country_counts.values)
    bars2 = ax2.barh(range(len(country_counts)), all_counts_log[::-1])
    ax2.set_yticks(range(0, len(country_counts), max(1, len(country_counts)//20)))  # Show every nth country
    ax2.set_yticklabels([country_counts.index[::-1][i] for i in range(0, len(country_counts), max(1, len(country_counts)//20))])
    ax2.set_xlabel('Log₁₀(Number of Samples)', fontsize=12)
    ax2.set_title('All Countries - Log Scale', fontsize=14, fontweight='bold')
    
    # Color bars using alternative colormap for contrast
    alt_cmap = 'plasma' if cmap_name != 'plasma' else 'viridis'
    colors2 = plt.cm.get_cmap(alt_cmap)(np.linspace(0.2, 1, len(country_counts)))
    for bar, color in zip(bars2, colors2):
        bar.set_color(color)
    
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save files
    png_path = os.path.join(output_dir, "sample_charts.png")
    svg_path = os.path.join(output_dir, "sample_charts.svg")
    
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.savefig(svg_path, format='svg', bbox_inches='tight')
    
    print(f"Charts saved as PNG: {png_path}")
    print(f"Charts saved as SVG: {svg_path}")
    
    plt.show()

def main():
    """Main function to run the mapping script."""
    args = parse_arguments()
    
    try:
        # Find shapefile
        shapefile_path = find_shapefile(args.map_data, args.shapefile)
        if not shapefile_path:
            print("Error: Could not find valid shapefile.")
            sys.exit(1)
        
        # Load and process the data
        country_counts = load_and_process_data(args.input_csv, args.country_column, 
                                             args.count_column, args.unique_count)
        if country_counts is None:
            sys.exit(1)
        
        # Create the map
        result = create_choropleth_map(country_counts, shapefile_path, args.output_dir, 
                                     args.title, args.border_extension, args.colour, args.bounds)
        
        if result is not None:
            print("\nMapping complete!")
            print(f"Files saved in: {args.output_dir}")
        else:
            print("\nMap creation failed. Creating fallback charts...")
            create_fallback_charts(country_counts, args.output_dir, args.title, args.colour)
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
