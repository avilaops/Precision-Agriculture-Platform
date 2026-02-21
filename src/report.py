"""
Precision Agriculture Platform - Report Generation
Creates interactive HTML reports with maps and statistics

Output includes:
- Interactive folium maps with harvest points and zones
- Statistical summaries and charts
- Export-ready format (HTML + embedded data)
"""

import folium
from folium import plugins
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from typing import Optional, Dict, List
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt


class MapGenerator:
    """Generate interactive folium maps"""
    
    @staticmethod
    def create_harvest_map(harvest_gdf: gpd.GeoDataFrame,
                          zones_gdf: Optional[gpd.GeoDataFrame] = None,
                          center: Optional[tuple] = None,
                          zoom: int = 14) -> folium.Map:
        """
        Create harvest data map with zones
        
        Args:
            harvest_gdf: GeoDataFrame with harvest points
            zones_gdf: Optional GeoDataFrame with zone polygons
            center: Map center (lat, lon) or None to auto-calculate
            zoom: Initial zoom level
            
        Returns:
            folium.Map object
        """
        # Ensure geographic CRS
        if not harvest_gdf.crs.is_geographic:
            harvest_gdf = harvest_gdf.to_crs('EPSG:4326')
        
        if zones_gdf is not None and not zones_gdf.crs.is_geographic:
            zones_gdf = zones_gdf.to_crs('EPSG:4326')
        
        # Calculate center
        if center is None:
            centroid = harvest_gdf.dissolve().centroid.iloc[0]
            center = (centroid.y, centroid.x)
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles='OpenStreetMap'
        )
        
        # Add satellite layer
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        # Add zone polygons
        if zones_gdf is not None:
            # Color palette
            colors = ['#d73027', '#fc8d59', '#fee08b', '#d9ef8b', '#91cf60', '#1a9850']
            
            for idx, row in zones_gdf.iterrows():
                zone_id = row['zone_id']
                color = colors[zone_id % len(colors)]
                
                folium.GeoJson(
                    row['geometry'],
                    name=row['zone_name'],
                    style_function=lambda x, c=color: {
                        'fillColor': c,
                        'color': c,
                        'weight': 2,
                        'fillOpacity': 0.3
                    },
                    tooltip=folium.Tooltip(
                        f"<b>{row['zone_name']}</b><br>"
                        f"Yield: {row['yield_mean']:.1f} ± {row['yield_std']:.1f} ton/ha<br>"
                        f"Points: {row['n_points']}<br>"
                        f"Area: {row['area_ha']:.1f} ha"
                    )
                ).add_to(m)
        
        # Add harvest points with heatmap
        heat_data = [[point.y, point.x, val] for point, val in 
                     zip(harvest_gdf.geometry, harvest_gdf['yield'])]
        
        plugins.HeatMap(
            heat_data,
            name='Yield Heatmap',
            min_opacity=0.3,
            radius=15,
            blur=20,
            gradient={
                0.0: 'blue',
                0.5: 'yellow',
                1.0: 'red'
            }
        ).add_to(m)
        
        # Add point markers (sample for performance)
        sample_size = min(500, len(harvest_gdf))
        sample_indices = np.random.choice(len(harvest_gdf), sample_size, replace=False)
        
        marker_cluster = plugins.MarkerCluster(name='Sample Points')
        
        for idx in sample_indices:
            row = harvest_gdf.iloc[idx]
            point = row['geometry']
            yield_val = row['yield']
            
            folium.CircleMarker(
                location=[point.y, point.x],
                radius=3,
                popup=f"Yield: {yield_val:.2f} ton/ha",
                color='black',
                fillColor='yellow',
                fillOpacity=0.7,
                weight=1
            ).add_to(marker_cluster)
        
        marker_cluster.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add fullscreen button
        plugins.Fullscreen().add_to(m)
        
        return m
    
    @staticmethod
    def create_yield_histogram(yield_values: np.ndarray, 
                               zones_gdf: Optional[gpd.GeoDataFrame] = None) -> str:
        """
        Create yield distribution histogram
        
        Returns:
            Base64 encoded PNG image
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Overall histogram
        ax.hist(yield_values, bins=30, alpha=0.5, color='steelblue', 
               edgecolor='black', label='All Points')
        
        # Zone histograms
        if zones_gdf is not None:
            colors = ['#d73027', '#fc8d59', '#fee08b', '#91cf60', '#1a9850']
            for idx, row in zones_gdf.iterrows():
                zone_id = row['zone_id']
                # Note: This is simplified - in real implementation would filter by zone
                ax.axvline(row['yield_mean'], color=colors[zone_id % len(colors)],
                          linestyle='--', linewidth=2, 
                          label=f"{row['zone_name']} mean")
        
        ax.set_xlabel('Yield (ton/ha)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Yield Distribution', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return img_base64


class ReportGenerator:
    """Generate HTML reports"""
    
    def __init__(self):
        self.template = self._get_template()
    
    def _get_template(self) -> str:
        """HTML report template"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Precision Agriculture Report - {{REPORT_DATE}}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c5f2d;
            border-bottom: 3px solid #97bc62;
            padding-bottom: 10px;
        }
        h2 {
            color: #2c5f2d;
            margin-top: 30px;
            border-left: 4px solid #97bc62;
            padding-left: 10px;
        }
        .metadata {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .metadata p {
            margin: 5px 0;
            color: #555;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }
        .stat-card .unit {
            font-size: 14px;
            opacity: 0.8;
        }
        .zone-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .zone-table th {
            background: #2c5f2d;
            color: white;
            padding: 12px;
            text-align: left;
        }
        .zone-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        .zone-table tr:hover {
            background: #f5f5f5;
        }
        .map-container {
            margin: 20px 0;
            border: 2px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .chart-container {
            text-align: center;
            margin: 20px 0;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            text-align: center;
            color: #888;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌾 Precision Agriculture Report</h1>
        
        <div class="metadata">
            <p><strong>Generated:</strong> {{REPORT_DATE}}</p>
            <p><strong>Field:</strong> {{FIELD_NAME}}</p>
            <p><strong>Data Points:</strong> {{N_POINTS}}</p>
            <p><strong>Management Zones:</strong> {{N_ZONES}}</p>
        </div>
        
        <h2>📊 Summary Statistics</h2>
        <div class="stats-grid">
            {{STATS_CARDS}}
        </div>
        
        <h2>🗺️ Interactive Map</h2>
        <div class="map-container">
            {{MAP_HTML}}
        </div>
        
        <h2>📈 Yield Distribution</h2>
        <div class="chart-container">
            <img src="data:image/png;base64,{{HISTOGRAM_BASE64}}" alt="Yield Histogram">
        </div>
        
        <h2>🎯 Management Zones</h2>
        <table class="zone-table">
            <thead>
                <tr>
                    <th>Zone</th>
                    <th>Points</th>
                    <th>Yield Mean (ton/ha)</th>
                    <th>Yield Std (ton/ha)</th>
                    <th>Area (ha)</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {{ZONE_ROWS}}
            </tbody>
        </table>
        
        <div class="footer">
            <p>Generated by Precision Agriculture Platform</p>
            <p>CanaSwarm Ecosystem - Decision Layer MVP</p>
        </div>
    </div>
</body>
</html>
        """
    
    def generate(self, 
                 harvest_gdf: gpd.GeoDataFrame,
                 zones_gdf: Optional[gpd.GeoDataFrame] = None,
                 field_name: str = "Unnamed Field",
                 output_file: Optional[Path] = None) -> str:
        """
        Generate complete HTML report
        
        Args:
            harvest_gdf: Harvest point data
            zones_gdf: Management zones
            field_name: Field identifier
            output_file: Output path (if None, returns HTML string)
            
        Returns:
            HTML string
        """
        print(f"\n📄 Generating Report...")
        
        # Generate map
        print(f"   🗺️  Creating interactive map...")
        map_obj = MapGenerator.create_harvest_map(harvest_gdf, zones_gdf)
        map_html = map_obj._repr_html_()
        
        # Generate histogram
        print(f"   📊 Creating yield histogram...")
        histogram_base64 = MapGenerator.create_yield_histogram(
            harvest_gdf['yield'].values, zones_gdf
        )
        
        # Calculate statistics
        yield_values = harvest_gdf['yield'].values
        stats = {
            'n_points': len(harvest_gdf),
            'yield_mean': float(yield_values.mean()),
            'yield_median': float(np.median(yield_values)),
            'yield_std': float(yield_values.std()),
            'yield_min': float(yield_values.min()),
            'yield_max': float(yield_values.max()),
            'n_zones': len(zones_gdf) if zones_gdf is not None else 0
        }
        
        # Build stats cards
        stats_cards_html = f"""
            <div class="stat-card">
                <h3>Mean Yield</h3>
                <p class="value">{stats['yield_mean']:.1f}</p>
                <p class="unit">ton/ha</p>
            </div>
            <div class="stat-card">
                <h3>Median Yield</h3>
                <p class="value">{stats['yield_median']:.1f}</p>
                <p class="unit">ton/ha</p>
            </div>
            <div class="stat-card">
                <h3>Std Deviation</h3>
                <p class="value">{stats['yield_std']:.2f}</p>
                <p class="unit">ton/ha</p>
            </div>
            <div class="stat-card">
                <h3>Range</h3>
                <p class="value">{stats['yield_min']:.1f} - {stats['yield_max']:.1f}</p>
                <p class="unit">ton/ha</p>
            </div>
        """
        
        # Build zone table
        zone_rows_html = ""
        if zones_gdf is not None:
            for _, row in zones_gdf.iterrows():
                yield_mean = row['yield_mean']
                
                # Simple recommendation logic
                if yield_mean < stats['yield_mean'] - 0.5 * stats['yield_std']:
                    recommendation = "🔴 Increase inputs"
                elif yield_mean > stats['yield_mean'] + 0.5 * stats['yield_std']:
                    recommendation = "🟢 Maintain/reduce inputs"
                else:
                    recommendation = "🟡 Standard management"
                
                zone_rows_html += f"""
                    <tr>
                        <td><strong>{row['zone_name']}</strong></td>
                        <td>{row['n_points']}</td>
                        <td>{row['yield_mean']:.2f}</td>
                        <td>{row['yield_std']:.2f}</td>
                        <td>{row['area_ha']:.1f}</td>
                        <td>{recommendation}</td>
                    </tr>
                """
        else:
            zone_rows_html = "<tr><td colspan='6' style='text-align:center;'>No zones defined</td></tr>"
        
        # Fill template
        html = self.template
        html = html.replace('{{REPORT_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        html = html.replace('{{FIELD_NAME}}', field_name)
        html = html.replace('{{N_POINTS}}', str(stats['n_points']))
        html = html.replace('{{N_ZONES}}', str(stats['n_zones']))
        html = html.replace('{{STATS_CARDS}}', stats_cards_html)
        html = html.replace('{{MAP_HTML}}', map_html)
        html = html.replace('{{HISTOGRAM_BASE64}}', histogram_base64)
        html = html.replace('{{ZONE_ROWS}}', zone_rows_html)
        
        # Save to file
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding='utf-8')
            print(f"   ✅ Report saved: {output_path}")
        
        return html


def generate_report(harvest_gdf: gpd.GeoDataFrame,
                   zones_gdf: Optional[gpd.GeoDataFrame] = None,
                   field_name: str = "Unnamed Field",
                   output_file: Optional[str] = None) -> str:
    """
    Generate precision agriculture report
    
    Args:
        harvest_gdf: Harvest data
        zones_gdf: Management zones
        field_name: Field name
        output_file: Output HTML file path
        
    Returns:
        HTML string
    """
    generator = ReportGenerator()
    return generator.generate(harvest_gdf, zones_gdf, field_name, output_file)


if __name__ == "__main__":
    print("Precision Agriculture Platform - Report Generation")
    print("=" * 50)
    print()
    print("Usage:")
    print("  from src.report import generate_report")
    print()
    print("  html = generate_report(")
    print("      harvest_gdf,")
    print("      zones_gdf,")
    print("      field_name='Field A',")
    print("      output_file='output/report.html'")
    print("  )")
