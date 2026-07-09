#!/bin/bash
# Script para executar testes de validação de dados

set -e

echo "════════════════════════════════════════════════════════════════════════"
echo "ANACONDO: Executando Test Suite"
echo "════════════════════════════════════════════════════════════════════════"

# Verificar se pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest não está instalado"
    echo "Instale com: pip install -r requirements-dev.txt"
    exit 1
fi

# Executar testes com relatório
echo ""
echo "Rodando testes..."
pytest tests/test_data_validation.py \
    -v \
    --tb=short \
    --html=tests/report.html \
    --self-contained-html \
    -s

# Resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo "✓ Todos os testes passaram!"
    echo "📊 Relatório gerado: tests/report.html"
    echo "════════════════════════════════════════════════════════════════════════"
    exit 0
else
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo "❌ Alguns testes falharam"
    echo "════════════════════════════════════════════════════════════════════════"
    exit 1
fi
