"""Quick test of Precision API imports and data structures"""
from src.api import app, MOCK_FIELDS, FieldRecommendations

print("✓ API imports successful")
print(f"✓ Mock fields available: {list(MOCK_FIELDS.keys())}")

# Test data structure
field_data = MOCK_FIELDS["F001"]
recommendations = FieldRecommendations(**field_data)

print(f"✓ Field: {recommendations.field_id}")
print(f"✓ Zones: {len(recommendations.zones)}")
print(f"✓ Summary impact: R$ {recommendations.summary.total_estimated_impact_brl:,.2f}")
print("✓ Pydantic validation working!")
print("\nReady to start API server:")
print("  uvicorn src.api:app --host 0.0.0.0 --port 5000")
