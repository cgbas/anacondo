# CI/CD — GitHub Actions + Git LFS

## 📋 Configuração

### GitHub Actions Workflows

Todos os workflows estão em `.github/workflows/`:

| Workflow | Trigger | Ação |
|----------|---------|------|
| `test.yml` | Push/PR em main ou feature/* | Executa testes com pytest |
| `lint.yml` | Push/PR em main ou feature/* | Valida qualidade de código |

### Git LFS (Large File Storage)

Configurado em `.gitattributes` para versionamento eficiente de arquivos grandes:

- ✅ `exports/csv/*.csv` — CSVs processados
- ✅ `exports/figs/*.png` — Gráficos gerados
- ✅ `exports/hojas/**` — Dados brutos (XLSX, XLS)
- ✅ `exports/pdf/**` — PDFs

## 🚀 Como Usar

### Instalar Git LFS

```bash
# macOS
brew install git-lfs

# Linux
apt-get install git-lfs  # Debian/Ubuntu
yum install git-lfs      # RedHat/CentOS

# Depois
git lfs install
```

### Rastrear Arquivos com Git LFS

```bash
# Exemplo: rastrear um CSV grande
git lfs track "exports/csv/lancamentos_consolidados.csv"

# Ver arquivos rastreados
git lfs ls-files
```

### Push com LFS

```bash
# Git automaticamente detecta e usa LFS
git push origin main

# Ver status de LFS
git lfs status
```

## 🔍 Validação Local (Antes de Push)

Antes de fazer push, teste localmente:

### 1. Executar Testes

```bash
# Instalar dependências
pip install -r requirements-dev.txt

# Rodar testes
bash scripts/run_tests.sh
```

### 2. Lint de Notebooks

```bash
# Verificar qualidade de código
python scripts/lint_notebooks.py
```

### 3. Verificar Git

```bash
# Ver status
git status
git diff --cached

# Confirmar que tudo está bem
git status
```

## 📊 Relatórios de Testes

Após cada push/PR, os relatórios estão disponíveis como **Artifacts** no GitHub Actions:

- `pytest-report` — Relatório HTML com resultados dos testes

## 🔧 Troubleshooting

### Git LFS não está funcionando

```bash
# Verificar instalação
git lfs version

# Reinicializar LFS
git lfs install --force
```

### Arquivo foi commitado sem LFS

```bash
# Remover do histórico (cuidado!)
git lfs migrate import --include="exports/csv/*.csv"
```

### Testes falhando no GitHub

1. Verificar logs no GitHub Actions
2. Rodarhttps://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions
3. Fazer commit de fix em nova branch

## 📚 Referências

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Git LFS](https://git-lfs.com/)
- [Pytest Docs](https://docs.pytest.org/)
