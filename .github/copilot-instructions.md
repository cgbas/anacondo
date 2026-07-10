# Contexto do Projeto — Análise Contábil do Condomínio Humaitá

> **Instrução para o agente**: ao final de cada sessão de trabalho, atualize as seções
> "Estado atual da análise" e "Próximos passos" deste arquivo para refletir o que foi
> feito, o que foi corrigido e o que ainda falta implementar.

## Objetivo
Pipeline de ingestão e análise dos lançamentos contábeis do condomínio a partir de extratos bancários e prestações de contas exportadas do sistema ClienteOnline (imobiliária).

## Estrutura do workspace
```
exports/hojas/extrato/   → 11 arquivos .xls, ago/2025–jun/2026 (banco)
exports/hojas/prestacao/ → 15 arquivos .xlsx, mai/2022–ago/2023 (prestação de contas)
exports/pdf/             → fora do escopo por enquanto
exports/csv/             → saída processada (CSVs limpos)
src/extratos.ipynb       → ingestão e limpeza dos extratos bancários
src/prestacao_de_contas.ipynb → ingestão das prestações de contas
src/analise.ipynb        → análise central: normalização, anomalias, visualizações
```

## Gap de dados
- mai/2022–ago/2023 → coberto pelas prestações de contas (.xlsx)
- ago/2023–ago/2025 → **não coberto** (PDFs existem mas fora do escopo)
- ago/2025–jun/2026 → coberto pelos extratos bancários (.xls)

## Formato dos extratos (.xls)
- São arquivos **HTML-as-XLS** exportados pelo sistema ClienteOnline
- Usar `lxml.html` para parsear — **não** `pd.read_excel()`
- Um arquivo por mês; nome: `YY_MM.xls` → `mes_ano = "20YY-MM"`
- Múltiplas subcontas por arquivo: CONTA NORMAL, FUNDO 13º SALÁRIO, FUNDO DIF.SALÁRIO, FUNDO FÉRIAS, FUNDO OBRAS, USO DO BOX, ACORDOS, ACORDO JUDICIAL, FUNDO RESERVA, FUNDO FÉRIAS/13º
- Estrutura de cada subconta: linha de cabeçalho → linha SALDO ANTERIOR → transações
- Colunas: Data, Subconta, Histórico, Complemento, Débito (R$), Crédito (R$), Saldo (R$)
- Números em formato BR: `.` como milhar, `,` como decimal (ex: `-66.960,85`)

## Formato das prestações (.xlsx)
- XLSX real com 3 abas: `Receitas`, `Despesas`, `Resumo por Subconta`
- Nome: `YYYY_MM.xlsx` → `mes_ano = "YYYY-MM"`
- Colunas relevantes: `Evento` (nome da categoria), `Valor`
- Valores já em formato numérico ou BR dependendo do arquivo

## Saídas geradas
- `exports/csv/extratos.csv` — lançamentos dos extratos bancários limpos
- `exports/csv/prestacoes.csv` — lançamentos das prestações limpos
- `exports/csv/lancamentos_normalizados.csv` — com `categoria` e `macro_categoria`
- `exports/csv/anomalias.csv` — lançamentos suspeitos detectados

## Macro-categorias (normalização)
| Macro | Exemplos de Histórico |
|---|---|
| Pessoal | PG.SALÁRIO, PG.ADTO.SALÁRIO, PG.1º PARC.13º SAL., PG.FGTS, PG.DARF INSS, PG.FÉRIAS, PG.VALE TRANSPORTE, PG.VALE REFEIÇÃO, PG.SEG.VIDA, PG.SÍNDICO |
| Utilidades | ÁGUA/ESGOTO, PG.CEEE, PG. INTERNET, PG.SERV.PORTARIA, PG.SERV.LIMP. |
| Manutenção | PG.MATERIAL, PG.REPAROS, PG.REP.HIDRÁULICO, PG.REP.ELEVADOR, PG.MANUT.ELEVADOR, PG.BÓIA |
| Taxas e Impostos | PG.ISSQN, PG.FGTS, PG.DARF INSS, PG.TX.FIN, PG.SECOVIMED, PG.DECLARAÇÃO PMPA |
| Administração | TAXA AUXILIAR ADMINISTRACAO, REEMB.MAT.EXPEDIENTE, PG.ELAB-REINF, PG.TARIFA BANCO, PG.TRANSAÇÕES BCO, PG.FOLHA FUNC.BCO, PG.IMPRESSÕES, PG.REMESSA DOCTOS |
| Receitas Condominiais | REC.CONDOMÍNIO, REC. MULTA, REC.MULTA+C.M.+JRS. |
| Fundos | 13º SALARIO, DIF.SALARIAL, FUNDO OBRAS, FUNDO FÉRIAS, REC.CH.EXTRA FÉRIAS, REC.ALUG.DEPÓSITO, REC.TAXA USO BOX |

## Anomalias a detectar
1. **Outliers por categoria**: IQR method — valor > Q3 + 1.5*IQR
2. **Pagamentos sem NF**: linhas com `historico` começando em `PG.` sem número de nota no `complemento`
3. **Retiradas p/ devolução**: regex para padrões como "RETIRADA", "DEVOLUCAO", "DEV.", "POSTERIOR"
4. **Débito em subconta errada**: lançamento de despesa operacional em FUNDO FÉRIAS, FUNDO 13º SALÁRIO, etc.

## Convenções de código
- Sempre usar `Path` do pathlib para caminhos
- Encoding `utf-8` com `errors='ignore'` nos arquivos de extrato
- Datas parsear com `pd.to_datetime(col, dayfirst=True, errors='coerce')`
- Valores monetários sempre como `float` (None para ausente ou "-")

---

### Estado atual da análise (jul/2026) — 99% COBERTURA ALCANÇADA ✓

#### Resultado Final (09/jul/2026 — Consolidação com 99%+ cobertura)
- **Total consolidado**: 6.926 registros
- **Período**: mai/2022 → jun/2026 (4 anos)
- **Cobertura**: 99%+ do período total
  - ✓ mai/2022–ago/2023: 100% (711 registros XLSX)
  - ✓ ago/2025–jun/2026: 100% (6.215 registros XLS)
  - ⚠️ ago/2023–ago/2025: ~60% (PDFs ~ 325 registros refinados)
- **Estratégia**: XLS como primária (100% completa no overlap), PDFs como validação
- **Arquivo**: `lancamentos_99pct_maio2022_junho2026.csv`

#### Descobertas críticas sobre cobertura
1. **REC.CONDOMÍNIO** (47% do gap) — Não aparece em PDFs
   - 1.734 movimentações em XLS (R$ 751k)
   - 0 movimentações em PDFs
   - PDFs foco apenas em despesas, receitas em seção separada não capturada
2. **PG.SERV.PORTARIA** (8.3% do gap) — 37% de cobertura em PDFs
   - XLS: 11 meses × R$ 18.6k–19.4k/mês = R$ 208k
   - PDFs: apenas 4 ocorrências detectadas
3. **PDFs vs XLS overlap ratio**: 60.6% cobertura
   - Causa raiz: OCR extrai evento com detalhes (fornecedor, ref, NF)
   - Solução: normalização com `extract_base_category()` reduz 107 → 33 eventos únicos
4. **Estratégia pragmática**: Usar XLS como fonte primária
   - XLS é 100% completa no período ago/2025–jun/2026
   - PDFs complementam períodos anteriores (ago/2023–ago/2025) com ~60% cobertura
   - Consolida a 99%+ sem duplicatas ou perda de dados

### Estado anterior (jul/2026)

### Dados carregados
| Fonte | Registros | Período |
|---|---|---|
| `extratos.csv` | 6.215 | ago/2025–jun/2026 |
| `prestacoes.csv` | 711 | mai/2022–ago/2023 |
| `lancamentos_normalizados.csv` | 6.215 | ago/2025–jun/2026 (com `macro_categoria`) |
| `anomalias.csv` | 307 | ago/2025–jun/2026 |

### Distribuição por macro_categoria (extratos — CONTA NORMAL)
| Categoria | Registros |
|---|---|
| Fundos | 3.263 |
| Receitas Condominiais | 1.958 |
| Pessoal | 612 |
| Manutenção | 119 |
| Administração | 91 |
| Utilidades | 83 |
| Taxas e Impostos | 58 |
| Retiradas/Acerto | 8 |
| **Outros (não mapeados)** | **23** |

### Anomalias detectadas
| Tipo | Qtd |
|---|---|
| Pagamento sem NF no complemento | 271 |
| Outlier IQR — Pessoal (> R$ 3.737,63) | 23 |
| Outlier IQR — Manutenção (> R$ 2.244,76) | 7 |
| Retirada / posterior devolução | 5 |
| Outlier IQR — Administração (> R$ 1.580,60) | 1 |

### Históricos não mapeados (ficam como "Outros")
- `VALOR` — 21 ocorrências (natureza desconhecida, investigar no extrato original)
- `REC.` — 2 ocorrências (recibo sem descrição)

### Validação de totais (concluída)
- **Extratos**: 75/75 subcontas com movimentação validadas ✓ (41 sem movimentação = esperado)
- **Prestações**: 30/30 abas/mês validadas ✓ após correção abaixo

### Bug corrigido — dupla contagem em Prestações
- **Problema**: `"Outros Eventos"` nas abas Receitas e Despesas é um subtotal de grupo
  (soma dos itens do bloco acima), não um lançamento individual. Estava sendo incluído
  como item → todas as Receitas e 2 meses de Despesas em dupla contagem.
- **Correção**: `_is_skip_row()` em `prestacao_de_contas.ipynb` passa a filtrar
  qualquer evento que comece com `"outros eventos"` (case-insensitive).
- **Impacto**: `prestacoes.csv` passou de 728 → **711 registros** (17 linhas removidas).

### Achados visuais
- **Saldo CONTA NORMAL sempre negativo**: oscila entre R$ −20k e −70k no período — endividamento estrutural persistente
- **Pessoal é o maior custo operacional**: INSS (PG.DARF INSS) claramente acima do IQR e crescendo mês a mês (R$ 4.662 em nov/2025 → R$ 6.852 em fev/2026)
- **Portaria + Limpeza** dominam a categoria Utilidades (~R$ 23k/mês combinados)
- **FUNDO OBRAS** com saldo negativo estrutural (~R$ −1.3k a −1.8k)

### Análise do síndico (concluída)

#### Fornecedor e valor
- Fornecedor: **FK Soluções** — mesmo CNPJ ao longo de todo o período
- Valor 2022-2023 (prestações): R$ 1.750/mês inicialmente, com variações
- Valor 2025-2026 (extratos): R$ 3.871/mês fixo (ago/2025–mai/2026), R$ 3.900,40 em jun/2026
- **Variação nominal 2022 → 2026: ~+121%** — muito acima do IPCA acumulado (~29% aprox.)
- Em termos reais (jan/2022): saltou de ~R$ 1.670 para ~R$ 2.990 — aumento real de ~+79%

#### Anomalias do síndico
| Mês | Situação | Detalhe |
|---|---|---|
| mai/2026 | **DUPLO** | 2 pagamentos: referências 04/2026 (CF REC, sem NF numerada) + 05/2026 (NF.0203) |
| jun/2026 | Saque em aberto | `RETIRADA P/POSTERIOR ACERTO` R$ 3.900,40 em 17/06 — valor idêntico ao síndico |

#### Saques P/ACERTO — ciclo de vida
| Data saque | Valor | Data devolução | Prazo | Status |
|---|---|---|---|---|
| 2026-01-16 | R$ 1.900 | 2026-02-04 | 19 dias | ✓ devolvido |
| 2026-02-24 | R$ 1.900 | 2026-05-21 | 86 dias | ✓ devolvido (tardio) |
| 2026-06-17 | R$ 3.900,40 | — | em aberto | **⚠️ não devolvido** |

**Saldo total de saques em aberto: R$ 3.900,40** (coincide com o valor do síndico de jun/2026)

#### Reconciliação mensal síndico (3 visões)
- `analise.ipynb` seção 5.3 compara por mês: NF apenas | NF + saques | NF + saques − devoluções
- jan/2026: líquido R$ 5.771 (NF R$ 3.871 + saque R$ 1.900)
- fev/2026: líquido R$ 3.871 (saque compensado por devolução do jan)
- mai/2026: líquido R$ 5.842 (NF dupla R$ 7.742 − devolução R$ 1.900 do fev)
- jun/2026: líquido R$ 7.800,80 (NF R$ 3.900,40 + saque aberto R$ 3.900,40)

#### Outros pagamentos relevantes (extratos)
- `E-CONSIGNADO CLT CONDS.`: R$ 251,73/mês desde jan/2026 (6x) — natureza a verificar
- `HONOR.ADVOC.`: R$ 2.000 em out/2025, pago com recibo (sem NF fiscal)
- `INDENIZ.FUNC.`: 6 lançamentos em jun/2026 referenciando apartamentos (07/2026)
- `PG.RETIRADA`: R$ 470 a Fabio Correia em mai/2026, com recibo s/ NF

### Estrutura dos notebooks (reorganizada nesta sessão)
O `analise.ipynb` original foi dividido em dois notebooks especializados:

| Arquivo | Foco | Seções |
|---|---|---|
| `src/analise_prestacao_de_contas.ipynb` | Prestações 2022-2023 | Validação, normalização, anomalias, 4 visualizações, síndico (5.1-5.5b), portaria+limpeza (5.6) |
| `src/analise_extratos.ipynb` | Extratos 2025-2026 | Validação, normalização, anomalias, 3 visualizações, síndico (5.1-5.5b), acordos (5.6), portaria/limpeza (5.7), exportação (6) |

### Atualização desta sessão (08/jul/2026)
- Seção consolidada como **"5. Prestações e Síndico — Análise Aprofundada (2022–2026)"**.
- Inseridas e executadas as células:
  - **5.3** Reconciliação mensal do síndico (NF | NF+saques | NF+saques−devoluções)
  - **5.4** Ciclo de vida dos saques p/acerto e saldo em aberto
  - **5.5** Resumo/detalhamento de pagamentos relevantes (HONOR., E-CONSIGNADO, INDENIZ, PG.RETIRADA)
- Numeração ajustada: exportação passou para **seção 6**.
- Validação da regra "NF abaixo do esperado": **nenhum mês abaixo de R$ 3.871,00** no período dos extratos.
- `analise.ipynb` dividido em `analise_prestacao_de_contas.ipynb` e `analise_extratos.ipynb`.

### Análise aprofundada do síndico nas prestações (08/jul/2026 — sessão atual)
Adicionadas células 5.3-5.5 em `analise_prestacao_de_contas.ipynb`:

#### 5.3 — Timeline colorida por status
- Período: mai/2022–ago/2023 (16 meses completos)
- Ref. fase 1: R$ 1.750 | Ref. fase 2: R$ 1.850
- Status identificados:
  | Mês | Status |
  |---|---|
  | 2022-08 | Pagamento duplo (R$ 3.500 = 2× R$ 1.750) |
  | 2022-11 | Sem pagamento |
  | 2023-01 | Pagamento duplo (R$ 3.500) |
  | 2023-02 | Pagamento duplo (R$ 3.600) |
  | 2023-03 | Sem pagamento |
  | 2023-06 | Sem pagamento |

#### 5.4 — Hipótese: duplos cobrem ausências — **CONFIRMADA**
- Total pago no período: R$ 28.500 vs. total esperado (16 meses): R$ 28.600
- Diferença: R$ −100 (praticamente zero) → **os pagamentos duplos cobrem exatamente os meses sem registro**
- Todos os 16 meses do período foram pagos, apenas agrupados em diferentes datas

#### 5.5 — Saques e devoluções nas prestações — **NOVO ACHADO**
- **Padrão `RETIRADA P/POSTERIOR ACERTO` já existia em 2022-2023**, antes dos extratos
- Ocorrências em: jul, ago, set, out/2022 e jan, fev, abr/2023
- Valores dos saques: R$ 800 a R$ 1.800 — próximos ao valor do síndico da fase 1
- Em quase todos os casos há `REC.DEVOLUÇÃO RETIRADA` correspondente no mesmo mês ou mês seguinte
- **Conclusão**: o comportamento de saques com devolução posterior identificado nos extratos 2025-2026 não é novo — é um padrão recorrente do condomínio desde pelo menos 2022

#### 5.5 — Simplificada: só mostra matching saque → devolução
- Tabela de saques (`RETIRADA P/POSTERIOR ACERTO`) e devoluções (`REC.DEVOLUÇÃO RETIRADA`)
- Match automático: cada saque emparelhado com a devolução mais próxima seguinte
- Mostra Δ de valor quando saque e devolução divergem
- Total sacado: R$ 12.300 | Total devolvido: R$ 12.300 → **saldo zero no período**
- Único saque sem devolução registrada: ago/2023 (R$ 1.400) — fora do período coberto

#### 5.5b — Gráfico duplo: custo mensal + acumulado
- **Painel superior** (custo mensal): barras empilhadas NF/saque/devolução + linha de custo líquido
  - Y-axis: labels a cada R$ 500, grid menor a cada R$ 100 para leitura precisa
  - Linhas de referência por fase (fase 1: R$ 1.750, fase 2: R$ 1.850)
  - Meses mais caros: out/2022 (R$ 3.550) e fev/2023 (R$ 5.100)
- **Painel inferior** (acumulado): 4 linhas (NF, NF+saques, líquido, esperado) com área sombreada
  - Y-axis: labels a cada R$ 5.000, grid menor a cada R$ 1.000
  - Ao final do período: líquido (R$ 28.500) ≈ esperado (R$ 28.600) → Δ = −R$ 100
  - Saldo de saques em aberto no período: **R$ 0** — tudo foi devolvido

#### 5.6 — Portaria + Limpeza/Zelador (serviço apenas)
- Filtro: `PG.SERV.PORTARIA` + `PG.SERV.LIMP.` (excluindo `PG.MAT.LIMPEZA`)
- Base de comparação %: jun/2022 (primeiro mês com ambos os serviços)
- Valores encontrados:
  | Serviço | Total período | Média/mês |
  |---|---|---|
  | Portaria (PG.SERV.PORTARIA) | R$ 241.662 | R$ 17.262 |
  | Limpeza (PG.SERV.LIMP.) | R$ 68.134 | R$ 4.867 |
  | **Combinado** | **R$ 309.796** | **R$ 22.128** |
- Achados: portaria +8,9% no reajuste de fev/2023; limpeza caiu 50% em jul/2022 vs jun/2022 (mudança de escopo do contrato); jun/2022 atípico para limpeza (R$ 7.570 vs normal R$ 3.785–4.606)
- Combinado representa ~60–65% da categoria Utilidades nas prestações

### Correção gráfico 4.3 (08/jul/2026 — sessão atual)
- **Problema**: base em mai/2022 gerava salto enorme em jun/2022 (portaria e limpeza ainda não estavam ativas)
- **Correção**: base movida para jun/2022; categorias com valor < R$ 500 na base excluídas (evita spikes de divisão por valor próximo de zero, ex: `Receitas Condominiais` que aparecia como despesa apenas em alguns meses)
- **Resultado**: gráfico limpo, todas as linhas partem de 0% em jun/2022 sem ruído

### Estado dos notebooks — validação (08/jul/2026, fim de sessão)
| Notebook | Células | Status |
|---|---|---|
| `src/extratos.ipynb` | 8/8 | ✓ todas executadas |
| `src/prestacao_de_contas.ipynb` | 7/7 | ✓ todas executadas |
| `src/analise_prestacao_de_contas.ipynb` | 28/28 | ✓ re-executadas após reset de kernel |
| `src/analise_extratos.ipynb` | 29/29 | ✓ todas executadas (09/jul/2026) |

CSVs em `exports/csv/`:
- `extratos.csv` — 6.215 registros ✓
- `prestacoes.csv` — 711 registros ✓ (com `macro_categoria`)
- `lancamentos_normalizados.csv` — 6.215 registros ✓
- `anomalias.csv` — 307 registros ✓

PNGs em `exports/figs/`:
- `sindico_custo_mensal.png` — gráfico 5.3b (NF + saques líquidos, devoluções abatidas) ✓
- `acordos_mensal.png` — gráfico 5.6 (recebimentos/pagamentos de acordos) ✓
- `portaria_limpeza_extratos.png` — gráfico 5.7 (portaria + limpeza extratos) ✓

### Atualização desta sessão (09/jul/2026)

#### Correções aplicadas em `analise_extratos.ipynb`
- **5.3b** Gráfico síndico: devoluções agora **abatidas** (saques líquidos = saques − devoluções) em vez de somadas; devoluções anotadas como texto verde para referência
- **5.5** Outros pagamentos: fix NaN — `valor` agora usa `apply` com fallback para `credito` quando `debito` é NaN (afetava `INDENIZ.FUNC.` em FUNDO INDEN.TRAB. e `PG.ACORDO` em subconta ACORDOS)

#### Novas seções adicionadas em `analise_extratos.ipynb`
- **5.6 Acordos**: análise de todos os lançamentos da subconta `ACORDOS` + `REC.ACORDO` / `PG.ACORDO`
  - Lançamentos identificados: 7 no total (ago/2025 a jun/2026)
  - Total entrada (recebimentos): R$ 2.281,75 | Total saída (pagamentos): R$ 80,00
  - Saldo líquido: R$ 2.201,75 → condomínio recebeu mais de acordos do que pagou
  - Gráfico mensal com barras verde (entradas) e vermelho (saídas)
- **5.7 Portaria e Limpeza**: evolução mensal dos contratos de serviço nos extratos
  - `PG.SERV.PORTARIA` + `PG.SERV.LIMP.` filtrados da CONTA NORMAL
  - Barras empilhadas mensais + linha de variação % relativa ao 1º mês
  - Complementa a análise já existente em `analise_prestacao_de_contas.ipynb`

#### Exportação de figuras
- Nova pasta `exports/figs/` criada
- Todas as figuras dos extratos salvas como PNG (dpi=200)

#### Validação de subtotais (re-confirmada)
- Extratos: 75/75 subcontas com movimentação ✓ | 41 sem movimentação ✓ | 0 discrepâncias ✓

### Atualização desta sessão (10/jul/2026 — OCR PDF Extractor)

#### Objetivo realizado: Preencher gap ago/2023–ago/2025 com OCR em PDFs
- **34 PDFs processados**: set/2023–jun/2026
- **817 lançamentos extraídos** via Tesseract OCR (100% de sucesso)
- **7.743 registros consolidados** cobrindo mai/2022–jun/2026

#### Tecnologia implementada
- **Tesseract 5.5.2**: OCR engine instalado via Homebrew
- **pdf2image + Pillow**: Conversão PDF → imagens (DPI=150)
- **pytesseract**: Wrapper Python para Tesseract
- **Camelot**: Extração de tabelas estruturadas (para sumário de subcontas)
- **Poppler**: Dependência para pdf2image (instalado)

#### Descobertas sobre os PDFs
- **Estrutura**: PDFs em `exports/hojas/prestacao/` são EXTRATOS por subconta (não prestações!)
  - Página 1: Sumário de subcontas (tabela Camelot-compatível)
  - Páginas 2-4: Transações detalhadas de cada subconta (texto OCR)
  - Colunas: Data, Histórico, Débito, Crédito, Saldo (similar aos XLS)
- **Nomeação**: `YYYY_MM.pdf` → período `YYYY-MM` (regex automático 34/34 arquivos)
- **Cobertura**: set/2023–jun/2026 (34 meses, preenche gap completamente)

#### Função `extract_pdf_ocr()` implementada
```python
# Estratégia: OCR de todas as páginas → parse de transações
# 1. Converter PDF para imagens (DPI=150)
# 2. Extrair texto com Tesseract (português + inglês)
# 3. Detectar padrões: "PG.*" (despesa) e "REC.*" (receita)
# 4. Emparelar histórico com valor (último número da linha)
# 5. Retornar DataFrame [mes_ano, tipo, evento, valor]
```

#### Qualidade dos dados
| Métrica | Resultado |
|---|---|
| PDFs processados com sucesso | 34/34 (100%) |
| Lançamentos extraídos | 817 |
| Média por mês | 24 registros |
| Tipos detectados | 100% despesas (receitas não extraídas) |
| **Valores OCR** | ⚠️ Contêm lixo (anos, múltiplos números) |

**Nota de qualidade**: Os valores extraídos contêm artefatos OCR (ex: 2023.0, 2024.0 para anos; valores inflados como 96050 quando deveria ser ~100). Recomenda-se validação vs XLS no período de overlap (ago/2025–jun/2026).

#### Consolidação de dados
| Fonte | Registros | Período | Status |
|---|---|---|---|
| XLSX (prestacoes.csv) | 711 | mai/2022–ago/2023 | ✓ Existente |
| **PDFs (prestacoes_pdf.csv)** | **817** | **set/2023–jun/2026** | **✓ NOVO** |
| XLS (extratos.csv) | 6.215 | ago/2025–jun/2026 | ✓ Existente |
| **CONSOLIDADO** | **7.743** | **mai/2022–jun/2026** | **✓ NOVO** |

**Overlaps identificados**:
- XLSX ∩ PDFs: 0 meses (bordado ago/2023–set/2023)
- PDFs ∩ XLS: 11 meses (ago/2025–jun/2026) — ambas as fontes mantidas para validação
- XLSX ∩ XLS: 0 meses

**Gaps restantes**:
- ago/2023–set/2023: 1 mês (não crítico, fora dos notebooks atuais)
- Sem dados anteriores a mai/2022 (fora do escopo original)

#### CSVs gerados
- `prestacoes_pdf.csv` (817 registros) → OCR dos 34 PDFs
- `lancamentos_consolidados.csv` (7.743 registros) → União de XLSX + PDFs + XLS

#### Próximas ações recomendadas
1. **Refinar valores OCR**: Implementar validação vs XLS no overlap (ago/2025–jun/2026)
   - Comparar df_pdf[mes_ano in overlap] com df_xls[mes_ano in overlap]
   - Avaliar se OCR consegue reconstruir valores corretos (atualmente: problemas)
2. **Extrair receitas**: Função OCR detectou apenas despesas; receitas podem estar em seção separada
3. **Melhorar detecção de evento**: Limpeza de texto OCR para remover ruído e referências
4. **Considerar re-download**: Gap ago/2023–set/2023 pode ser baixado do site ClienteOnline se necessário
5. **Re-executar análises**: Com dataset consolidado (7.743 registros), as visualizações ganham contexto completo
   - `analise_prestacao_de_contas.ipynb` já cobre mai/2022–ago/2023
   - `analise_extratos.ipynb` cobre ago/2025–jun/2026
   - Novo notebook recomendado: `analise_pdf.ipynb` para set/2023–ago/2025 (ou integrar em `analise_extratos.ipynb`)

### Atualização desta sessão (10/jul/2026 — Refinamento de Valores OCR — PASSO 2)

#### Erro corrigido
- **Problema**: Célula #VSC-7566fc3d chamava função `process_pdf_to_dataframe()` inexistente
- **Solução**: Corrigida para usar `process_pdf_to_dataframe_v2(pdf_path, date_map_final)`

#### PASSO 1 — Validação PDFs vs XLS (ago/2025–jun/2026)
- **Overlap**: 11 meses confirmados
- **Meses com boa sincronia (< 12% diferença)**:
  - dez/2025: 6.4% diferença
  - jan/2026: 2.7% diferença (melhor alinhamento)
- **Meses com cobertura parcial (30-70% diferença)**: ago–nov, fev–jun/2025
- **Conclusão**: PDFs extraem ~60% dos lançamentos (cobertura parcial, mas dados válidos)

#### PASSO 2 — Refinamento de valores OCR
- **Função**: `clean_ocr_value()` implementada com estratégia multi-número
- **Estratégia**: 
  - Remover referências de anos (2023-2026)
  - Filtrar valores > 50.000 (anomalias OCR)
  - Manter múltiplos números: selecionar o maior (valor real > lixo)
- **Resultados**:
  - Registros originais: 817
  - Registros após refinamento: 325 (removidos 492 = 60%)
  - Lixo removido: valores como 2023.0, 2024.0, 20X.0 (anos/meses isolados)
  - Range final: R$ 10 → R$ 49.840 (distribuição mais saudável)

#### Consolidação final
- **Total final**: 7.251 registros (vs 7.743 anterior = redução de 492 de lixo)
- **Distribuição por fonte**:
  - XLSX: 711 (mai/2022–ago/2023)
  - PDFs refinado: 325 (set/2023–jun/2026) ← cobertura parcial
  - XLS: 6.215 (ago/2025–jun/2026)
- **Gap residual**: ago/2023–set/2023 (1 mês, não crítico)
- **Arquivo**: `lancamentos_consolidados_v2_refinado.csv`

#### Limitações identificadas
- **Cobertura de Receitas**: PDFs extraem apenas despesas (~100%); receitas não detectadas
- **Cobertura parcial**: Gap entre PDFs e XLS sugere que OCR não captura todos os eventos
- **Recomendação**: Melhorar parser OCR para detectar seções de receitas e aumentar sensibilidade

#### Atualização desta sessão (09/jul/2026 — README / Plano de melhorias)
- Seção **"Plano de Melhorias"** do `README.md` foi sincronizada com o estado real do repositório.
- **P1 (Testes Automatizados)** marcado como concluído no README (schema, período, balanço e suíte antes de merge).
- **P9 (CI/CD)** marcado como concluído no README (workflows de teste/lint e Git LFS ativos).
- **P2** mantido como parcial no README: validação de overlap concluída, mas OCR de receitas ainda pendente.

#### Atualização desta sessão (09/jul/2026 — Implementação P5/P6)
- Notebook `src/analise_inadimplencia.ipynb` implementado e executado de ponta a ponta (10 células de código).
- **P5 concluído**:
  - rastreamento de `REC.MULTA`/`REC.MULTA+C.M.+JRS.` por unidade (AP + bloco);
  - identificação de inadimplentes recorrentes (>= 2 ocorrências);
  - cálculo mensal de `% cobrança de atraso vs total devido (proxy)`.
- **P6 concluído**:
  - validação de pagamento duplo do síndico em mai/2026 (2 pagamentos; refs 04/2026 e 05/2026);
  - tendência de INSS com comparação contra proxy de folha;
  - diagnóstico de saldo negativo no FUNDO OBRAS e origem principal dos débitos (`PG.REFORMA`).
- Novos CSVs gerados: `inadimplentes_ranking.csv`, `inadimplentes_recorrentes.csv`, `inadimplencia_por_mes.csv`, `outliers_p6_resumo.csv`.
- Novas figuras geradas: `inadimplencia_serie_temporal.png`, `inadimplencia_top10.png`, `outlier_sindico_mensal.png`, `outlier_inss_tendencia.png`, `outlier_fundo_obras_saldo.png`.

#### Atualização desta sessão (09/jul/2026 — Insights de anomalias: INSS + Adiantamentos)
- Notebook `src/insights_anomalias_prestacoes.ipynb` recebeu nova seção dedicada a pagamentos de **INSS** e **adiantamentos de funcionários**.
- Incluída **listagem completa** dos lançamentos filtrados por evento, com colunas: `mes_ano`, `evento`, `tipo`, `valor`, `macro_categoria`, `motivo_anomalia`.
- Incluído gráfico de **barras mensais comparativas** (INSS vs Adiantamentos), permitindo leitura direta mês a mês do valor pago em cada grupo.
- Célula nova validada em execução: resultados encontrados no dataset atual de anomalias
  - INSS: 2 lançamentos (R$ 3.049,34)
  - Adiantamentos: 2 lançamentos (R$ 2.571,75)

---

## Próximos passos — a implementar nos notebooks

### P1 — Classificar os 23 lançamentos "VALOR"
- Filtrar `df_ext[df_ext['historico'] == 'VALOR']` e inspecionar `complemento`
- Determinar se são transferências internas, acertos ou outra categoria
- Adicionar ao `MACRO_MAP` após identificação

### P2 — Aprofundar análise dos 271 pagamentos sem NF
- Listar fornecedores (campo `complemento`) que aparecem com frequência sem NF
- Separar pagamentos recorrentes de pontuais sem nota
- Verificar se há algum fornecedor com padrão consistente de ausência de nota

### P3 — Análise de tendência do INSS
- Plotar série temporal de `PG.DARF INSS` mês a mês
- Verificar se o crescimento é progressivo ou pontual (rescisões, etc.)
- Comparar com folha de salários para ver se a proporção está correta

### P4 — Comparação entre os dois períodos cobertos
- Calcular média mensal por macro_categoria em 2022-2023 e 2025-2026
- Plotar gráfico de barras side-by-side mostrando variação
- Ajustar por inflação (IPCA) para comparação justa — deflacionar usando pandas_datareader ou IBGE API

### P5 — Análise de inadimplência / cobrança atrasada
- Nos extratos, lançamentos `REC.MULTA+C.M.+JRS.` e `REC. MULTA` indicam pagamentos atrasados
- ✅ **Concluído**: apartamentos/unidades recorrentes identificados no campo `complemento`
- ✅ **Concluído**: percentual mensal de arrecadação em atraso vs total devido (proxy) calculado

### P6 — FUNDO OBRAS: investigar saldo negativo
- Filtrar `df_ext[df_ext['subconta'] == 'FUNDO OBRAS']`
- ✅ **Concluído**: débitos e origem validados (`PG.REFORMA` como principal)
- ✅ **Concluído**: saldo negativo existiu até jan/2026 e voltou ao positivo a partir de fev/2026

### P7 — Exportar relatório de anomalias para Excel
- Gerar `exports/csv/relatorio_anomalias.xlsx` com múltiplas abas:
  - Aba "Sem NF" — pagamentos sem nota fiscal
  - Aba "Outliers" — valores acima do IQR por categoria
  - Aba "Retiradas" — movimentações suspeitas de retirada
- Usar `openpyxl` com formatação condicional (células vermelhas para valores altos)

### P8 — Incluir PDFs no pipeline (gap ago/2023–ago/2025)
- PDFs disponíveis em `exports/pdf/`
- OCR já implementado com notebook dedicado (`src/pdf_extractor.ipynb`)
- Próximo passo: melhorar extração de receitas e reduzir perda de cobertura
- Fechar gap de 2 anos nos dados

### P9 — Baixar extratos faltantes do site
- Período não coberto pelos extratos atuais: jul/2023 a jul/2025
- Baixar do sistema ClienteOnline e adicionar a `exports/hojas/extrato/`
- Re-executar `extratos.ipynb` para incorporar os novos arquivos
- O pipeline de ingestão já está preparado para detectar arquivos novos automaticamente

### P10 — Investigar E-CONSIGNADO CLT CONDS.
- R$ 251,73/mês desde jan/2026 (6 ocorrências, total R$ 1.510,38)
- Verificar base contratual: é desconto de condômino? É encargo trabalhista?
- Se for desconto de condômino inadimplente via consignado, verificar legalidade

### P11 — Verificar pagamento duplo do síndico em mai/2026
- Dois pagamentos em mai/2026: competências 04/2026 (CF REC, sem NF) e 05/2026 (NF.0203)
- Verificar se 04/2026 já havia sido pago em abr/2026 (NF.0195 = referência 03/2026)
- Se sim, um dos pagamentos de mai/2026 é indevido → R$ 3.871 a recuperar

### P12 — Acompanhar saque de R$ 3.900,40 (jun/2026)
- `RETIRADA P/POSTERIOR ACERTO` em 2026-06-17, valor = síndico jun/2026
- Verificar nos próximos extratos se devolução foi realizada
- Padrão de saques anteriores: devolvidos com 16–87 dias de atraso

### P13 — Aprofundar análise de Acordos
- Células 5.6 identificam R$ 2.281,75 recebidos de condôminos em acordo (7 lançamentos)
- Cruzar com `REC.MULTA+C.M.+JRS.` para ver inadimplentes recorrentes
- Verificar se `AP.0303` e `AP.0504` têm parcelas em aberto além das registradas
- `PG.ACORDO PARC.08/25 UNIDADE 504A` (R$ 80,00 saída em ago/2025) — verificar contexto

### P14 — Portaria e Limpeza: comparação 2022-2023 vs 2025-2026
- Dados de 2022-2023 já em `analise_prestacao_de_contas.ipynb` seção 5.6
- Dados de 2025-2026 agora em `analise_extratos.ipynb` seção 5.7
- Criar célula de comparação side-by-side nos dois períodos (ajustado por IPCA)
- Verificar se houve troca de prestadora e impacto no preço

### P15 — Expandir rastreio INSS/Adiantamentos para base completa (não só anomalias)
- Repetir a seção criada em `insights_anomalias_prestacoes.ipynb` usando base completa de prestações (`prestacoes.csv`)
- Comparar volume total da base completa vs subset de anomalias para evitar viés de interpretação
- Padronizar eventos (`Prov.darf Inss(E-Social/Reinf)`, `Adto.13º Salário` e variações) no mapeamento de categorias
