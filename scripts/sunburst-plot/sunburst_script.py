#!/usr/bin/env python3
"""
Enhanced Sunburst Chart Generator
Creates a hierarchical sunburst plot with optional small slice aggregation and customizable line thickness
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
import sys
from collections import defaultdict
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

def load_and_process_data(csv_file, sample_id_col, level_cols, count_unique=False):
    """
    Load CSV and process hierarchical data for up to 5 levels
    """
    try:
        df = pd.read_csv(csv_file, low_memory=False)
        print(f"Loaded {len(df)} rows from {csv_file}")
        
        # Filter out None values and empty strings from level_cols
        active_levels = [col for col in level_cols if col and col.strip()]
        
        # Filter out rows with missing data in key columns
        required_cols = [sample_id_col] + active_levels
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in CSV. Available columns: {list(df.columns)}")
        
        df_clean = df.dropna(subset=required_cols)
        print(f"After removing rows with missing data: {len(df_clean)} rows")
        print(f"Active hierarchy levels: {len(active_levels)} - {active_levels}")
        
        # Build hierarchical structure dynamically
        def build_nested_dict(depth):
            if depth == 0:
                return set if count_unique else int
            return lambda: defaultdict(build_nested_dict(depth - 1))
        
        hierarchy = defaultdict(build_nested_dict(len(active_levels) - 1))
        
        for _, row in df_clean.iterrows():
            current_level = hierarchy
            for i, level_col in enumerate(active_levels):
                key = str(row[level_col]).strip()
                if i == len(active_levels) - 1:
                    if count_unique:
                        current_level[key].add(str(row[sample_id_col]).strip())
                    else:
                        current_level[key] += 1
                else:
                    current_level = current_level[key]
        
        # Convert sets to counts if using count_unique
        if count_unique:
            def convert_sets_to_counts(obj):
                if isinstance(obj, set):
                    return len(obj)
                elif isinstance(obj, defaultdict):
                    return defaultdict(int, {k: convert_sets_to_counts(v) for k, v in obj.items()})
                return obj
            
            hierarchy = convert_sets_to_counts(hierarchy)
            # Calculate total unique values
            total_count = sum(calculate_total_recursive(v) for v in hierarchy.values())
        else:
            total_count = len(df_clean)
        
        return hierarchy, total_count, active_levels
        
    except Exception as e:
        print(f"Error processing data: {e}")
        sys.exit(1)

def aggregate_small_slices(data_dict, threshold_percent, total_for_level, other_label="Other"):
    """
    Aggregate small slices into an "Other" category based on percentage threshold
    
    Args:
        data_dict: Dictionary of items to potentially aggregate
        threshold_percent: Minimum percentage threshold (0-100) for individual items
        total_for_level: Total count for the current level
        other_label: Label to use for aggregated small items
    
    Returns:
        Tuple of (aggregated_dict, other_items_list)
    """
    if threshold_percent <= 0:
        return data_dict, []
    
    threshold_count = (threshold_percent / 100.0) * total_for_level
    
    # Separate items above and below threshold
    main_items = {}
    small_items = {}
    other_total = 0
    
    for key, value in data_dict.items():
        item_count = calculate_total_recursive(value) if not isinstance(value, int) else value
        
        if item_count >= threshold_count:
            main_items[key] = value
        else:
            small_items[key] = value
            other_total += item_count
    
    # If we have small items to aggregate and it would be meaningful
    if small_items and len(small_items) > 1 and other_total > 0:
        # Add the "Other" category
        main_items[other_label] = other_total
        
        print(f"    Aggregated {len(small_items)} items < {threshold_percent}% into '{other_label}' ({other_total:,} total)")
        return main_items, list(small_items.keys())
    else:
        # Don't aggregate if only one small item or no small items
        return data_dict, []

def generate_distinct_colors(n_colors):
    """Generate highly distinct colors for better discrimination"""
    if n_colors <= 12:
        # Use hand-picked distinct colors for small sets
        base_colors = [
            '#BB8FCE', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
            '#98D8C8', '#FF6B6B', '#F7DC6F', '#85C1E9', '#F8C471', '#82E0AA'
        ]
        return [base_colors[i % len(base_colors)] for i in range(n_colors)]
    else:
        # Use multiple colormap cycles for larger sets
        colors = []
        colormaps = [plt.cm.Set1, plt.cm.Set2, plt.cm.Set3, plt.cm.Paired, plt.cm.Dark2]
        for i in range(n_colors):
            cmap = colormaps[i // 9 % len(colormaps)]
            colors.append(cmap((i % 9) / 9))
        return colors

def generate_color_variations(base_color, n_variations):
    """Generate variations of a base color by adjusting brightness"""
    if isinstance(base_color, str):
        # Convert hex to RGB
        if base_color.startswith('#'):
            r, g, b = int(base_color[1:3], 16)/255, int(base_color[3:5], 16)/255, int(base_color[5:7], 16)/255
        else:
            # Assume it's a named color
            r, g, b = mcolors.to_rgb(base_color)
    else:
        # Already RGB tuple
        r, g, b = base_color[:3]
    
    variations = []
    
    if n_variations == 1:
        return [base_color]
    
    # Generate variations by adjusting brightness
    for i in range(n_variations):
        # Create variations from 0.3 to 1.0 brightness multiplier
        factor = 0.3 + (0.7 * i / (n_variations - 1))
        new_r = min(1.0, r * factor + (1 - factor) * 0.9)  # Lighten for better contrast
        new_g = min(1.0, g * factor + (1 - factor) * 0.9)
        new_b = min(1.0, b * factor + (1 - factor) * 0.9)
        variations.append((new_r, new_g, new_b))
    
    return variations

def calculate_total_recursive(data):
    """Recursively calculate total from nested dictionary"""
    if isinstance(data, int):
        return data
    return sum(calculate_total_recursive(v) for v in data.values())

def create_sunburst_chart(hierarchy, total_samples, active_levels, output_file='sunburst_chart.png', 
                         title='Data Sunburst Analysis', figsize=(18, 18), auto_formats=True,
                         color_inherit_level=1, color_mode='variations', count_unique=False,
                         line_width=0.5, threshold_percent=0.0, other_label="Other", 
                         label_threshold=5.0):
    """
    Create a sunburst chart with hierarchical segments for up to 5 levels
    
    Args:
        line_width: Width of lines between segments (default: 0.5, original was 2)
        threshold_percent: Percentage threshold for aggregating small slices (0 = no aggregation)
        other_label: Label to use for aggregated small items
        label_threshold: Minimum angle in degrees for showing labels (default: 5.0)
        color_inherit_level: Level from which colors should be inherited (1-based indexing)
        color_mode: 'variations' = create color variations for deeper levels
                   'same' = use exact same colors for all levels
    """    
    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(aspect="equal"))
    
    n_levels = len(active_levels)
    
    # Define ring radii dynamically based on number of levels
    center_radius = 0.15
    ring_width = (0.85 - center_radius) / n_levels
    radii = [center_radius + i * ring_width for i in range(n_levels + 1)]
    
    print(f"Creating {n_levels} level sunburst with radii: {radii}")
    print(f"Color inheritance level: {color_inherit_level}")
    print(f"Color mode: {color_mode}")
    print(f"Line width: {line_width}")
    print(f"Small slice threshold: {threshold_percent}%")
    print(f"Label threshold: {label_threshold} degrees")
    
    # Apply small slice aggregation to level 1 if threshold is set
    processed_hierarchy = dict(hierarchy)
    aggregation_info = {}  # Track what was aggregated
    
    if threshold_percent > 0:
        print(f"Applying {threshold_percent}% threshold for small slice aggregation:")
        level1_totals = {k: calculate_total_recursive(v) for k, v in hierarchy.items()}
        total_for_level1 = sum(level1_totals.values())
        
        processed_hierarchy, aggregated_items = aggregate_small_slices(
            hierarchy, threshold_percent, total_for_level1, other_label
        )
        
        if aggregated_items:
            aggregation_info['level_1'] = aggregated_items
    
    # Calculate totals for level 1 and sort
    level1_totals = {k: calculate_total_recursive(v) for k, v in processed_hierarchy.items()}
    level1_sorted = sorted(level1_totals.items(), key=lambda x: x[1], reverse=True)
    
    # Generate distinct colors for level 1
    level1_colors = generate_distinct_colors(len(level1_sorted))
    base_color_map = {key: level1_colors[i] for i, (key, _) in enumerate(level1_sorted)}
    
    segments = []  # Store all segments for drawing
    
    def process_level(data_dict, level, parent_angle_start, parent_angle_size, parent_color, path=[]):
        """Recursively process each level of the hierarchy"""
        if level >= n_levels:
            return
        
        # Apply small slice aggregation if enabled and we're not at the top level or processing aggregated data
        processed_data = data_dict
        if threshold_percent > 0 and level > 0 and other_label not in str(path):
            # Calculate total for this level
            if isinstance(list(data_dict.values())[0], int):
                total_for_level = sum(data_dict.values())
            else:
                total_for_level = sum(calculate_total_recursive(v) for v in data_dict.values())
            
            processed_data, aggregated_items = aggregate_small_slices(
                data_dict, threshold_percent, total_for_level, other_label
            )
            
            if aggregated_items:
                level_key = f"level_{level + 1}"
                if level_key not in aggregation_info:
                    aggregation_info[level_key] = []
                aggregation_info[level_key].extend([f"{'/'.join(path)}/{item}" for item in aggregated_items])
        
        # Sort items by size
        if isinstance(list(processed_data.values())[0], int):
            # Final level - values are integers
            items_sorted = sorted(processed_data.items(), key=lambda x: x[1], reverse=True)
            total_for_level = sum(processed_data.values())
        else:
            # Intermediate level - values are dictionaries
            items_sorted = sorted(processed_data.items(), key=lambda x: calculate_total_recursive(x[1]), reverse=True)
            total_for_level = sum(calculate_total_recursive(v) for v in processed_data.values())
        
        current_angle = parent_angle_start
        
        # Determine color scheme based on inheritance level and mode
        level_colors = []
        
        if level + 1 <= color_inherit_level:
            # Before or at inheritance level - use distinct colors
            if level == 0:
                # Level 1 uses predefined distinct colors
                level_colors = [base_color_map.get(key, '#CCCCCC') for key, _ in items_sorted]
            else:
                # Generate distinct colors for this level
                level_colors = generate_distinct_colors(len(items_sorted))
        else:
            # After inheritance level - inherit from parent
            if color_mode == 'same':
                # Use exact same color as parent
                level_colors = [parent_color] * len(items_sorted)
            else:  # color_mode == 'variations'
                # Generate variations of the parent color
                level_colors = generate_color_variations(parent_color, len(items_sorted))
        
        for i, (key, value) in enumerate(items_sorted):
            if isinstance(value, int):
                item_total = value
            else:
                item_total = calculate_total_recursive(value)
                
            # Calculate angle for this segment
            angle_size = (item_total / total_for_level) * parent_angle_size
            
            # Use assigned color
            segment_color = level_colors[i]
            
            segments.append({
                'level': level + 1,
                'start_angle': current_angle,
                'end_angle': current_angle + angle_size,
                'inner_radius': radii[level],
                'outer_radius': radii[level + 1],
                'color': segment_color,
                'label': f"{key}\n{item_total:,}",
                'key': key,
                'value': item_total,
                'path': path + [key]
            })
            
            # Recursively process next level if it exists
            if not isinstance(value, int) and level + 1 < n_levels:
                process_level(value, level + 1, current_angle, angle_size, segment_color, path + [key])
            
            current_angle += angle_size
    
    # Start processing from level 1
    process_level(processed_hierarchy, 0, 0, 360, None, [])
    
    # Draw all segments
    for segment in segments:
        # Create wedge with customizable line width
        wedge = mpatches.Wedge(
            (0, 0), segment['outer_radius'],
            segment['start_angle'], segment['end_angle'],
            width=segment['outer_radius'] - segment['inner_radius'],
            facecolor=segment['color'],
            edgecolor='white',
            linewidth=line_width  # Now customizable
        )
        ax.add_patch(wedge)
        
        # Calculate if we should show label based on angle size threshold
        angle_size = segment['end_angle'] - segment['start_angle']
        show_label = angle_size > label_threshold  # Apply consistent threshold to all levels
            
        if show_label:
            # Calculate label position
            mid_angle = (segment['start_angle'] + segment['end_angle']) / 2
            mid_radius = (segment['inner_radius'] + segment['outer_radius']) / 2
            
            # Convert to radians
            angle_rad = np.radians(mid_angle)
            x = mid_radius * np.cos(angle_rad)
            y = mid_radius * np.sin(angle_rad)
            
            # Improved text rotation - always radial outward
            rotation = mid_angle
            # Adjust for readability - text should read outward from center
            if mid_angle > 90 and mid_angle <= 270:
                rotation = mid_angle + 180  # Flip text in bottom half
            
            # Font size based on level and segment size
            base_fontsize = max(6, min(12, 14 - segment['level']))
            if angle_size < 10:
                fontsize = max(6, base_fontsize - 2)
            else:
                fontsize = base_fontsize
                
            fontweight = 'bold' if segment['level'] <= 2 else 'normal'
            
            # Always use black text as requested
            text_color = 'black'
            
            # Add text
            text = ax.text(x, y, segment['label'], 
                          horizontalalignment='center', verticalalignment='center',
                          fontsize=fontsize, weight=fontweight, rotation=rotation,
                          color=text_color)
    
    # Add center circle with total
    center_circle = plt.Circle((0, 0), center_radius, fc='white', ec='black', linewidth=3)
    ax.add_patch(center_circle)
    
    count_label = 'Unique\nValues' if count_unique else 'Total\nSamples'
    ax.text(0, 0, f'{count_label}\n{total_samples:,}', 
            horizontalalignment='center', verticalalignment='center',
            fontsize=14, weight='bold', color='black')
    
    # Set equal aspect ratio and remove axes
    max_radius = radii[-1]
    ax.set_xlim(-max_radius * 1.1, max_radius * 1.1)
    ax.set_ylim(-max_radius * 1.1, max_radius * 1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Set title
    plt.title(title, fontsize=18, weight='bold', pad=20, color='black')    
    # Save the figure in specified format(s)
    plt.tight_layout()
    
    # Determine output format from file extension
    file_ext = output_file.lower().split('.')[-1]
    
    # Set appropriate DPI and format parameters
    save_params = {
        'bbox_inches': 'tight',
        'facecolor': 'white'
    }
    
    if file_ext in ['png', 'jpg', 'jpeg', 'tiff', 'tif']:
        save_params['dpi'] = 300
    elif file_ext in ['svg', 'pdf', 'eps']:
        # Vector formats don't need DPI but benefit from other settings
        save_params['dpi'] = 300  # Still good for any embedded raster elements
        if file_ext == 'svg':
            save_params['format'] = 'svg'
        elif file_ext == 'eps':
            save_params['format'] = 'eps'
    
    plt.savefig(output_file, **save_params)
    print(f"Sunburst chart saved as {output_file} ({file_ext.upper()} format)")
    
    # Also save in additional formats if specified
    if auto_formats:
        base_name = '.'.join(output_file.split('.')[:-1])
        
        # Automatically save SVG version for editing (unless already SVG)
        if file_ext != 'svg':
            svg_file = f"{base_name}.svg"
            plt.savefig(svg_file, format='svg', bbox_inches='tight', facecolor='white')
            print(f"Also saved editable SVG version: {svg_file}")
        
        # Automatically save PDF version for high-quality printing (unless already PDF)
        if file_ext != 'pdf':
            pdf_file = f"{base_name}.pdf"
            plt.savefig(pdf_file, format='pdf', bbox_inches='tight', facecolor='white')
            print(f"Also saved PDF version: {pdf_file}")
    
    # Display summary statistics
    print(f"\nSummary Statistics:")
    count_type = "unique values" if count_unique else "samples"
    print(f"Total {count_type}: {total_samples:,}")
    print(f"Number of levels: {n_levels}")
    print(f"Color inheritance from level: {color_inherit_level}")
    print(f"Color mode: {color_mode}")
    print(f"Line width: {line_width}")
    print(f"Label threshold: {label_threshold} degrees")
    
    # Report aggregation results
    if aggregation_info:
        print(f"\nSmall slice aggregation (threshold: {threshold_percent}%):")
        for level_key, items in aggregation_info.items():
            level_num = level_key.split('_')[1]
            print(f"  Level {level_num}: {len(items)} items aggregated into '{other_label}'")
            for item in items[:5]:  # Show first 5 items
                print(f"    - {item}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
    
    for i, level_name in enumerate(active_levels):
        level_segments = [s for s in segments if s['level'] == i + 1]
        print(f"Level {i+1} ({level_name}): {len(level_segments)} categories")
    
    for key, total in level1_sorted:
        percentage = (total / total_samples) * 100
        print(f"  {key}: {total:,} {count_type} ({percentage:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Generate sunburst chart from CSV data (up to 5 levels)')
    parser.add_argument('csv_file', help='Path to input CSV file')
    parser.add_argument('--sample-id', default='Sample-ID', help='Column name for sample IDs (default: Sample-ID)')
    parser.add_argument('--level1', default='Partner_sub', help='Column for level 1 (default: Partner_sub)')
    parser.add_argument('--level2', default='partner', help='Column for level 2 (default: partner)')
    parser.add_argument('--level3', default='Project-Code', help='Column for level 3 (default: Project-Code)')
    parser.add_argument('--level4', default=None, help='Column for level 4 (optional)')
    parser.add_argument('--level5', default=None, help='Column for level 5 (optional)')
    parser.add_argument('--color-inherit-level', type=int, default=1, 
                       help='Level from which colors should be inherited (1-5). ' +
                            'Level 1: each top-level category and descendants get unique colors. ' +
                            'Level 2: levels 1-2 get unique colors, level 3+ inherit from level 2, etc. (default: 1)')
    parser.add_argument('--color-mode', choices=['variations', 'same'], default='variations',
                       help='Color inheritance mode: "variations" creates color shades for deeper levels, ' +
                            '"same" uses identical colors for all inherited levels (default: variations)')
    parser.add_argument('--count-unique', action='store_true', 
                       help='Count unique values in sample-id column instead of all records (default: False)')
    parser.add_argument('--output', default='sunburst_chart.png', 
                       help='Output filename with extension (default: sunburst_chart.png)\n' +
                            'Supported formats: PNG, JPG, PDF, SVG, EPS, TIFF\n' +
                            'SVG and PDF are automatically generated for editing')
    parser.add_argument('--title', default='Data Sunburst Analysis', help='Chart title')
    parser.add_argument('--width', type=int, default=18, help='Figure width in inches (default: 18)')
    parser.add_argument('--height', type=int, default=18, help='Figure height in inches (default: 18)')
    parser.add_argument('--no-auto-formats', action='store_true', 
                       help='Skip automatic generation of SVG and PDF versions')
    
    # NEW ARGUMENTS for enhancements
    parser.add_argument('--line-width', type=float, default=0.5,
                       help='Width of lines between segments (default: 0.5, original was 2.0)')
    parser.add_argument('--threshold', type=float, default=0.0,
                       help='Percentage threshold for aggregating small slices into "Other" group (0-100, default: 0 = no aggregation)')
    parser.add_argument('--other-label', default='Other',
                       help='Label to use for aggregated small items (default: "Other")')
    parser.add_argument('--label-threshold', type=float, default=5.0,
                       help='Minimum angle in degrees for showing segment labels (default: 5.0)')
    
    args = parser.parse_args()
    
    # Validate threshold
    if args.threshold < 0 or args.threshold > 100:
        print(f"Error: --threshold must be between 0 and 100 (got {args.threshold})")
        sys.exit(1)
    
    # Validate color inheritance level
    level_cols = [args.level1, args.level2, args.level3, args.level4, args.level5]
    active_levels = [col for col in level_cols if col and col.strip()]
    
    if args.color_inherit_level < 1 or args.color_inherit_level > len(active_levels):
        print(f"Error: --color-inherit-level must be between 1 and {len(active_levels)} (number of active levels)")
        sys.exit(1)
    
    # Load and process data
    hierarchy, total_samples, active_levels = load_and_process_data(
        args.csv_file, args.sample_id, level_cols, args.count_unique
    )
    
    # Create the chart
    create_sunburst_chart(
        hierarchy, total_samples, active_levels,
        output_file=args.output,
        title=args.title,
        figsize=(args.width, args.height),
        auto_formats=not args.no_auto_formats,
        color_inherit_level=args.color_inherit_level,
        color_mode=args.color_mode,
        count_unique=args.count_unique,
        line_width=args.line_width,
        threshold_percent=args.threshold,
        other_label=args.other_label,
        label_threshold=args.label_threshold
    )

if __name__ == "__main__":
    # Example usage if run directly
    if len(sys.argv) == 1:
        print("Enhanced Sunburst Chart Generator")
        print("=================================")
        print("\nBasic usage:")
        print("python enhanced_sunburst_chart_script.py bge_museum_data.csv")
        print("\nNew features:")
        print("python enhanced_sunburst_chart_script.py data.csv --line-width 0.2    # Thinner lines")
        print("python enhanced_sunburst_chart_script.py data.csv --threshold 5.0     # Group items < 5% into 'Other'")
        print("python enhanced_sunburst_chart_script.py data.csv --label-threshold 3.0  # Only show labels for segments > 3 degrees")
        print("python enhanced_sunburst_chart_script.py data.csv --threshold 10 --other-label 'Miscellaneous'")
        print("\nCombined usage:")
        print("python enhanced_sunburst_chart_script.py data.csv --line-width 0.3 --threshold 8.0")
        print("\nAll original features still supported:")
        print("python enhanced_sunburst_chart_script.py data.csv --output chart.svg")
        print("python enhanced_sunburst_chart_script.py data.csv --level4 Category4 --level5 Category5")
        print("python enhanced_sunburst_chart_script.py data.csv --color-inherit-level 2")
        print("python enhanced_sunburst_chart_script.py data.csv --count-unique")
        print("\nSupported formats: PNG, JPG, PDF, SVG, EPS, TIFF")
        print("Note: SVG and PDF versions are automatically created for editing")
        print("\nFor help: python enhanced_sunburst_chart_script.py --help")
    else:
        main()