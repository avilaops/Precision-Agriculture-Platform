"""
Precision Agriculture Platform - Data Ingestion Module
Handles reading, validation, and preprocessing of harvest data

Input formats supported:
- CSV with columns: latitude, longitude, yield (productivity)
- Shapefiles with point geometry and yield attribute
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Union, Dict, Optional, List
import numpy as np
from shapely.geometry import Point, Polygon, box
import warnings

warnings.filterwarnings('ignore')


class DataValidator:
    """Validates harvest data quality"""
    
    def __init__(self, min_points: int = 100, yield_range: tuple = (0, 200)):
        """
        Args:
            min_points: Minimum number of points required
            yield_range: Valid range for yield values (tons/ha)
        """
        self.min_points = min_points
        self.yield_min, self.yield_max = yield_range
    
    def validate(self, gdf: gpd.GeoDataFrame) -> Dict:
        """
        Validate geodataframe
        
        Returns:
            dict with validation results and stats
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        # Check minimum points
        n_points = len(gdf)
        results['stats']['n_points'] = n_points
        
        if n_points < self.min_points:
            results['errors'].append(f"Insufficient points: {n_points} (min: {self.min_points})")
            results['valid'] = False
        
        # Check yield column
        if 'yield' not in gdf.columns:
            results['errors'].append("Missing 'yield' column")
            results['valid'] = False
            return results
        
        # Yield statistics
        yield_data = gdf['yield'].dropna()
        results['stats']['yield_mean'] = float(yield_data.mean())
        results['stats']['yield_std'] = float(yield_data.std())
        results['stats']['yield_min'] = float(yield_data.min())
        results['stats']['yield_max'] = float(yield_data.max())
        results['stats']['yield_median'] = float(yield_data.median())
        
        # Check for NaN values
        n_nan = gdf['yield'].isna().sum()
        if n_nan > 0:
            results['warnings'].append(f"{n_nan} points with missing yield values")
            results['stats']['n_missing'] = int(n_nan)
        
        # Check yield range
        outliers_low = (gdf['yield'] < self.yield_min).sum()
        outliers_high = (gdf['yield'] > self.yield_max).sum()
        
        if outliers_low > 0:
            results['warnings'].append(f"{outliers_low} points below minimum yield ({self.yield_min})")
            results['stats']['outliers_low'] = int(outliers_low)
        
        if outliers_high > 0:
            results['warnings'].append(f"{outliers_high} points above maximum yield ({self.yield_max})")
            results['stats']['outliers_high'] = int(outliers_high)
        
        # Check coordinate validity
        bounds = gdf.total_bounds
        results['stats']['bounds'] = {
            'min_lon': float(bounds[0]),
            'min_lat': float(bounds[1]),
            'max_lon': float(bounds[2]),
            'max_lat': float(bounds[3])
        }
        
        # Check CRS
        if gdf.crs is None:
            results['warnings'].append("No CRS defined, assuming EPSG:4326")
        
        return results


class HarvestDataReader:
    """Reads harvest data from various formats"""
    
    @staticmethod
    def read_csv(filepath: Union[str, Path], 
                 lat_col: str = 'latitude',
                 lon_col: str = 'longitude',
                 yield_col: str = 'yield',
                 crs: str = 'EPSG:4326') -> gpd.GeoDataFrame:
        """
        Read harvest data from CSV
        
        Args:
            filepath: Path to CSV file
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            yield_col: Name of yield column
            crs: Coordinate reference system
            
        Returns:
            GeoDataFrame with point geometry
        """
        df = pd.read_csv(filepath)
        
        # Check required columns
        required = [lat_col, lon_col, yield_col]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        
        # Create geometry
        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
        
        # Standardize yield column name
        if yield_col != 'yield':
            gdf = gdf.rename(columns={yield_col: 'yield'})
        
        return gdf[['geometry', 'yield']]
    
    @staticmethod
    def read_shapefile(filepath: Union[str, Path],
                       yield_col: str = 'yield') -> gpd.GeoDataFrame:
        """
        Read harvest data from shapefile
        
        Args:
            filepath: Path to shapefile
            yield_col: Name of yield attribute
            
        Returns:
            GeoDataFrame
        """
        gdf = gpd.read_file(filepath)
        
        # Check yield column
        if yield_col not in gdf.columns:
            raise ValueError(f"Yield column '{yield_col}' not found")
        
        # Ensure point geometry
        if not all(gdf.geometry.geom_type == 'Point'):
            raise ValueError("Shapefile must contain point geometry")
        
        # Standardize yield column name
        if yield_col != 'yield':
            gdf = gdf.rename(columns={yield_col: 'yield'})
        
        return gdf[['geometry', 'yield']]
    
    @staticmethod
    def read_boundary(filepath: Union[str, Path]) -> gpd.GeoDataFrame:
        """
        Read field boundary shapefile
        
        Args:
            filepath: Path to boundary shapefile
            
        Returns:
            GeoDataFrame with polygon geometry
        """
        gdf = gpd.read_file(filepath)
        
        # Ensure polygon geometry
        if not all(gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])):
            raise ValueError("Boundary must contain polygon geometry")
        
        return gdf


def ingest_harvest_data(data_file: Union[str, Path],
                        boundary_file: Optional[Union[str, Path]] = None,
                        file_type: str = 'auto',
                        validate: bool = True,
                        clean_outliers: bool = True) -> tuple:
    """
    Main ingestion function - reads and validates harvest data
    
    Args:
        data_file: Path to harvest data (CSV or shapefile)
        boundary_file: Optional path to field boundary shapefile
        file_type: 'csv', 'shapefile', or 'auto' (detect from extension)
        validate: Run validation checks
        clean_outliers: Remove outliers during cleaning
        
    Returns:
        tuple: (harvest_gdf, boundary_gdf, validation_results)
    """
    data_path = Path(data_file)
    
    # Auto-detect file type
    if file_type == 'auto':
        ext = data_path.suffix.lower()
        if ext == '.csv':
            file_type = 'csv'
        elif ext == '.shp':
            file_type = 'shapefile'
        else:
            raise ValueError(f"Unknown file extension: {ext}. Specify file_type explicitly.")
    
    # Read data
    print(f"📂 Reading {file_type} file: {data_path.name}")
    
    if file_type == 'csv':
        harvest_gdf = HarvestDataReader.read_csv(data_path)
    elif file_type == 'shapefile':
        harvest_gdf = HarvestDataReader.read_shapefile(data_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    
    print(f"   ✅ Loaded {len(harvest_gdf)} points")
    
    # Read boundary if provided
    boundary_gdf = None
    if boundary_file:
        boundary_path = Path(boundary_file)
        print(f"📂 Reading boundary: {boundary_path.name}")
        boundary_gdf = HarvestDataReader.read_boundary(boundary_path)
        
        # Clip points to boundary
        harvest_gdf = gpd.sjoin(harvest_gdf, boundary_gdf, predicate='within', how='inner')
        harvest_gdf = harvest_gdf[['geometry', 'yield']]
        print(f"   ✅ {len(harvest_gdf)} points within boundary")
    
    # Validate
    validation_results = None
    if validate:
        print(f"🔍 Validating data quality...")
        validator = DataValidator()
        validation_results = validator.validate(harvest_gdf)
        
        if validation_results['valid']:
            print(f"   ✅ Validation passed")
        else:
            print(f"   ❌ Validation failed:")
            for error in validation_results['errors']:
                print(f"      - {error}")
        
        if validation_results['warnings']:
            print(f"   ⚠️  Warnings:")
            for warning in validation_results['warnings']:
                print(f"      - {warning}")
        
        # Print statistics
        stats = validation_results['stats']
        print(f"\n📊 Data Statistics:")
        print(f"   Points: {stats['n_points']}")
        print(f"   Yield: {stats['yield_mean']:.1f} ± {stats['yield_std']:.1f} ton/ha")
        print(f"   Range: {stats['yield_min']:.1f} - {stats['yield_max']:.1f} ton/ha")
        print(f"   Median: {stats['yield_median']:.1f} ton/ha")
    
    # Clean outliers
    if clean_outliers:
        print(f"\n🧹 Cleaning outliers...")
        initial_count = len(harvest_gdf)
        
        # Remove extreme outliers (IQR method)
        Q1 = harvest_gdf['yield'].quantile(0.25)
        Q3 = harvest_gdf['yield'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        harvest_gdf = harvest_gdf[
            (harvest_gdf['yield'] >= lower_bound) & 
            (harvest_gdf['yield'] <= upper_bound)
        ]
        
        removed = initial_count - len(harvest_gdf)
        if removed > 0:
            print(f"   ✅ Removed {removed} outliers ({removed/initial_count*100:.1f}%)")
        else:
            print(f"   ✅ No outliers found")
    
    return harvest_gdf, boundary_gdf, validation_results


if __name__ == "__main__":
    # Example usage
    print("Precision Agriculture Platform - Data Ingestion")
    print("=" * 50)
    print()
    print("Usage:")
    print("  from src.ingest import ingest_harvest_data")
    print()
    print("  harvest_gdf, boundary_gdf, validation = ingest_harvest_data(")
    print("      data_file='data/harvest_2024.csv',")
    print("      boundary_file='data/field_boundary.shp'")
    print("  )")
