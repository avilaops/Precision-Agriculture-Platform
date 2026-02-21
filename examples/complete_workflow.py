"""
Example: Complete precision agriculture workflow
Generates synthetic harvest data and runs full analysis pipeline
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import ingest_harvest_data
from src.zones import delineate_management_zones
from src.report import generate_report


def generate_synthetic_harvest_data(n_points: int = 1000, 
                                    seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic harvest data with spatial patterns
    
    Args:
        n_points: Number of GPS points to generate
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with latitude, longitude, yield
    """
    np.random.seed(seed)
    
    # Define field bounds (example: sugarcane field in Brazil)
    center_lat, center_lon = -20.5, -49.5
    field_size = 0.01  # ~1 km
    
    # Generate points in a rectangular field
    lats = np.random.uniform(
        center_lat - field_size/2, 
        center_lat + field_size/2, 
        n_points
    )
    lons = np.random.uniform(
        center_lon - field_size/2, 
        center_lon + field_size/2, 
        n_points
    )
    
    # Create spatial yield pattern (simulate soil fertility gradient + noise)
    # Zone 1: Low productivity (northwest)
    zone1_factor = 1.0 - 0.5 * (
        (lats - center_lat + field_size/2) / field_size +
        (lons - center_lon + field_size/2) / field_size
    )
    
    # Zone 2: High productivity (southeast)
    zone2_factor = 0.5 * (
        (lats - center_lat + field_size/2) / field_size +
        (lons - center_lon + field_size/2) / field_size
    )
    
    # Base yield with spatial pattern
    base_yield = 70  # ton/ha
    yield_variation = 25  # ton/ha
    
    yields = base_yield + yield_variation * (zone1_factor + zone2_factor)
    
    # Add random noise
    yields += np.random.normal(0, 5, n_points)
    
    # Add some localized hot spots (e.g., better water availability)
    hotspot_lat, hotspot_lon = center_lat + 0.002, center_lon - 0.002
    distance_to_hotspot = np.sqrt(
        (lats - hotspot_lat)**2 + (lons - hotspot_lon)**2
    )
    hotspot_bonus = 15 * np.exp(-distance_to_hotspot * 1000)
    yields += hotspot_bonus
    
    # Clip to realistic range
    yields = np.clip(yields, 40, 120)
    
    # Create DataFrame
    df = pd.DataFrame({
        'latitude': lats,
        'longitude': lons,
        'yield': yields
    })
    
    return df


def run_complete_example():
    """Run complete precision agriculture analysis"""
    
    print("=" * 70)
    print("PRECISION AGRICULTURE PLATFORM - COMPLETE EXAMPLE")
    print("=" * 70)
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Step 1: Generate synthetic data
    print("\n📊 STEP 1: Generate Synthetic Harvest Data")
    print("-" * 70)
    df = generate_synthetic_harvest_data(n_points=1500, seed=42)
    
    # Save to CSV
    csv_file = output_dir / "harvest_data_synthetic.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ Generated {len(df)} GPS points")
    print(f"✅ Saved to: {csv_file}")
    
    # Step 2: Ingest and validate data
    print("\n📥 STEP 2: Ingest and Validate Data")
    print("-" * 70)
    harvest_gdf, boundary_gdf, validation = ingest_harvest_data(
        data_file=csv_file,
        file_type='csv',
        validate=True,
        clean_outliers=True
    )
    
    if not validation['valid']:
        print("❌ Validation failed. Stopping.")
        return
    
    # Step 3: Delineate management zones
    print("\n🎯 STEP 3: Delineate Management Zones")
    print("-" * 70)
    zones_results = delineate_management_zones(
        harvest_gdf,
        n_zones=None,  # Auto-select optimal number
        resolution=10.0,
        idw_power=2.0
    )
    
    zones_gdf = zones_results['zones_gdf']
    
    # Save zones to shapefile
    zones_file = output_dir / "management_zones.shp"
    zones_gdf.to_file(zones_file)
    print(f"\n✅ Zones saved to: {zones_file}")
    
    # Step 4: Generate report
    print("\n📄 STEP 4: Generate Interactive Report")
    print("-" * 70)
    report_file = output_dir / "precision_agriculture_report.html"
    
    html = generate_report(
        harvest_gdf=harvest_gdf,
        zones_gdf=zones_gdf,
        field_name="Synthetic Field Demo",
        output_file=str(report_file)
    )
    
    print(f"\n✅ Report generated: {report_file}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE ✅")
    print("=" * 70)
    print(f"\n📁 Output files:")
    print(f"   - Harvest data: {csv_file}")
    print(f"   - Management zones: {zones_file}")
    print(f"   - Report: {report_file}")
    
    print(f"\n📊 Summary:")
    print(f"   - Points analyzed: {len(harvest_gdf)}")
    print(f"   - Management zones: {len(zones_gdf)}")
    print(f"   - Mean yield: {harvest_gdf['yield'].mean():.1f} ton/ha")
    print(f"   - Yield range: {harvest_gdf['yield'].min():.1f} - {harvest_gdf['yield'].max():.1f} ton/ha")
    
    print(f"\n🌐 Open the report in your browser:")
    print(f"   file:///{report_file.absolute()}")
    print()


if __name__ == "__main__":
    try:
        run_complete_example()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
