#!/usr/bin/env python3
"""
Mock API do Precision-Agriculture-Platform
Simula endpoint: GET /api/v1/recommendations?field_id={id}

USO:
    python api_mock.py
    # Servidor roda em http://localhost:5000
    # Testar: curl http://localhost:5000/api/v1/recommendations?field_id=F001
"""

from flask import Flask, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)

# Carregar dados de exemplo
MOCK_DATA_PATH = Path(__file__).parent / "example_zones.json"

@app.route('/api/v1/recommendations', methods=['GET'])
def get_recommendations():
    """
    Retorna recomendações de manejo por zona
    
    Query params:
        field_id (str): ID do talhão
    
    Response: JSON com zonas + recomendações + impacto financeiro
    """
    field_id = request.args.get('field_id')
    
    if not field_id:
        return jsonify({
            "error": "field_id é obrigatório",
            "example": "/api/v1/recommendations?field_id=F001"
        }), 400
    
    # Carregar mock data
    with open(MOCK_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Simular resposta (na versão real, busca do banco)
    if field_id != data['field_id']:
        return jsonify({
            "error": f"Talhão {field_id} não encontrado",
            "available": [data['field_id']]
        }), 404
    
    return jsonify(data), 200


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check do serviço"""
    return jsonify({
        "status": "ok",
        "service": "Precision-Agriculture-Platform Mock",
        "version": "v1.0.0-mock"
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Documentação básica da API"""
    return jsonify({
        "service": "Precision-Agriculture-Platform Mock API",
        "endpoints": {
            "/api/v1/recommendations": {
                "method": "GET",
                "params": ["field_id"],
                "description": "Retorna recomendações de manejo por zona"
            },
            "/api/v1/health": {
                "method": "GET",
                "description": "Health check"
            }
        },
        "example": "GET /api/v1/recommendations?field_id=F001-UsinaGuarani-Piracicaba"
    }), 200


if __name__ == '__main__':
    print("\n🌱 Precision-Agriculture-Platform Mock API")
    print("=" * 50)
    print(f"📂 Dados mock: {MOCK_DATA_PATH}")
    print("🌐 Servidor: http://localhost:5000")
    print("📖 Documentação: http://localhost:5000/")
    print(f"🧪 Teste: curl http://localhost:5000/api/v1/recommendations?field_id=F001-UsinaGuarani-Piracicaba")
    print("=" * 50)
    print("\n▶️  Servidor rodando...\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
