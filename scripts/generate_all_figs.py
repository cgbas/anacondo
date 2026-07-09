import warnings
warnings.filterwarnings('ignore')
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from matplotlib.patches import Patch
from PIL import Image

sns.set_theme(style="whitegrid", palette="tab10")
plt.rcParams.update({"figure.dpi": 120})

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / 'exports' / 'csv'
OUT_DIR = ROOT / 'exports' / 'figs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load data
df_ext = pd.read_csv(CSV_DIR / 'extratos.csv', parse_dates=['data'])
try:
    df_prest = pd.read_csv(CSV_DIR / 'prestacoes.csv')
except Exception:
    df_prest = pd.read_csv(CSV_DIR / 'prestacoes.csv', encoding='latin-1')

# Ensure mes_ano ordering
if 'mes_ano' not in df_ext.columns:
    df_ext['mes_ano'] = df_ext['data'].dt.to_period('M').astype(str)

# 1) Despesas mensais por macro-categoria (stacked)
despesas_ext = (
    df_ext[(df_ext['subconta'] == 'CONTA NORMAL') & df_ext['debito'].notna()]
    .groupby(['mes_ano', 'macro_categoria'])['debito'].sum().abs().reset_index()
)
pivot = despesas_ext.pivot(index='mes_ano', columns='macro_categoria', values='debito').fillna(0)
fig, ax = plt.subplots(figsize=(16,6))
pivot.plot(kind='bar', stacked=True, ax=ax, colormap='tab10')
ax.set_title('Despesas mensais por macro-categoria (Extratos — ago/2025–jun/2026)')
ax.set_ylabel('R$')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'R$ {x:,.0f}'))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
fig.savefig(OUT_DIR / 'despesas_mensais_por_macro_categoria.png')
plt.close(fig)

# 2) Total acumulado por macro-categoria (horizontal)
total_por_cat = (
    df_ext[(df_ext['subconta'] == 'CONTA NORMAL') & df_ext['debito'].notna()]
    .groupby('macro_categoria')['debito'].sum().abs().sort_values()
)
fig, ax = plt.subplots(figsize=(10,6))
bars = ax.barh(total_por_cat.index, total_por_cat.values)
for bar, val in zip(bars, total_por_cat.values):
    ax.text(bar.get_width() + total_por_cat.max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"R$ {val:,.0f}", va='center', fontsize=9)
ax.set_title('Total acumulado por macro-categoria — Extratos')
ax.set_xlabel('R$')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'R$ {x:,.0f}'))
plt.tight_layout()
fig.savefig(OUT_DIR / 'total_acumulado_por_macro_categoria.png')
plt.close(fig)

# 3) Evolução do saldo — CONTA NORMAL
saldo_normal = (
    df_ext[df_ext['subconta'] == 'CONTA NORMAL']
    .sort_values('data')
    .drop_duplicates(subset=['data'], keep='last')
)
fig, ax = plt.subplots(figsize=(16,5))
ax.fill_between(saldo_normal['data'], saldo_normal['saldo'], alpha=0.3, color='steelblue')
ax.plot(saldo_normal['data'], saldo_normal['saldo'], color='steelblue', linewidth=1)
ax.axhline(0, color='red', linewidth=0.8, linestyle='--')
ax.set_title('Evolução do saldo — CONTA NORMAL')
ax.set_ylabel('Saldo (R$)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'R$ {x:,.0f}'))
plt.tight_layout()
fig.savefig(OUT_DIR / 'saldo_conta_normal.png')
plt.close(fig)

# 4) Síndico — custo mensal (reproduce recon logic)
sind_ext = df_ext[df_ext['historico'].str.upper().str.contains('SÍNDICO|SINDICO', na=False) & (df_ext['subconta'] == 'CONTA NORMAL')].copy()
sind_ext['valor_abs'] = sind_ext['debito'].abs()
if 'complemento' in sind_ext.columns:
    sind_ext['ref_competencia'] = sind_ext['complemento'].str.extract(r'(\d{2}/20\d{2})', expand=False)

saques_base = df_ext[df_ext['subconta'].eq('SAQUES P/ACERTO')].copy()
saques_base['debito_abs'] = saques_base['debito'].abs()

sind_nf_m = sind_ext.groupby('mes_ano')['valor_abs'].sum()
saques_m = saques_base.groupby('mes_ano')['debito_abs'].sum()
devol_m = saques_base.groupby('mes_ano')['credito'].sum()
recon = pd.DataFrame(index=sorted(set(sind_nf_m.index) | set(saques_m.index) | set(devol_m.index)))
recon['nf_apenas'] = sind_nf_m.reindex(recon.index).fillna(0.0)
recon['saques'] = saques_m.reindex(recon.index).fillna(0.0)
recon['devolucoes'] = devol_m.reindex(recon.index).fillna(0.0)
recon['nf_mais_saques_menos_devol'] = recon['nf_apenas'] + recon['saques'] - recon['devolucoes']

fig, ax = plt.subplots(figsize=(13,5))
meses = recon.index.tolist()
x = range(len(meses))
net_saques = recon['saques'] - recon['devolucoes']
ax.bar(x, recon['nf_apenas'], label='NF síndico', color='#2a7ab5', zorder=3)
ax.bar(x, net_saques, bottom=recon['nf_apenas'], label='Saque p/acerto (líquido)', color='#f0a500', zorder=3)
ax.plot(x, recon['nf_mais_saques_menos_devol'], color='#c62828', marker='o', linewidth=2, zorder=4, label='Custo líquido (NF+saques−devol.)')
ax.set_xticks(x)
ax.set_xticklabels(meses, rotation=45, ha='right')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'R$ {v:,.0f}'))
ax.set_title('Custo mensal com síndico — NF + saques (devoluções abatidas)')
ax.legend()
plt.tight_layout()
fig.savefig(OUT_DIR / 'sindico_custo_mensal.png')
plt.close(fig)

# 5) Prestações — timeline e portaria+limpeza
# Prepare prestacoes dataframe
if 'mes_ano' not in df_prest.columns:
    df_prest['mes_ano'] = df_prest['mes'].astype(str) if 'mes' in df_prest.columns else df_prest.get('mes_ano', pd.Series(dtype=str))

# Sindico timeline (from prestaÃ§Ãµes)
sind_prest = df_prest[df_prest['evento'].str.upper().str.contains('SÍNDICO|SINDICO', na=False)].copy()
if not sind_prest.empty:
    sind_prest_m = sind_prest.groupby('mes_ano')['valor'].sum().reset_index().sort_values('mes_ano')
    fig, ax = plt.subplots(figsize=(12,3))
    ax.bar(sind_prest_m['mes_ano'], sind_prest_m['valor'], color='#e07b39')
    ax.set_title('Síndico — prestações (timeline)')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'R$ {v:,.0f}'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'prestacoes_sindico_timeline.png')
    plt.close(fig)

# Portaria + limpeza
filt_port = df_prest['evento'].str.upper().str.contains('PG.SERV.PORTARIA|PG.SERV.LIMP|PG.SERV.LIMP\.', na=False)
port_df = df_prest[filt_port].copy()
if not port_df.empty:
    port_sum = port_df.groupby('evento')['valor'].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8,4))
    port_sum.plot(kind='bar', ax=ax)
    ax.set_title('Portaria + Limpeza — Prestações')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'R$ {v:,.0f}'))
    plt.tight_layout()
    fig.savefig(OUT_DIR / 'prestacoes_portaria_limpeza.png')
    plt.close(fig)

# Create PDF with all PNGs
pngs = sorted(OUT_DIR.glob('*.png'))
if pngs:
    imgs = [Image.open(p).convert('RGB') for p in pngs]
    out_pdf = OUT_DIR / 'relatorio_visualizacoes.pdf'
    imgs[0].save(out_pdf, save_all=True, append_images=imgs[1:], quality=85)
    print('✓ PDF gerado:', out_pdf)
else:
    print('Nenhuma figura encontrada para gerar o PDF')

print('✓ Todas as figuras geradas em', OUT_DIR)
