"""
Unit tests for data ingestion module
"""

import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point, Polygon
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import (
    DataValidator,
    HarvestDataReader,
    ingest_harvest_data
)


class TestDataValidator:
    """Test DataValidator class"""
    
    def test_validate_valid_data(self):
        """Test validation with valid data"""
        # Create sample data
        points = [Point(x, y) for x, y in zip(
            np.random.uniform(-50, -49, 200),
            np.random.uniform(-20, -19, 200)
        )]
        yields = np.random.uniform(50, 100, 200)
        
        gdf = gpd.GeoDataFrame({
            'yield': yields,
            'geometry': points
        }, crs='EPSG:4326')
        
        validator = DataValidator(min_points=100, yield_range=(0, 200))
        results = validator.validate(gdf)
        
        assert results['valid'] == True
        assert len(results['errors']) == 0
        assert results['stats']['n_points'] == 200
        assert 50 <= results['stats']['yield_mean'] <= 100
    
    def test_validate_insufficient_points(self):
        """Test validation with too few points"""
        points = [Point(0, 0), Point(1, 1)]
        yields = [50, 60]
        
        gdf = gpd.GeoDataFrame({
            'yield': yields,
            'geometry': points
        }, crs='EPSG:4326')
        
        validator = DataValidator(min_points=100)
        results = validator.validate(gdf)
        
        assert results['valid'] == False
        assert len(results['errors']) > 0
        assert 'Insufficient points' in results['errors'][0]
    
    def test_validate_missing_yield_column(self):
        """Test validation with missing yield column"""
        points = [Point(0, 0), Point(1, 1)]
        
        gdf = gpd.GeoDataFrame({
            'geometry': points
        }, crs='EPSG:4326')
        
        validator = DataValidator()
        results = validator.validate(gdf)
        
        assert results['valid'] == False
        assert "Missing 'yield' column" in results['errors'][0]
    
    def test_validate_with_outliers(self):
        """Test validation detects outliers"""
        points = [Point(x, y) for x, y in zip(
            np.random.uniform(-50, -49, 150),
            np.random.uniform(-20, -19, 150)
        )]
        yields = np.append(np.random.uniform(50, 100, 148), [500, 600])  # Add outliers
        
        gdf = gpd.GeoDataFrame({
            'yield': yields,
            'geometry': points
        }, crs='EPSG:4326')
        
        validator = DataValidator(min_points=100, yield_range=(0, 200))
        results = validator.validate(gdf)
        
        assert results['valid'] == True
        assert len(results['warnings']) > 0
        assert 'outliers_high' in results['stats']


class TestHarvestDataReader:
    """Test HarvestDataReader class"""
    
    def test_read_csv_basic(self, tmp_path):
        """Test reading basic CSV file"""
        # Create sample CSV
        csv_file = tmp_path / "harvest.csv"
        df = pd.DataFrame({
            'latitude': [-20.0, -20.1, -20.2],
            'longitude': [-50.0, -50.1, -50.2],
            'yield': [80.5, 85.3, 78.9]
        })
        df.to_csv(csv_file, index=False)
        
        # Read CSV
        gdf = HarvestDataReader.read_csv(csv_file)
        
        assert len(gdf) == 3
        assert 'yield' in gdf.columns
        assert 'geometry' in gdf.columns
        assert gdf.crs.to_string() == 'EPSG:4326'
        assert all(gdf.geometry.geom_type == 'Point')
    
    def test_read_csv_custom_columns(self, tmp_path):
        """Test reading CSV with custom column names"""
        csv_file = tmp_path / "harvest_custom.csv"
        df = pd.DataFrame({
            'lat': [-20.0, -20.1],
            'lon': [-50.0, -50.1],
            'productivity': [80.5, 85.3]
        })
        df.to_csv(csv_file, index=False)
        
        gdf = HarvestDataReader.read_csv(
            csv_file,
            lat_col='lat',
            lon_col='lon',
            yield_col='productivity'
        )
        
        assert len(gdf) == 2
        assert 'yield' in gdf.columns  # Should be renamed
    
    def test_read_csv_missing_columns(self, tmp_path):
        """Test error on missing required columns"""
        csv_file = tmp_path / "incomplete.csv"
        df = pd.DataFrame({
            'latitude': [-20.0],
            'yield': [80.5]
            # Missing longitude
        })
        df.to_csv(csv_file, index=False)
        
        with pytest.raises(ValueError, match="Missing columns"):
            HarvestDataReader.read_csv(csv_file)


class TestIngestHarvestData:
    """Test main ingestion function"""
    
    def test_ingest_csv_basic(self, tmp_path):
        """Test complete ingestion workflow"""
        # Create sample CSV
        csv_file = tmp_path / "harvest.csv"
        n_points = 150
        df = pd.DataFrame({
            'latitude': np.random.uniform(-20, -19, n_points),
            'longitude': np.random.uniform(-50, -49, n_points),
            'yield': np.random.uniform(60, 100, n_points)
        })
        df.to_csv(csv_file, index=False)
        
        # Ingest
        harvest_gdf, boundary_gdf, validation = ingest_harvest_data(
            csv_file,
            file_type='csv',
            validate=True,
            clean_outliers=True
        )
        
        assert len(harvest_gdf) <= n_points  # May remove outliers
        assert validation is not None
        assert validation['valid'] == True
        assert harvest_gdf.crs.to_string() == 'EPSG:4326'
    
    def test_ingest_auto_detect_csv(self, tmp_path):
        """Test auto-detection of file type"""
        csv_file = tmp_path / "data.csv"
        df = pd.DataFrame({
            'latitude': [-20.0, -20.1],
            'longitude': [-50.0, -50.1],
            'yield': [80.0, 85.0]
        })
        df.to_csv(csv_file, index=False)
        
        harvest_gdf, _, _ = ingest_harvest_data(csv_file, file_type='auto')
        
        assert len(harvest_gdf) == 2
    
    def test_ingest_with_outlier_cleaning(self, tmp_path):
        """Test outlier removal"""
        csv_file = tmp_path / "with_outliers.csv"
        n_points = 200
        yields = np.append(
            np.random.uniform(60, 100, n_points - 5),
            [500, 600, 700, 0, 1]  # Extreme outliers
        )
        
        df = pd.DataFrame({
            'latitude': np.random.uniform(-20, -19, n_points),
            'longitude': np.random.uniform(-50, -49, n_points),
            'yield': yields
        })
        df.to_csv(csv_file, index=False)
        
        harvest_gdf, _, _ = ingest_harvest_data(
            csv_file,
            clean_outliers=True
        )
        
        # Should remove extreme outliers
        assert len(harvest_gdf) < n_points
        assert harvest_gdf['yield'].min() > 10
        assert harvest_gdf['yield'].max() < 400


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])
