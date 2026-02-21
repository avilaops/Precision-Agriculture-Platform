"""
Precision Agriculture Platform - Decision Layer MVP
Spatial data processing for variable rate management

Modules:
- ingest: Data ingestion and validation
- zones: Management zone delineation
- report: Interactive HTML report generation
"""

__version__ = "0.1.0"
__author__ = "CanaSwarm Ecosystem"

from .ingest import ingest_harvest_data, DataValidator, HarvestDataReader
from .zones import delineate_management_zones, IDWInterpolator, ZoneDelineator
from .report import generate_report, ReportGenerator, MapGenerator

__all__ = [
    # Ingest
    'ingest_harvest_data',
    'DataValidator',
    'HarvestDataReader',
    
    # Zones
    'delineate_management_zones',
    'IDWInterpolator',
    'ZoneDelineator',
    
    # Report
    'generate_report',
    'ReportGenerator',
    'MapGenerator',
]
