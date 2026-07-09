"""
Configuração global para testes pytest.
"""

import sys
from pathlib import Path

# Adicionar src ao path para importar módulos
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Hook para configuração inicial do pytest"""
    print("\n" + "="*80)
    print("ANACONDO: Test Suite")
    print("="*80)
    print("Validando integridade de dados (schema, períodos, balanço)")
    print("="*80)
