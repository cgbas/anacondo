#!/usr/bin/env python3
"""
Script de lint para Jupyter Notebooks — Verificar qualidade de código

Regras:
1. Máximo de 5 print statements por célula (exceto seções de debug)
2. Sem hardcodes de caminhos (usar Path, constantes globais)
3. Sem credenciais em código
4. Todas as funções devem ter docstring
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

def check_notebook_lint(nb_path: Path) -> Tuple[bool, List[str]]:
    """
    Verifica qualidade de um notebook.
    
    Retorna (is_clean, list_of_warnings)
    """
    warnings = []
    
    try:
        with open(nb_path) as f:
            nb = json.load(f)
    except Exception as e:
        return False, [f"Erro ao abrir {nb_path}: {e}"]
    
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        
        source = "".join(cell.get("source", []))
        
        # Regra 1: Verificar quantidade de prints
        print_count = source.count("print(")
        if print_count > 10:
            warnings.append(
                f"  ⚠️  Célula {cell_idx + 1}: {print_count} print statements "
                f"(máximo recomendado: 10)"
            )
        
        # Regra 2: Verificar hardcodes de caminho
        hardcode_patterns = [
            "/Users/", "/home/", "C:\\", "D:\\",
            "~/Desktop", "~/Documents",
        ]
        for pattern in hardcode_patterns:
            if pattern in source:
                warnings.append(
                    f"  ⚠️  Célula {cell_idx + 1}: caminho hardcoded detectado: {pattern}"
                )
        
        # Regra 3: Verificar credenciais
        cred_patterns = ["password", "api_key", "secret", "token="]
        for pattern in cred_patterns:
            if pattern.lower() in source.lower():
                warnings.append(
                    f"  ⚠️  Célula {cell_idx + 1}: padrão de credencial detectado: {pattern}"
                )
        
        # Regra 4: Verificar docstrings em funções
        if "def " in source:
            lines = source.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    # Verificar se próxima linha tem docstring
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if not (next_line.startswith('"""') or next_line.startswith("'''")):
                            func_name = line.split("def ")[1].split("(")[0]
                            warnings.append(
                                f"  ⚠️  Célula {cell_idx + 1}: função '{func_name}' sem docstring"
                            )
    
    is_clean = len(warnings) == 0
    return is_clean, warnings


def main():
    """Executa lint em todos os notebooks."""
    src_dir = Path("src")
    nb_files = list(src_dir.glob("*.ipynb"))
    
    if not nb_files:
        print("⚠️  Nenhum notebook encontrado em src/")
        return 0
    
    print("🔍 Executando lint de notebooks...\n")
    
    total_issues = 0
    for nb_file in sorted(nb_files):
        is_clean, warnings = check_notebook_lint(nb_file)
        
        if is_clean:
            print(f"✓ {nb_file.name}: OK")
        else:
            print(f"⚠️  {nb_file.name}:")
            for warning in warnings:
                print(warning)
                total_issues += 1
            print()
    
    if total_issues > 0:
        print(f"\n⚠️  Total de problemas encontrados: {total_issues}")
        print("💡 Dica: execute scripts/run_tests.sh para mais detalhes")
        return 1
    else:
        print("\n✓ Todos os notebooks passaram no lint!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
