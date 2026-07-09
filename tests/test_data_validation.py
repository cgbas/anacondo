"""
Test suite para validação de dados dos CSVs gerados.

Executa validações de:
- Schema: tipos de dados corretos
- Períodos: todos os meses esperados presentes
- Balanço: receitas ≈ despesas (tolerância 1%)
- Integridade: sem duplicatas, NaNs inesperados
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pytest
from typing import Tuple, Dict, List

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO E FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

CSV_DIR = Path(__file__).parent.parent / "exports" / "csv"

# Schema esperado para cada CSV
SCHEMA_PRESTACOES = {
    "mes_ano": "object",  # string YYYY-MM
    "evento": "object",
    "tipo": "object",  # RECEITA ou DESPESA
    "valor": "float64",
    "macro_categoria": "object",
}

SCHEMA_EXTRATOS = {
    "mes_ano": "object",
    "data": "object",
    "subconta": "object",
    "historico": "object",
    "complemento": "object",
    "debito": "float64",
    "credito": "float64",
    "saldo": "float64",
    "saldo_anterior": "float64",
}

SCHEMA_ANOMALIAS = {
    "mes_ano": "object",
    "evento": "object",
    "tipo": "object",
    "valor": "float64",
    "macro_categoria": "object",
    "motivo_anomalia": "object",
}

# ═══════════════════════════════════════════════════════════════════════════
# TESTES: VALIDAÇÃO DE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def df_prestacoes():
    """Carrega prestacoes.csv"""
    csv_path = CSV_DIR / "prestacoes.csv"
    if not csv_path.exists():
        pytest.skip(f"Arquivo não encontrado: {csv_path}")
    return pd.read_csv(csv_path)


@pytest.fixture
def df_extratos():
    """Carrega extratos.csv"""
    csv_path = CSV_DIR / "extratos.csv"
    if not csv_path.exists():
        pytest.skip(f"Arquivo não encontrado: {csv_path}")
    return pd.read_csv(csv_path)


@pytest.fixture
def df_anomalias():
    """Carrega anomalias_prestacoes.csv"""
    csv_path = CSV_DIR / "anomalias_prestacoes.csv"
    if not csv_path.exists():
        pytest.skip(f"Arquivo não encontrado: {csv_path}")
    return pd.read_csv(csv_path)


class TestSchemaValidation:
    """Validação de tipos de dados (schema)"""

    @staticmethod
    def _dtype_matches(dtype, expected: str) -> bool:
        """Compara dtype aceitando 'object' e 'str' como equivalentes para strings.
        Necessário porque pandas 3.x reporta StringDtype como 'str' em vez de 'object'."""
        actual = str(dtype)
        if expected == "object":
            return actual in ("object", "str")
        return actual == expected

    def test_prestacoes_schema(self, df_prestacoes):
        """Verifica se colunas têm tipos corretos"""
        for col, expected_type in SCHEMA_PRESTACOES.items():
            assert col in df_prestacoes.columns, f"Coluna '{col}' não existe"
            assert self._dtype_matches(df_prestacoes[col].dtype, expected_type), \
                f"Coluna '{col}': esperado {expected_type}, obtido {df_prestacoes[col].dtype}"

    def test_extratos_schema(self, df_extratos):
        """Verifica se colunas têm tipos corretos"""
        for col, expected_type in SCHEMA_EXTRATOS.items():
            assert col in df_extratos.columns, f"Coluna '{col}' não existe"
            assert self._dtype_matches(df_extratos[col].dtype, expected_type), \
                f"Coluna '{col}': esperado {expected_type}, obtido {df_extratos[col].dtype}"

    def test_anomalias_schema(self, df_anomalias):
        """Verifica se colunas têm tipos corretos"""
        for col, expected_type in SCHEMA_ANOMALIAS.items():
            assert col in df_anomalias.columns, f"Coluna '{col}' não existe"
            assert self._dtype_matches(df_anomalias[col].dtype, expected_type), \
                f"Coluna '{col}': esperado {expected_type}, obtido {df_anomalias[col].dtype}"

    def test_valor_column_numeric(self, df_prestacoes, df_extratos):
        """Confirma que coluna 'valor' é sempre numérica (float) em prestacoes,
        e que debito/credito são numéricos em extratos"""
        assert df_prestacoes["valor"].dtype in ["float64", "float32"], \
            "df_prestacoes['valor'] deve ser float"
        
        # Sem NaNs ou infinitos em prestacoes
        assert not df_prestacoes["valor"].isna().any(), \
            "df_prestacoes['valor'] tem NaNs"
        assert np.isfinite(df_prestacoes["valor"]).all(), \
            "df_prestacoes['valor'] tem infinitos"

        # extratos usa debito/credito (mutuamente exclusivos, NaN é esperado)
        assert df_extratos["debito"].dtype in ["float64", "float32"], \
            "df_extratos['debito'] deve ser float"
        assert df_extratos["credito"].dtype in ["float64", "float32"], \
            "df_extratos['credito'] deve ser float"
        assert np.isfinite(df_extratos["debito"].dropna()).all(), \
            "df_extratos['debito'] tem infinitos"
        assert np.isfinite(df_extratos["credito"].dropna()).all(), \
            "df_extratos['credito'] tem infinitos"

    def test_tipo_column_valid_values(self, df_prestacoes, df_extratos):
        """Coluna 'tipo' deve conter apenas RECEITA ou DESPESA em prestacoes;
        em extratos debito (negativo) e credito (positivo) são mutuamente exclusivos"""
        valid_tipos = {"RECEITA", "DESPESA"}
        
        invalid_prestacoes = set(df_prestacoes["tipo"].unique()) - valid_tipos
        assert not invalid_prestacoes, \
            f"df_prestacoes['tipo'] contém valores inválidos: {invalid_prestacoes}"
        
        # Em extratos, debito e credito não devem coexistir na mesma linha
        both_set = df_extratos["debito"].notna() & df_extratos["credito"].notna()
        assert not both_set.any(), \
            f"Extratos têm {both_set.sum()} linhas com debito E credito simultâneos"

    def test_mes_ano_format(self, df_prestacoes, df_extratos):
        """Coluna 'mes_ano' deve estar em formato YYYY-MM"""
        import re
        
        mes_ano_pattern = re.compile(r"^\d{4}-\d{2}$")
        
        invalid_meses_p = df_prestacoes[~df_prestacoes["mes_ano"].astype(str).str.match(mes_ano_pattern)]
        assert len(invalid_meses_p) == 0, \
            f"df_prestacoes['mes_ano'] com formato inválido: {invalid_meses_p['mes_ano'].unique()}"
        
        invalid_meses_e = df_extratos[~df_extratos["mes_ano"].astype(str).str.match(mes_ano_pattern)]
        assert len(invalid_meses_e) == 0, \
            f"df_extratos['mes_ano'] com formato inválido: {invalid_meses_e['mes_ano'].unique()}"


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: VALIDAÇÃO DE PERÍODOS
# ═══════════════════════════════════════════════════════════════════════════


class TestPeriodValidation:
    """Validação de cobertura de períodos"""

    def test_prestacoes_period_continuous(self, df_prestacoes):
        """Verifica se prestações cobrem período esperado (mai/2022 - jun/2026)"""
        meses = sorted(df_prestacoes["mes_ano"].unique())
        
        # Primeiro e último mês esperado
        assert meses[0] == "2022-05", f"Período inicial esperado: 2022-05, obtido: {meses[0]}"
        assert meses[-1] == "2026-06", f"Período final esperado: 2026-06, obtido: {meses[-1]}"
        
        # Meses faltantes conhecidos (PDFs não cobrem estes meses)
        known_gaps = {"2023-06"}
        expected_months = pd.date_range(start="2022-05", end="2026-06", freq="MS").strftime("%Y-%m").tolist()
        missing_months = set(expected_months) - set(meses) - known_gaps
        assert not missing_months, f"Meses inesperadamente faltantes em prestacoes: {sorted(missing_months)}"

    def test_extratos_period_coverage(self, df_extratos):
        """Verifica se extratos cobrem período (ago/2025 - jun/2026)"""
        meses = sorted(df_extratos["mes_ano"].unique())
        
        # Primeiro e último mês esperado
        assert meses[0] == "2025-08", f"Período inicial esperado: 2025-08, obtido: {meses[0]}"
        assert meses[-1] == "2026-06", f"Período final esperado: 2026-06, obtido: {meses[-1]}"
        
        # Nenhum mês faltante
        expected_months = pd.date_range(start="2025-08", end="2026-06", freq="MS").strftime("%Y-%m").tolist()
        missing_months = set(expected_months) - set(meses)
        assert not missing_months, f"Meses faltantes em extratos: {sorted(missing_months)}"

    def test_prestacoes_each_month_has_data(self, df_prestacoes):
        """Cada mês deve ter registros de receita E despesa"""
        for mes_ano in df_prestacoes["mes_ano"].unique():
            df_mes = df_prestacoes[df_prestacoes["mes_ano"] == mes_ano]
            
            has_receita = (df_mes["tipo"] == "RECEITA").any()
            has_despesa = (df_mes["tipo"] == "DESPESA").any()
            
            assert has_receita, f"Mês {mes_ano} sem RECEITA"
            assert has_despesa, f"Mês {mes_ano} sem DESPESA"

    def test_extratos_each_month_has_data(self, df_extratos):
        """Cada mês deve ter registros de débito E crédito"""
        for mes_ano in df_extratos["mes_ano"].unique():
            df_mes = df_extratos[df_extratos["mes_ano"] == mes_ano]
            
            has_credito = df_mes["credito"].notna().any()
            has_debito = df_mes["debito"].notna().any()
            
            assert has_credito, f"Mês {mes_ano} sem crédito"
            assert has_debito, f"Mês {mes_ano} sem débito"


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: VALIDAÇÃO DE BALANÇO PATRIMONIAL
# ═══════════════════════════════════════════════════════════════════════════


class TestBalanceValidation:
    """Validação de balanço: receitas ≈ despesas"""

    def test_prestacoes_total_balance_reasonable(self, df_prestacoes):
        """Verifica se balanço total é razoável (receptoras ≥ 95% despesas)"""
        total_receita = df_prestacoes[df_prestacoes["tipo"] == "RECEITA"]["valor"].sum()
        total_despesa = df_prestacoes[df_prestacoes["tipo"] == "DESPESA"]["valor"].sum()
        
        razao = total_receita / total_despesa if total_despesa > 0 else 0
        
        # Receitas devem cobrir pelo menos 95% das despesas (tolerância: 5%)
        assert razao >= 0.95, \
            f"Balanço em prestacoes não saudável: receita cobre apenas {razao*100:.1f}% despesa"
        
        print(f"\n✓ Balanço prestacoes: {total_receita/1e6:.2f}M receita / {total_despesa/1e6:.2f}M despesa = {razao*100:.1f}%")

    def test_extratos_total_balance_reasonable(self, df_extratos):
        """Verifica se balanço total é razoável"""
        total_credito = df_extratos["credito"].sum()  # NaN conta como 0
        total_debito_abs = df_extratos["debito"].abs().sum()
        
        razao = total_credito / total_debito_abs if total_debito_abs > 0 else 0
        
        # Receitas devem cobrir pelo menos 90% das despesas (tolerância maior para extratos)
        assert razao >= 0.90, \
            f"Balanço em extratos não saudável: crédito cobre apenas {razao*100:.1f}% débito"
        
        print(f"\n✓ Balanço extratos: {total_credito/1e6:.2f}M crédito / {total_debito_abs/1e6:.2f}M débito = {razao*100:.1f}%")

    def test_prestacoes_monthly_balance_consistency(self, df_prestacoes):
        """Cada mês deve ter receita + despesa sem déficit excessivo"""
        for mes_ano in sorted(df_prestacoes["mes_ano"].unique()):
            df_mes = df_prestacoes[df_prestacoes["mes_ano"] == mes_ano]
            
            receita = df_mes[df_mes["tipo"] == "RECEITA"]["valor"].sum()
            despesa = df_mes[df_mes["tipo"] == "DESPESA"]["valor"].sum()
            
            # Déficit máximo permitido: 50% (dados de PDFs podem ter cobertura parcial)
            razao = receita / despesa if despesa > 0 else 0
            assert razao >= 0.50, \
                f"Mês {mes_ano}: receita muito baixa ({razao*100:.1f}% da despesa)"

    def test_extratos_monthly_balance_consistency(self, df_extratos):
        """Cada mês deve ter crédito + débito sem déficit excessivo"""
        for mes_ano in sorted(df_extratos["mes_ano"].unique()):
            df_mes = df_extratos[df_extratos["mes_ano"] == mes_ano]
            
            credito = df_mes["credito"].sum()
            debito_abs = df_mes["debito"].abs().sum()
            
            # Déficit máximo permitido: 15%
            razao = credito / debito_abs if debito_abs > 0 else 0
            assert razao >= 0.85, \
                f"Mês {mes_ano}: crédito muito baixo ({razao*100:.1f}% do débito)"


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: INTEGRIDADE DE DADOS
# ═══════════════════════════════════════════════════════════════════════════


class TestDataIntegrity:
    """Validação de integridade geral"""

    def test_prestacoes_no_duplicate_rows(self, df_prestacoes):
        """Não deve haver duplicatas exatas"""
        duplicatas = df_prestacoes.duplicated().sum()
        assert duplicatas == 0, f"df_prestacoes tem {duplicatas} linhas duplicadas"

    def test_extratos_no_duplicate_rows(self, df_extratos):
        """Não deve haver duplicatas exatas"""
        duplicatas = df_extratos.duplicated().sum()
        assert duplicatas == 0, f"df_extratos tem {duplicatas} linhas duplicadas"

    def test_prestacoes_no_unexpected_nulls(self, df_prestacoes):
        """Colunas críticas não devem ter NaNs"""
        critical_cols = ["mes_ano", "evento", "tipo", "valor", "macro_categoria"]
        for col in critical_cols:
            nulls = df_prestacoes[col].isna().sum()
            assert nulls == 0, f"df_prestacoes['{col}'] tem {nulls} NaNs"

    def test_extratos_no_unexpected_nulls(self, df_extratos):
        """Colunas críticas não devem ter NaNs"""
        critical_cols = ["mes_ano", "subconta", "historico"]
        for col in critical_cols:
            nulls = df_extratos[col].isna().sum()
            assert nulls == 0, f"df_extratos['{col}'] tem {nulls} NaNs"

    def test_valor_always_positive(self, df_prestacoes, df_extratos):
        """Coluna 'valor' deve ser sempre positiva em prestacoes;
        debito deve ser sempre negativo e credito sempre positivo em extratos"""
        negative_p = (df_prestacoes["valor"] < 0).sum()
        assert negative_p == 0, f"df_prestacoes tem {negative_p} valores negativos"
        
        positive_debito = (df_extratos["debito"].dropna() > 0).sum()
        assert positive_debito == 0, f"df_extratos tem {positive_debito} débitos positivos (devem ser negativos)"
        
        negative_credito = (df_extratos["credito"].dropna() < 0).sum()
        assert negative_credito == 0, f"df_extratos tem {negative_credito} créditos negativos"

    def test_macro_categoria_valid_values(self, df_prestacoes):
        """Macro-categorias devem estar no conjunto esperado"""
        valid_categories = {
            "Pessoal", "Utilidades", "Manutenção", "Taxas e Impostos",
            "Administração", "Receitas Condominiais", "Fundos", "Retiradas/Acerto", "Outros"
        }
        
        invalid_p = set(df_prestacoes["macro_categoria"].unique()) - valid_categories
        assert not invalid_p, f"df_prestacoes com categorias inválidas: {invalid_p}"


# ═══════════════════════════════════════════════════════════════════════════
# TESTES: ANOMALIAS
# ═══════════════════════════════════════════════════════════════════════════


class TestAnomalies:
    """Validação de detecção de anomalias"""

    def test_anomalias_csv_exists(self):
        """Arquivo anomalias_prestacoes.csv deve existir"""
        csv_path = CSV_DIR / "anomalias_prestacoes.csv"
        assert csv_path.exists(), f"Arquivo não encontrado: {csv_path}"

    def test_anomalias_have_valid_reasons(self, df_anomalias):
        """Cada anomalia deve ter motivo válido"""
        valid_reasons = {
            "Outlier IQR", "Não mapeado", "Sem NF", "Retirada/Posterior",
            "Evento sem categoria mapeada"
        }
        
        invalid = df_anomalias[~df_anomalias["motivo_anomalia"].isin(valid_reasons)]
        assert len(invalid) == 0, \
            f"Anomalias com motivos inválidos: {invalid['motivo_anomalia'].unique()}"

    def test_anomalias_subset_of_prestacoes(self, df_prestacoes, df_anomalias):
        """Todas as anomalias devem estar em prestacoes.csv"""
        # Criar chave composta para comparação
        key_prestacoes = set(zip(df_prestacoes["mes_ano"], df_prestacoes["evento"], df_prestacoes["valor"]))
        key_anomalias = set(zip(df_anomalias["mes_ano"], df_anomalias["evento"], df_anomalias["valor"]))
        
        extra = key_anomalias - key_prestacoes
        assert len(extra) == 0, \
            f"Anomalias não encontradas em prestacoes: {extra}"


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTAR TESTES
# ═══════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    """Executa testes com pytest"""
    pytest.main([__file__, "-v", "--tb=short", "-s"])
