"""
Precision Agriculture Platform - Management Zone Delineation
IDW interpolation and zone clustering for variable rate management

Algorithms:
- Inverse Distance Weighting (IDW) for spatial interpolation
- K-Means clustering for zone delineation
- Silhouette analysis for optimal cluster count
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
from scipy.interpolate import griddata
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from shapely.geometry import Point, Polygon
from typing import Optional, Tuple, List
import warnings

warnings.filterwarnings('ignore')


class IDWInterpolator:
    """Inverse Distance Weighting interpolation"""
    
    def __init__(self, power: float = 2.0, max_neighbors: int = 12):
        """
        Args:
            power: IDW power parameter (higher = more local influence)
            max_neighbors: Maximum number of neighbors for interpolation
        """
        self.power = power
        self.max_neighbors = max_neighbors
        self.tree = None
        self.values = None
    
    def fit(self, points: np.ndarray, values: np.ndarray):
        """
        Fit interpolator to point data
        
        Args:
            points: Array of (x, y) coordinates, shape (n, 2)
            values: Array of values, shape (n,)
        """
        self.tree = cKDTree(points)
        self.values = values
    
    def predict(self, grid_points: np.ndarray) -> np.ndarray:
        """
        Interpolate values at grid points
        
        Args:
            grid_points: Array of (x, y) coordinates, shape (m, 2)
            
        Returns:
            Interpolated values, shape (m,)
        """
        if self.tree is None:
            raise ValueError("Interpolator not fitted. Call fit() first.")
        
        # Query nearest neighbors
        distances, indices = self.tree.query(
            grid_points, 
            k=min(self.max_neighbors, len(self.values))
        )
        
        # Handle single point case
        if distances.ndim == 1:
            distances = distances.reshape(1, -1)
            indices = indices.reshape(1, -1)
        
        # Calculate IDW weights
        # Avoid division by zero for exact matches
        distances = np.maximum(distances, 1e-10)
        weights = 1.0 / np.power(distances, self.power)
        
        # Normalize weights
        weights = weights / weights.sum(axis=1, keepdims=True)
        
        # Weighted average
        interpolated = (weights * self.values[indices]).sum(axis=1)
        
        return interpolated
    
    def interpolate_grid(self, bounds: Tuple[float, float, float, float],
                        resolution: float = 10.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create interpolated grid
        
        Args:
            bounds: (min_x, min_y, max_x, max_y)
            resolution: Grid cell size in meters
            
        Returns:
            tuple: (grid_x, grid_y, grid_values)
        """
        min_x, min_y, max_x, max_y = bounds
        
        # Create grid
        x = np.arange(min_x, max_x, resolution)
        y = np.arange(min_y, max_y, resolution)
        grid_x, grid_y = np.meshgrid(x, y)
        
        # Interpolate
        grid_points = np.c_[grid_x.ravel(), grid_y.ravel()]
        grid_values = self.predict(grid_points)
        grid_values = grid_values.reshape(grid_x.shape)
        
        return grid_x, grid_y, grid_values


class ZoneDelineator:
    """Management zone delineation using clustering"""
    
    def __init__(self, n_zones: Optional[int] = None, 
                 min_zones: int = 2, 
                 max_zones: int = 7):
        """
        Args:
            n_zones: Fixed number of zones (if None, auto-select)
            min_zones: Minimum zones for auto-selection
            max_zones: Maximum zones for auto-selection
        """
        self.n_zones = n_zones
        self.min_zones = min_zones
        self.max_zones = max_zones
        self.model = None
        self.scaler = StandardScaler()
        self.optimal_n_zones = None
    
    def _find_optimal_zones(self, X: np.ndarray) -> int:
        """
        Find optimal number of zones using silhouette analysis
        
        Args:
            X: Feature matrix
            
        Returns:
            Optimal number of zones
        """
        silhouette_scores = []
        zone_range = range(self.min_zones, self.max_zones + 1)
        
        for n in zone_range:
            kmeans = KMeans(n_clusters=n, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            score = silhouette_score(X, labels)
            silhouette_scores.append(score)
        
        # Select number with highest silhouette score
        optimal_idx = np.argmax(silhouette_scores)
        optimal_n = list(zone_range)[optimal_idx]
        
        print(f"   📊 Silhouette scores:")
        for n, score in zip(zone_range, silhouette_scores):
            marker = "➜" if n == optimal_n else " "
            print(f"   {marker} {n} zones: {score:.3f}")
        
        return optimal_n
    
    def fit_predict(self, yield_values: np.ndarray, 
                   features: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Delineate management zones
        
        Args:
            yield_values: Yield values, shape (n,)
            features: Optional additional features, shape (n, m)
            
        Returns:
            Zone labels, shape (n,)
        """
        # Prepare features
        if features is None:
            X = yield_values.reshape(-1, 1)
        else:
            X = np.c_[yield_values, features]
        
        # Standardize
        X_scaled = self.scaler.fit_transform(X)
        
        # Determine number of zones
        if self.n_zones is None:
            print(f"🔍 Finding optimal number of zones...")
            self.optimal_n_zones = self._find_optimal_zones(X_scaled)
            n_zones = self.optimal_n_zones
            print(f"   ✅ Selected {n_zones} zones")
        else:
            n_zones = self.n_zones
            self.optimal_n_zones = n_zones
        
        # Fit K-Means
        print(f"🎯 Clustering into {n_zones} management zones...")
        self.model = KMeans(n_clusters=n_zones, random_state=42, n_init=10)
        labels = self.model.fit_predict(X_scaled)
        
        # Sort zones by mean yield (low to high)
        zone_means = [yield_values[labels == i].mean() for i in range(n_zones)]
        zone_order = np.argsort(zone_means)
        
        # Remap labels
        label_map = {old: new for new, old in enumerate(zone_order)}
        labels = np.array([label_map[label] for label in labels])
        
        return labels


def delineate_management_zones(harvest_gdf: gpd.GeoDataFrame,
                               n_zones: Optional[int] = None,
                               resolution: float = 10.0,
                               idw_power: float = 2.0,
                               return_grid: bool = True) -> dict:
    """
    Complete management zone delineation workflow
    
    Args:
        harvest_gdf: GeoDataFrame with harvest points
        n_zones: Number of zones (None = auto-select)
        resolution: Interpolation grid resolution in meters
        idw_power: IDW power parameter
        return_grid: Include interpolated grid in results
        
    Returns:
        dict with zones_gdf, grid_data, statistics
    """
    print(f"\n🌾 Management Zone Delineation")
    print("=" * 50)
    
    # Reproject to projected CRS for accurate distances
    if harvest_gdf.crs.is_geographic:
        print(f"📐 Reprojecting to UTM...")
        # Estimate UTM zone from centroid
        centroid = harvest_gdf.dissolve().centroid.iloc[0]
        utm_zone = int((centroid.x + 180) / 6) + 1
        hemisphere = 'north' if centroid.y >= 0 else 'south'
        utm_crs = f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84 +units=m +no_defs"
        harvest_utm = harvest_gdf.to_crs(utm_crs)
    else:
        harvest_utm = harvest_gdf.copy()
    
    # Extract coordinates and values
    coords = np.array([[geom.x, geom.y] for geom in harvest_utm.geometry])
    values = harvest_utm['yield'].values
    
    print(f"📊 Input: {len(harvest_utm)} points")
    print(f"   Yield range: {values.min():.1f} - {values.max():.1f} ton/ha")
    
    # IDW interpolation
    print(f"\n🗺️  IDW Interpolation (power={idw_power}, resolution={resolution}m)...")
    interpolator = IDWInterpolator(power=idw_power, max_neighbors=12)
    interpolator.fit(coords, values)
    
    bounds = harvest_utm.total_bounds
    grid_x, grid_y, grid_z = interpolator.interpolate_grid(bounds, resolution)
    
    print(f"   ✅ Grid: {grid_x.shape[1]} × {grid_x.shape[0]} cells")
    
    # Zone delineation
    print(f"\n🎨 Zone Delineation...")
    delineator = ZoneDelineator(n_zones=n_zones)
    
    # Cluster on grid values
    grid_values_flat = grid_z.ravel()
    zone_labels = delineator.fit_predict(grid_values_flat)
    zone_grid = zone_labels.reshape(grid_z.shape)
    
    # Create zone polygons (simplified)
    print(f"\n🔷 Creating zone polygons...")
    zones_list = []
    
    for zone_id in range(delineator.optimal_n_zones):
        mask = zone_grid == zone_id
        zone_points = harvest_utm[values >= values.min()]  # Placeholder for actual spatial join
        
        # Calculate zone statistics from original points
        points_in_zone = harvest_utm[
            (coords[:, 0] >= bounds[0]) & 
            (coords[:, 0] <= bounds[2]) &
            (coords[:, 1] >= bounds[1]) & 
            (coords[:, 1] <= bounds[3])
        ]
        
        # Assign points to nearest zone
        grid_coords = np.c_[grid_x.ravel(), grid_y.ravel()]
        tree = cKDTree(grid_coords)
        _, nearest_grid = tree.query(coords, k=1)
        point_zones = zone_labels[nearest_grid]
        
        zone_points = harvest_utm[point_zones == zone_id]
        
        if len(zone_points) == 0:
            continue
        
        zone_yield_mean = zone_points['yield'].mean()
        zone_yield_std = zone_points['yield'].std()
        zone_area = len(zone_points) * resolution * resolution / 10000  # hectares
        
        zones_list.append({
            'zone_id': zone_id,
            'zone_name': f"Zone {zone_id + 1}",
            'n_points': len(zone_points),
            'yield_mean': zone_yield_mean,
            'yield_std': zone_yield_std,
            'area_ha': zone_area,
            'geometry': zone_points.dissolve().convex_hull.iloc[0]
        })
    
    zones_gdf = gpd.GeoDataFrame(zones_list, crs=harvest_utm.crs)
    
    # Reproject back to original CRS
    if harvest_gdf.crs != harvest_utm.crs:
        zones_gdf = zones_gdf.to_crs(harvest_gdf.crs)
    
    # Print statistics
    print(f"\n📈 Zone Statistics:")
    print(f"{'Zone':<8} {'Points':<8} {'Yield (ton/ha)':<20} {'Area (ha)':<10}")
    print("-" * 50)
    for _, row in zones_gdf.iterrows():
        print(f"Zone {row['zone_id']+1:<3} {row['n_points']:<8} "
              f"{row['yield_mean']:>6.1f} ± {row['yield_std']:>4.1f}      "
              f"{row['area_ha']:>6.1f}")
    
    # Prepare results
    results = {
        'zones_gdf': zones_gdf,
        'n_zones': delineator.optimal_n_zones,
        'statistics': zones_gdf[['zone_id', 'zone_name', 'n_points', 
                                 'yield_mean', 'yield_std', 'area_ha']].to_dict('records')
    }
    
    if return_grid:
        results['grid'] = {
            'x': grid_x,
            'y': grid_y,
            'z': grid_z,
            'zone_labels': zone_grid,
            'crs': str(harvest_utm.crs)
        }
    
    return results


if __name__ == "__main__":
    print("Precision Agriculture Platform - Management Zones")
    print("=" * 50)
    print()
    print("Usage:")
    print("  from src.zones import delineate_management_zones")
    print()
    print("  results = delineate_management_zones(")
    print("      harvest_gdf,")
    print("      n_zones=5,  # or None for auto-select")
    print("      resolution=10.0  # meters")
    print("  )")
    print()
    print("  zones_gdf = results['zones_gdf']")
    print("  grid_data = results['grid']")
