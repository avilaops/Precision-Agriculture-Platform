"""
Precision Agriculture Platform - REST API

Exposes field analysis and zone recommendations via HTTP endpoints.
"""

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Pydantic models for API contracts
class FinancialImpact(BaseModel):
    """Financial impact of zone status."""
    estimated_loss_brl_year: Optional[float] = Field(
        None,
        description="Estimated annual loss in BRL"
    )
    estimated_gain_brl_year: Optional[float] = Field(
        None,
        description="Estimated annual gain in BRL"
    )
    reform_cost_brl: Optional[float] = Field(
        None,
        description="Cost of field reform in BRL"
    )
    payback_months: Optional[int] = Field(
        None,
        description="Payback period in months"
    )


class ZoneRecommendation(BaseModel):
    """Agronomic recommendation for a management zone."""
    action: str = Field(..., description="Recommended action")
    priority: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Action priority level"
    )
    reason: str = Field(..., description="Reason for recommendation")


class ManagementZone(BaseModel):
    """Management zone with analysis and recommendations."""
    zone_id: str = Field(..., description="Zone identifier")
    area_ha: float = Field(..., ge=0, description="Zone area in hectares")
    avg_yield_t_ha: float = Field(..., ge=0, description="Average yield in t/ha")
    expected_yield_t_ha: float = Field(
        ...,
        ge=0,
        description="Expected yield in t/ha"
    )
    profitability_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Profitability score (0-10)"
    )
    status: Literal["optimal", "warning", "critical"] = Field(
        ...,
        description="Zone status"
    )
    recommendation: ZoneRecommendation = Field(
        ...,
        description="Agronomic recommendation"
    )
    financial_impact: FinancialImpact = Field(
        ...,
        description="Financial impact analysis"
    )


class FieldSummary(BaseModel):
    """Summary statistics for the field."""
    total_estimated_impact_brl: float = Field(
        ...,
        description="Total estimated financial impact in BRL/year"
    )
    avg_profitability_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Average profitability score (0-10)"
    )


class FieldRecommendations(BaseModel):
    """Complete field analysis with zone recommendations."""
    field_id: str = Field(..., description="Field identifier")
    crop: str = Field(..., description="Crop type")
    season: str = Field(..., description="Growing season")
    harvest_number: int = Field(..., ge=1, description="Harvest/cutting number")
    total_area_ha: float = Field(..., ge=0, description="Total field area in hectares")
    analysis_date: str = Field(..., description="Analysis date (ISO 8601)")
    summary: FieldSummary = Field(..., description="Field summary statistics")
    zones: List[ManagementZone] = Field(
        ...,
        description="Management zones with recommendations"
    )


# Initialize FastAPI app
app = FastAPI(
    title="Precision Agriculture Platform API",
    description="REST API for field analysis and zone-based recommendations",
    version="1.0.0",
    contact={
        "name": "AvilaOps",
        "url": "https://github.com/avilaops/Precision-Agriculture-Platform",
    },
)


# Mock data storage (in production, this would be a database)
MOCK_FIELDS = {
    "F001": {
        "field_id": "F001-UsinaGuarani-Piracicaba",
        "crop": "cana-de-açúcar",
        "season": "2025/26",
        "harvest_number": 3,
        "total_area_ha": 150.5,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_estimated_impact_brl": 234500.00,
            "avg_profitability_score": 7.2,
        },
        "zones": [
            {
                "zone_id": "Z001",
                "area_ha": 45.2,
                "avg_yield_t_ha": 65.3,
                "expected_yield_t_ha": 80.0,
                "profitability_score": 6.2,
                "status": "warning",
                "recommendation": {
                    "action": "reform",
                    "priority": "high",
                    "reason": "Yield 18% below expected, aging ratoon (3rd cut)",
                },
                "financial_impact": {
                    "estimated_loss_brl_year": 120000.00,
                    "reform_cost_brl": 15000.00,
                    "payback_months": 8,
                },
            },
            {
                "zone_id": "Z002",
                "area_ha": 58.8,
                "avg_yield_t_ha": 78.5,
                "expected_yield_t_ha": 80.0,
                "profitability_score": 8.5,
                "status": "optimal",
                "recommendation": {
                    "action": "maintain",
                    "priority": "low",
                    "reason": "Yield within expected range, healthy crop",
                },
                "financial_impact": {
                    "estimated_gain_brl_year": 85000.00,
                },
            },
            {
                "zone_id": "Z003",
                "area_ha": 46.5,
                "avg_yield_t_ha": 52.1,
                "expected_yield_t_ha": 80.0,
                "profitability_score": 4.8,
                "status": "critical",
                "recommendation": {
                    "action": "immediate_reform",
                    "priority": "critical",
                    "reason": "Yield 35% below expected, severe degradation",
                },
                "financial_impact": {
                    "estimated_loss_brl_year": 180000.00,
                    "reform_cost_brl": 18000.00,
                    "payback_months": 6,
                },
            },
        ],
    },
    "F002": {
        "field_id": "F002-UsinaSantaClara-Araraquara",
        "crop": "cana-de-açúcar",
        "season": "2025/26",
        "harvest_number": 2,
        "total_area_ha": 220.3,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_estimated_impact_brl": 156000.00,
            "avg_profitability_score": 8.1,
        },
        "zones": [
            {
                "zone_id": "Z001",
                "area_ha": 110.0,
                "avg_yield_t_ha": 82.3,
                "expected_yield_t_ha": 85.0,
                "profitability_score": 8.8,
                "status": "optimal",
                "recommendation": {
                    "action": "maintain",
                    "priority": "low",
                    "reason": "Excellent yield, 2nd cut performing well",
                },
                "financial_impact": {
                    "estimated_gain_brl_year": 145000.00,
                },
            },
            {
                "zone_id": "Z002",
                "area_ha": 110.3,
                "avg_yield_t_ha": 75.2,
                "expected_yield_t_ha": 85.0,
                "profitability_score": 7.4,
                "status": "warning",
                "recommendation": {
                    "action": "fertilizer_adjustment",
                    "priority": "medium",
                    "reason": "Yield slightly below expected, nutrient deficiency suspected",
                },
                "financial_impact": {
                    "estimated_loss_brl_year": 68000.00,
                },
            },
        ],
    },
}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Precision Agriculture Platform API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "recommendations": "/api/v1/recommendations (GET)",
            "fields": "/api/v1/fields (GET)",
            "health": "/health (GET)",
            "docs": "/docs (GET)",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "available_fields": len(MOCK_FIELDS),
    }


@app.get("/api/v1/fields")
async def list_fields():
    """List available fields."""
    fields = [
        {
            "field_id": data["field_id"],
            "crop": data["crop"],
            "area_ha": data["total_area_ha"],
            "season": data["season"],
        }
        for data in MOCK_FIELDS.values()
    ]
    return {"fields": fields, "total": len(fields)}


@app.get(
    "/api/v1/recommendations",
    response_model=FieldRecommendations,
    summary="Get field recommendations",
    description="Retrieve zone-based agronomic recommendations for a field",
)
async def get_recommendations(
    field_id: str = Query(
        ...,
        description="Field identifier (e.g., F001)",
        min_length=1,
        max_length=50,
    )
) -> FieldRecommendations:
    """
    Get agronomic recommendations for a field.
    
    Returns zone-based analysis with:
    - Yield performance vs expected
    - Profitability scores
    - Agronomic recommendations (maintain, reform, etc.)
    - Financial impact analysis
    
    Args:
        field_id: Field identifier (e.g., F001, F002)
        
    Returns:
        FieldRecommendations with complete analysis
        
    Raises:
        404: Field not found
    """
    # Extract short field ID (F001 from F001-UsinaGuarani-Piracicaba)
    short_id = field_id.split("-")[0] if "-" in field_id else field_id
    
    if short_id not in MOCK_FIELDS:
        raise HTTPException(
            status_code=404,
            detail=f"Field '{field_id}' not found. Available: {', '.join(MOCK_FIELDS.keys())}",
        )
    
    field_data = MOCK_FIELDS[short_id]
    
    # Update analysis date to current date
    field_data["analysis_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return FieldRecommendations(**field_data)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for better error messages."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
