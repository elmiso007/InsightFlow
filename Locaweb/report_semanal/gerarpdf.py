from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import os
import re
import markdown
from pathlib import Path
import matplotlib.pyplot as plt
import tempfile
import numpy as np
import shutil
from matplotlib.ticker import FuncFormatter

sql_path = Path(__file__).parent 

VERDE = "#2ECC71"
VERMELHO = "#E74C3C"
ROXO = "#7D3C98"
COR_SEMANA_ANTERIOR = "#2b343c"
COR_SEMANA_ATUAL = "#e74c3c"

def _to_seconds(v):
    if isinstance(v, str):
        try:
            h, m, s = map(int, v.split(':'))
            return h*3600 + m*60 + s
        except Exception:
            return 0
    try:
        return int(v)
    except Exception:
        return 0

def _mmss(seg):  # 00:00 (valor absoluto)
    seg = int(seg)
    m = abs(seg) // 60
    s = abs(seg) % 60
    return f"{m:02d}:{s:02d}"

def _signed_mmss(seg):  # +MM:SS / -MM:SS
    sign = '+' if seg >= 0 else '-'
    return f"{sign}{_mmss(seg)}"

def _fmt_mmss_ticks(x, pos):  # formatter do eixo Y
    x = 0 if np.isnan(x) else int(x)
    return _mmss(x)

def criar_grafico_combinado_metricas(df_atual, df_anterior, temp_dir):
    """
    - grafico_contatos_variacao.png: barras comparativas + variação % (seta + cor)
    - grafico_tme_meta.png: linha TME (pontos e eixo em MM:SS), meta 03:00 e delta em ±MM:SS (seta + cor)
    """
    try:
        plt.style.use('default')

        if df_atual is None or df_anterior is None or df_atual.empty or df_anterior.empty:
            return []

        graficos_paths = []

        # ---- Métricas
        recebidos_atual    = df_atual.get('Recebidos',   [0]).iloc[0]
        recebidos_anterior = df_anterior.get('Recebidos',[0]).iloc[0]
        abandonos_atual    = df_atual.get('Abandonos',   [0]).iloc[0]
        abandonos_anterior = df_anterior.get('Abandonos',[0]).iloc[0]

        tme_atual    = _to_seconds(df_atual.get('TME',    [0]).iloc[0])
        tme_anterior = _to_seconds(df_anterior.get('TME', [0]).iloc[0])

        # ==============
        # Gráfico 1 — Barras
        # ==============
        fig1, ax1 = plt.subplots(figsize=(10, 6))

        categorias = ['Recebidos', 'Abandonos']
        valores_anterior = [recebidos_anterior, abandonos_anterior]
        valores_atual    = [recebidos_atual,    abandonos_atual]

        x = np.arange(len(categorias))
        width = 0.35

        b1 = ax1.bar(x - width/2, valores_anterior, width, label='Semana Anterior', color=COR_SEMANA_ANTERIOR, alpha=0.9)
        b2 = ax1.bar(x + width/2, valores_atual,    width, label='Semana Atual',   color=COR_SEMANA_ATUAL, alpha=0.9)

        for i, (va, vt, bar_a, bar_t) in enumerate(zip(valores_anterior, valores_atual, b1, b2)):
            # valores absolutos nas barras
            ax1.text(bar_a.get_x()+bar_a.get_width()/2, va, f'{int(va)}', ha='center', va='bottom', fontsize=10)
            ax1.text(bar_t.get_x()+bar_t.get_width()/2, vt, f'{int(vt)}', ha='center', va='bottom', fontsize=10)

            # variação % + seta + cor (queda = verde; alta = vermelho)
            if va != 0:
                delta = vt - va
                pct = delta / va * 100
                cor  = VERDE if delta < 0 else VERMELHO if delta > 0 else "#7f8c8d"
                seta = '↓' if delta < 0 else '↑' if delta > 0 else '→'
                ymax = max(va, vt)
                ax1.annotate(f'{seta} {pct:+.1f}%',
                             xy=(x[i], ymax),
                             xytext=(x[i], ymax + max(50, ymax*0.02)),
                             ha='center', va='bottom', fontsize=11, fontweight='bold', color=cor)
            else:
                ax1.text(x[i], max(va, vt) + 50, 'N/A', ha='center', va='bottom', fontsize=11, fontweight='bold')

        ax1.set_title('Contatos Recebidos x Abandonos:', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Contatos', fontweight='bold')
        ax1.set_xticks(x); ax1.set_xticklabels(categorias)
        ax1.legend(loc='upper right')
        ax1.grid(False)  # sem grid

        path_contatos = os.path.join(temp_dir, 'grafico_contatos_variacao.png')
        plt.tight_layout(); plt.savefig(path_contatos, dpi=300, bbox_inches='tight', facecolor='white'); plt.close()
        graficos_paths.append(path_contatos)

        # ==============
        # Gráfico 2 — TME
        # ==============
        if tme_atual > 0 or tme_anterior > 0:
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            semanas = ['Semana Anterior', 'Semana Atual']
            valores = [tme_anterior, tme_atual]

            ax2.plot(semanas, valores, marker='o', linewidth=3, markersize=9, color=ROXO, label='TME')

            # eixo y em MM:SS
            ax2.yaxis.set_major_formatter(FuncFormatter(_fmt_mmss_ticks))

            # meta 03:00
            meta_tme = 180
            ax2.axhline(meta_tme, color='gray', linestyle='--', linewidth=1)
            ax2.text(1.03, meta_tme, 'Meta 03:00', color='gray', va='center')

            # rótulos dos pontos (MM:SS)
            for i, v in enumerate(valores):
                ax2.annotate(_mmss(v), (i, v), xytext=(0, 12),
                             textcoords='offset points', ha='center', va='bottom',
                             fontsize=11, fontweight='bold')

            # delta em ±MM:SS (negativo=verde / positivo=vermelho)
            delta = tme_atual - tme_anterior
            altura_delta = (tme_atual + tme_anterior) / 2
            cor_delta = VERDE if delta < 0 else VERMELHO if delta > 0 else "#7f8c8d"
            seta = '↓' if delta < 0 else '↑' if delta > 0 else '→'
            ax2.annotate(f'{seta} {_signed_mmss(delta)}', xy=(0.5, altura_delta + 5), xytext=(0.5, altura_delta + 15),
                         ha='center', fontsize=10, color=cor_delta)

            ax2.set_title('Tempo Médio de Espera (TME):', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Tempo (MM:SS)', fontweight='bold')  # atualizado
            ax2.legend(loc='upper right')
            ax2.grid(False)

            ymin = min(valores + [meta_tme]) - 20
            ymax = max(valores + [meta_tme]) + 20
            ax2.set_ylim(ymin, ymax)

            path_tme = os.path.join(temp_dir, 'grafico_tme_meta.png')
            plt.tight_layout(); plt.savefig(path_tme, dpi=300, bbox_inches='tight', facecolor='white'); plt.close()
            graficos_paths.append(path_tme)

        return graficos_paths

    except Exception as e:
        plt.close('all')
        print(f"Erro ao criar gráfico combinado de métricas: {e}")
        return []

def criar_grafico_equipes_tme_series(metricas_equipes, metricas_equipes_sm, temp_dir):
    """
    Um único gráfico de linhas (séries) mostrando TME por equipe
    comparando Semana Anterior x Semana Atual.
    - Cada equipe = 1 série
    - Eixo Y em MM:SS
    - Sem grid; legenda com as equipes
    """
    try:
        if (metricas_equipes is None or metricas_equipes.empty or
            metricas_equipes_sm is None or metricas_equipes_sm.empty):
            return []

        # Harmonizar equipes (interseção)
        eq_atual = set(metricas_equipes['Equipe'].dropna().astype(str))
        eq_ant   = set(metricas_equipes_sm['Equipe'].dropna().astype(str))
        equipes  = sorted(eq_atual.intersection(eq_ant))
        if not equipes:
            return []

        # Preparar dados
        x = [0, 1]
        labels_x = ['Semana Anterior', 'Semana Atual']

        fig, ax = plt.subplots(figsize=(12, 7))

        for i, equipe in enumerate(equipes):
            row_ant = metricas_equipes_sm[metricas_equipes_sm['Equipe'].astype(str) == equipe].iloc[0]
            row_at  = metricas_equipes[metricas_equipes['Equipe'].astype(str) == equipe].iloc[0]

            tme_ant = _to_seconds(row_ant['TME'])
            tme_at  = _to_seconds(row_at['TME'])

            ax.plot(x, [tme_ant, tme_at], marker='o', linewidth=2.5, markersize=8, label=str(equipe))

            # Rótulo discreto acima de cada ponto
            for xi, yi in zip(x, [tme_ant, tme_at]):
                ax.annotate(_mmss(yi), (xi, yi), xytext=(0, 10),
                            textcoords='offset points', ha='center', va='bottom', fontsize=9)

        # Eixo Y como MM:SS
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_mmss_ticks))

        # Meta TME (ex.: 03:00)
        meta_tme = 180
        ax.axhline(meta_tme, color='gray', linestyle='--', linewidth=1)
        ax.text(1.03, meta_tme, 'Meta 03:00', color='gray', va='center')

        ax.set_xticks(x); ax.set_xticklabels(labels_x)
        ax.set_ylabel('Tempo (MM:SS)', fontweight='bold')
        ax.set_title('TME por Equipe — Semana Anterior x Semana Atual', fontsize=14, fontweight='bold')
        ax.legend(loc='best', ncol=2, fontsize=8)
        ax.grid(False)

        # Margem vertical
        ymin = 0
        ymax = max(meta_tme, *( _to_seconds(v) for v in metricas_equipes['TME'] ), *( _to_seconds(v) for v in metricas_equipes_sm['TME'] ))
        ax.set_ylim(max(0, ymin), ymax + 15)

        path = os.path.join(temp_dir, 'grafico_equipes_tme_series.png')
        plt.tight_layout(); plt.savefig(path, dpi=300, bbox_inches='tight', facecolor='white'); plt.close()
        return [path]
    except Exception as e:
        plt.close('all')
        print(f"Erro ao criar gráfico consolidado de TME por equipe: {e}")
        return []

def _consolida_valores_por_equipe(metricas_equipes, metricas_equipes_sm, coluna):
    """Retorna listas alinhadas de equipes, valores semana anterior e semana atual para uma coluna."""
    # Interseção de equipes
    eq_atual = set(metricas_equipes['Equipe'].dropna().astype(str))
    eq_ant   = set(metricas_equipes_sm['Equipe'].dropna().astype(str))
    equipes  = sorted(eq_atual.intersection(eq_ant), reverse=True)
    if not equipes:
        return [], [], [], []

    vals_ant, vals_at = [], []
    for equipe in equipes:
        row_ant = metricas_equipes_sm[metricas_equipes_sm['Equipe'].astype(str) == equipe].iloc[0]
        row_at  = metricas_equipes[metricas_equipes['Equipe'].astype(str) == equipe].iloc[0]

        v_ant = float(row_ant[coluna]) if str(row_ant[coluna]).strip() not in ('', 'None') else 0
        v_at  = float(row_at[coluna])  if str(row_at[coluna]).strip() not in ('', 'None') else 0
        vals_ant.append(v_ant)
        vals_at.append(v_at)

    # Mantém ordem alfabética reversa das equipes (Z-A)
    return equipes, vals_ant, vals_at, []

def criar_grafico_equipes_barras(metricas_equipes, metricas_equipes_sm, temp_dir, coluna, titulo):
    """
    Consolidado por equipe para 'coluna' (Recebidos/Abandonos), comparando Semana Anterior x Semana Atual.
    Evita sobreposição entre o rótulo do valor e o rótulo de delta usando offsets dinâmicos e jitter horizontal.
    """
    try:
        if (metricas_equipes is None or metricas_equipes.empty or
            metricas_equipes_sm is None or metricas_equipes_sm.empty):
            return []

        equipes, vals_ant, vals_at, _ = _consolida_valores_por_equipe(metricas_equipes, metricas_equipes_sm, coluna)
        if not equipes:
            return []

        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(equipes))
        width = 0.4

        b1 = ax.bar(x - width/2, vals_ant, width, label='Semana Anterior', color=COR_SEMANA_ANTERIOR, alpha=0.9)
        b2 = ax.bar(x + width/2, vals_at,  width, label='Semana Atual',   color=COR_SEMANA_ATUAL, alpha=0.9)

        # --- headroom no topo para acomodar rótulos/setas
        ymax = max([*vals_ant, *vals_at]) if (vals_ant or vals_at) else 1
        pad_top = max(24, ymax * 0.25)
        ax.set_ylim(0, ymax + pad_top)

        # --- threshold para "barra pequena" (proporcional à escala visível)
        threshold_small = (ymax + pad_top) * 0.08  # 8% da escala visível

        # Adicionar rótulos para ambas as barras
        for i, (va, vt, bar_a, bar_t) in enumerate(zip(vals_ant, vals_at, b1, b2)):
            x_center_ant = bar_a.get_x() + bar_a.get_width()/2
            value_offset_pts = 6
            ax.annotate(f'{int(va)}',
                        xy=(x_center_ant, va),
                        xytext=(0, value_offset_pts), textcoords='offset points',
                        ha='center', va='bottom', fontsize=9,
                        clip_on=False)
            
            # Rótulo para barra semana atual
            x_center = bar_t.get_x() + bar_t.get_width()/2
            small = vt <= threshold_small
            ax.annotate(f'{int(vt)}',
                        xy=(x_center, vt),
                        xytext=(0, value_offset_pts), textcoords='offset points',
                        ha='center', va='bottom', fontsize=9,
                        clip_on=False)

            # ---------- RÓTULO DO DELTA (offset dinâmico + jitter horizontal p/ barras pequenas) ----------
            if va != 0:
                delta = vt - va
                pct = (delta / va) * 100
                cor  = VERDE if delta < 0 else VERMELHO if delta > 0 else "#7f8c8d"
                seta = '↓' if delta < 0 else '↑' if delta > 0 else '→'

                y_anchor = max(vt, va)
                delta_offset_pts = 30 if not small else 38   # sobe mais se a barra for pequena
                x_jitter_pts = 0 if not small else (-1 if (i % 2 == 0) else 1)  # leve deslocamento lateral alternado

                ax.annotate(f'{seta} {pct:+.1f}%',
                            xy=(x_center, y_anchor),
                            xytext=(x_jitter_pts, delta_offset_pts), textcoords='offset points',
                            ha='center', va='bottom', fontsize=9, color=cor,
                            bbox=dict(facecolor='white', alpha=0.85, pad=0.5, linewidth=0),  # melhora legibilidade
                            clip_on=False)
            else:
                ax.annotate('N/A',
                            xy=(x_center, vt),
                            xytext=(0, 24), textcoords='offset points',
                            ha='center', va='bottom', fontsize=9, color="#7f8c8d",
                            bbox=dict(facecolor='white', alpha=0.85, pad=0.5, linewidth=0),
                            clip_on=False)

        ax.set_title(titulo, fontsize=14, fontweight='bold')
        #ax.set_ylabel('Quantidade', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(equipes, rotation=20, ha='right')
        ax.legend(loc='best')
        ax.grid(False)

        fname = f"grafico_equipes_{coluna.lower()}.png"
        path = os.path.join(temp_dir, fname)
        plt.tight_layout(); plt.savefig(path, dpi=300, bbox_inches='tight', facecolor='white'); plt.close()
        return [path]

    except Exception as e:
        plt.close('all')
        print(f"Erro ao criar gráfico consolidado por equipe ({coluna}): {e}")
        return []

def criar_grafico_nps_linha(df_nps_atual, df_nps_anterior, temp_dir, setor):
    """
    NPS por 'Pesquisa' comparando Semana Anterior x Semana Atual.
    - Valores exibidos levemente abaixo dos pontos.
    - Delta no ponto final com seta + cor (melhora=verde, piora=vermelho).
    - Linha de meta 80. Sem grid.
    """
    try:
        if (df_nps_atual is None or df_nps_atual.empty) and (df_nps_anterior is None or df_nps_anterior.empty):
            return []

        plt.style.use('default')

        # Pesquisas
        pesquisas = []
        if df_nps_atual is not None and not df_nps_atual.empty:
            pesquisas = list(df_nps_atual['Pesquisa'])
        if not pesquisas and df_nps_anterior is not None and not df_nps_anterior.empty:
            pesquisas = list(df_nps_anterior['Pesquisa'])
        if not pesquisas:
            return []

        # Pares (anterior, atual)
        nps_ant, nps_atu = [], []
        for p in pesquisas:
            nps_ant.append(int(df_nps_anterior[df_nps_anterior['Pesquisa'] == p]['NPS'].iloc[0])
                           if (df_nps_anterior is not None and not df_nps_anterior.empty and
                               p in df_nps_anterior['Pesquisa'].values) else 0)
            nps_atu.append(int(df_nps_atual[df_nps_atual['Pesquisa'] == p]['NPS'].iloc[0])
                           if (df_nps_atual is not None and not df_nps_atual.empty and
                               p in df_nps_atual['Pesquisa'].values) else 0)

        fig, ax = plt.subplots(figsize=(12, 7))
        x = [0, 1]
        semanas = ['Semana Anterior', 'Semana Atual']
        cores = ['#3498DB', '#E67E22', '#2ECC71']

        for i, p in enumerate(pesquisas):
            vals = [nps_ant[i], nps_atu[i]]
            cor_linha = cores[i % len(cores)]

            ax.plot(x, vals, marker='o', linewidth=3, markersize=9, color=cor_linha, label=p)

            # rótulos abaixo dos pontos (para não colidir com o delta)
            for xi, yi in zip(x, vals):
                ax.annotate(f'{int(yi)}', (xi, yi), xytext=(0, -10),
                            textcoords='offset points', ha='center', va='top',
                            fontsize=10, color=cor_linha)

            # delta no ponto final (verde melhora / vermelho piora)
            delta = nps_atu[i] - nps_ant[i]
            cor_delta = VERDE if delta > 0 else VERMELHO if delta < 0 else "#7f8c8d"
            seta = '↑' if delta > 0 else '↓' if delta < 0 else '→'
            ax.annotate(f'{seta} {delta:+.0f}', xy=(1, vals[1]), xytext=(1, vals[1] + 2),
                        ha='center', fontsize=10, color=cor_delta)

        # Meta 70
        ax.axhline(70, color='gray', linestyle='--', linewidth=1)
        ax.text(1.03, 70, 'Meta 70', color='gray', va='center')

        ax.set_xticks(x); ax.set_xticklabels(semanas)
        ax.set_ylabel('Score NPS', fontweight='bold')
        ax.set_title('NPS - Evolução Semanal:', fontsize=14, fontweight='bold')
        ax.legend(loc='lower right')
        ax.grid(False)
        if setor == 'Suporte':
            ax.set_ylim(40, 95)
        else:
            ax.set_ylim(20, 95)

        path_nps = os.path.join(temp_dir, 'grafico_nps_linha.png')
        plt.tight_layout(); plt.savefig(path_nps, dpi=300, bbox_inches='tight', facecolor='white'); plt.close()

        return [path_nps]

    except Exception as e:
        plt.close('all')
        print(f"Erro ao criar gráfico NPS: {e}")
        return []

def criar_dataframe_woz(analise_woz):
    import pandas as pd
    
    # Mapeamento de nomes mais legíveis
    nomes_legivel = {
        'woz_resolvido': 'WOZ Total',
        'woz_linux_resolvido': 'Linux',
        'woz_windows_resolvido': 'Windows', 
        'woz_wordpress_resolvido': 'WordPress',
        'woz_criadordesites_resolvido': 'Criador de Sites',
        'woz_ssl_resolvido': 'Certificado SSL',
        'woz_bancodedados_resolvido': 'Banco de Dados',
        'woz_restorebackup_resolvido': 'Restore/Backup',
        'woz_registro_resolvido': 'Registro de Domínio',
        'woz_cloudhosting_resolvido': 'Cloud Hosting',
        'woz_cloudserverpro_resolvido': 'Cloud Server Pro',
        'woz_vpslocaweb_resolvido': 'VPS Locaweb',
        'woz_servidordedicado_resolvido': 'Servidor Dedicado',
        'woz_servidorgerenciado_resolvido': 'Servidor Gerenciado',
        'woz_hospedagemdedicada_resolvido': 'Hospedagem Dedicada',
        'woz_locawebcloud_resolvido': 'Locaweb Cloud',
        'woz_email_resolvido': 'Email Locaweb',
        'woz_exchange_resolvido': 'Exchange',
        'woz_emailgo_resolvido': 'Email GO',
        'woz_gw_resolvido': 'Google Workspace',
        'woz_emarketing_resolvido': 'Email Marketing',
        'woz_smtp_resolvido': 'SMTP Locaweb',
        'woz_pabx_resolvido': 'PABX Virtual',
        'woz_revendalocaweb_resolvido': 'Revenda Locaweb',
        'woz_revendaplesk_resolvido': 'Revenda Plesk',
        'woz_revendacpanel_resolvido': 'Revenda cPanel',
        'woz_cobranca_resolvido': 'Cobrança'
    }
    
    # Preparar dados para o DataFrame
    dados_atual = []
    dados_anterior = []
    
    # Ordenar por total de casos da semana atual (decrescente)
    if 'taxa_resolucao_atual' in analise_woz:
        woz_ordenado = sorted(
            analise_woz['taxa_resolucao_atual'].items(),
            key=lambda x: x[1]['total_casos'],
            reverse=True
        )
    else:
        # Fallback para método antigo
        woz_ordenado = sorted(
            analise_woz['semana_atual'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
    
    for coluna, dados_taxa in woz_ordenado:
        # Verificar se há dados relevantes para mostrar
        if 'taxa_resolucao_atual' in analise_woz:
            total_atual = dados_taxa.get('total_casos', 0)
            casos_resolvidos_atual = dados_taxa.get('casos_resolvidos', 0)
            taxa_atual = dados_taxa.get('taxa_percentual', 0)
            
            # Dados da semana anterior
            dados_taxa_anterior = analise_woz['taxa_resolucao_anterior'].get(coluna, {})
            total_anterior = dados_taxa_anterior.get('total_casos', 0)
            casos_resolvidos_anterior = dados_taxa_anterior.get('casos_resolvidos', 0)
            taxa_anterior = dados_taxa_anterior.get('taxa_percentual', 0)
        else:
            # Fallback para dados originais
            casos_resolvidos_atual = analise_woz['semana_atual'][coluna]
            casos_resolvidos_anterior = analise_woz['semana_anterior'][coluna]
            total_atual = casos_resolvidos_atual
            total_anterior = casos_resolvidos_anterior
            taxa_atual = 0
            taxa_anterior = 0
        
        # Só mostra se houve casos em alguma semana
        if total_atual > 0 or total_anterior > 0:
            nome = nomes_legivel.get(coluna, coluna.replace('woz_', '').replace('_resolvido', ''))
            
            # Variação na taxa de resolução
            variacao_taxa = taxa_atual - taxa_anterior
            
            dados_atual.append({
                'Produto': nome,
                'Total': total_atual,
                'Resolvidos': casos_resolvidos_atual,
                'Taxa (%)': f"{taxa_atual:.1f}%",
                # 'Total (Anterior)': total_anterior,
                # 'Resolvidos (Anterior)': casos_resolvidos_anterior,
                # 'Anterior (%)': f"{taxa_anterior:.1f}%",
                'Variação da Taxa em Relação a Semana Anterior (%)': f"{variacao_taxa:+.1f}%"
            })

            dados_anterior.append({
                'Produto': nome,
                'Total': total_anterior,
                'Resolvidos': casos_resolvidos_anterior,
                'Taxa (%)': f"{taxa_anterior:.1f}%"
            })
    
    return pd.DataFrame(dados_atual), pd.DataFrame(dados_anterior)

def criar_grafico_woz(analise_woz, temp_dir):
    """
    Cria gráfico de barras comparando taxas de resolução WOZ entre semanas
    """
    
    # Mapeamento de nomes mais legíveis (versão compacta para gráfico)
    nomes_grafico = {
        'woz_resolvido': 'WOZ Total',
        'woz_linux_resolvido': 'Linux',
        'woz_windows_resolvido': 'Windows', 
        'woz_wordpress_resolvido': 'WordPress',
        'woz_criadordesites_resolvido': 'Criador Sites',
        'woz_ssl_resolvido': 'SSL',
        'woz_bancodedados_resolvido': 'Banco Dados',
        'woz_restorebackup_resolvido': 'Backup',
        'woz_registro_resolvido': 'Domínio',
        'woz_cloudhosting_resolvido': 'Cloud Host',
        'woz_cloudserverpro_resolvido': 'Cloud Server',
        'woz_vpslocaweb_resolvido': 'VPS',
        'woz_servidordedicado_resolvido': 'Srv Dedicado',
        'woz_servidorgerenciado_resolvido': 'Srv Gerenciado',
        'woz_hospedagemdedicada_resolvido': 'Host Dedicada',
        'woz_locawebcloud_resolvido': 'LW Cloud',
        'woz_email_resolvido': 'Email LW',
        'woz_exchange_resolvido': 'Exchange',
        'woz_emailgo_resolvido': 'Email GO',
        'woz_gw_resolvido': 'GWorkspace',
        'woz_emarketing_resolvido': 'Email Mkt',
        'woz_smtp_resolvido': 'SMTP',
        'woz_pabx_resolvido': 'PABX',
        'woz_revendalocaweb_resolvido': 'Revenda LW',
        'woz_revendaplesk_resolvido': 'Revenda Plesk',
        'woz_revendacpanel_resolvido': 'Revenda cPanel',
        'woz_cobrança_resolvido': 'Cobrança'
    }
    
    # Preparar dados para o gráfico
    woz_com_dados = []
    taxas_anterior = []
    taxas_atual = []
    
    # Se temos dados de taxa de resolução, usar eles
    if 'taxa_resolucao_atual' in analise_woz:
        # Ordenar por total de casos da semana atual e pegar top 13
        woz_ordenado = sorted(
            analise_woz['taxa_resolucao_atual'].items(),
            key=lambda x: x[1]['total_casos'],
            reverse=True
        )#[:13]
        
        for coluna, dados_atual in woz_ordenado:
            dados_anterior = analise_woz['taxa_resolucao_anterior'].get(coluna, {})
            
            # Só incluir se houver casos em alguma semana
            if dados_atual.get('total_casos', 0) > 0 or dados_anterior.get('total_casos', 0) > 0:
                nome = nomes_grafico.get(coluna, coluna.replace('woz_', '').replace('_resolvido', ''))
                woz_com_dados.append(nome)
                taxas_atual.append(dados_atual.get('taxa_percentual', 0))
                taxas_anterior.append(dados_anterior.get('taxa_percentual', 0))
    else:
        # Fallback para método antigo (volumes)
        woz_ordenado = sorted(
            analise_woz['semana_atual'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )#[:13]
        
        for coluna, volume_atual in woz_ordenado:
            if volume_atual > 0 or analise_woz['semana_anterior'][coluna] > 0:
                nome = nomes_grafico.get(coluna, coluna.replace('woz_', '').replace('_resolvido', ''))
                woz_com_dados.append(nome)
                taxas_atual.append(volume_atual)  # Usando volumes como fallback
                taxas_anterior.append(analise_woz['semana_anterior'][coluna])
    
    if not woz_com_dados:
        return None
    
    # Criar o gráfico
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = np.arange(len(woz_com_dados))
    width = 0.35
    
    # Criar barras
    bars1 = ax.bar(x - width/2, taxas_anterior, width, label='Semana Anterior', 
                   color='#2b343c', alpha=0.8)
    bars2 = ax.bar(x + width/2, taxas_atual, width, label='Semana Atual', 
                   color='#e74c3c', alpha=0.8)
    
    # Configurar eixos
    #ax.set_xlabel('Produtos/Serviços WOZ')
    if 'taxa_resolucao_atual' in analise_woz:
        ax.set_ylabel('Taxa de Resolução (%)')
        ax.set_title('Taxa de Resolução WOZ - Comparação Semanal', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)  # Taxa varia de 0 a 100%
    else:
        ax.set_ylabel('Quantidade de Protocolos Resolvidos')
        ax.set_title('Volume de Protocolos WOZ Resolvidos - Comparação Semanal', fontsize=14, fontweight='bold')
    
    ax.set_xticks(x)
    ax.set_xticklabels(woz_com_dados, rotation=45, ha='right')
    ax.legend()
    
    # Adicionar valores nas barras
    def add_value_labels(bars, is_percentage=False):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                if is_percentage:
                    label = f'{height:.1f}%'
                else:
                    label = f'{int(height)}'
                ax.annotate(label,
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # 3 pontos de offset vertical
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)
    
    is_percentage = 'taxa_resolucao_atual' in analise_woz
    add_value_labels(bars1, is_percentage)
    add_value_labels(bars2, is_percentage)
    
    # Ajustar layout
    plt.tight_layout()
    
    # Salvar gráfico
    grafico_path = os.path.join(temp_dir, 'grafico_woz.png')
    plt.savefig(grafico_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return grafico_path

def gerar_pdf(nome_arquivo, metricas_total, metricas, metricas_sm=None, metricas_canais=None, metricas_canais_sm=None,
              df_media_anual_canais=None, metricas_equipes=None, metricas_equipes_sm=None, metricas_media_anual=None,
              metricas_nps=None, metricas_nps_sm=None, metricas_nps_anual=None, setor="", periodo="",
              content_md_first_anl=None, content_md_second_anl=None, content_md_third_anl=None, content_md_fourth_anl=None,
              analise_woz=None, analise_woz_ia=None, incidentes_dados=None):

    styles = getSampleStyleSheet()
    story = []
    
    # Criar diretório temporário para gráficos
    temp_dir = tempfile.mkdtemp()

    # === Logo e Cabeçalho ===
    logo_path = f"{sql_path}/locaweb.png"  
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=120, height=50)
        logo.hAlign = 'LEFT'
        story.append(logo)
    
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Relatório Semanal de Atendimento</b><br/>Setor: {setor}", styles['Title']))
    story.append(Paragraph(f"<b>Período:</b> {periodo}", styles['Normal']))
    story.append(Spacer(1, 24))

    def tabela_df(df, titulo, cor=None):
        if cor is None:
            cor = "#2b343c"
        story.append(Paragraph(titulo, styles['Heading2']))
        data = [df.columns.to_list()] + df.values.tolist()

        # === Calcular largura proporcional por coluna
        pesos_colunas = [max([len(str(cell)) for cell in df[col]] + [len(str(col))]) for col in df.columns]
        total_pesos = sum(pesos_colunas)
        proporcoes = [peso / total_pesos for peso in pesos_colunas]
        largura_total = 18 * cm
        col_widths = [largura_total * proporcao for proporcao in proporcoes]

        # === Criar a tabela
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(cor)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))

        # Zebra Style
        for i in range(1, len(data)):
            bg_color = colors.whitesmoke if i % 2 == 0 else colors.lightgrey
            table.setStyle([('BACKGROUND', (0, i), (-1, i), bg_color)])

        story.append(table)
        story.append(Spacer(1, 8))



    # === Primeira tabela - semana atual
    tabela_df(metricas, "Resumo da Semana")
    tabela_df(metricas_canais, "Resumo da Semana - Canais")

    if metricas_equipes is not None:
        tabela_df(metricas_equipes, "Detalhamento por Equipes:")

    if setor == 'Suporte':
        story.append(PageBreak())

    # === Semana anterior ===
    tabela_df(metricas_sm, "Resumo da Semana Anterior:")
    tabela_df(metricas_canais_sm, "Resumo da Semana Anterior - Canais")

    if metricas_equipes_sm is not None:
        tabela_df(metricas_equipes_sm, "Detalhamento da Semana Anterior por Equipes :")

    story.append(PageBreak())

    # === Inserir análise semanal x semana anterior
    if content_md_first_anl:
        html = markdown.markdown(content_md_first_anl)
        titulo_md = Paragraph("Analise da Semana Atual X Semana Anterior:", styles['Heading2'])
        story.append(titulo_md)
        estilo_md = ParagraphStyle(name='MarkdownStyle', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10)
        for linha in html.split("\n"):
            if linha.strip():
                story.append(Paragraph(linha, estilo_md))
        
        # GRÁFICO COMBINADO
        if metricas is not None and metricas_sm is not None:
            graficos_combinados = criar_grafico_combinado_metricas(metricas, metricas_sm, temp_dir)
            for path in graficos_combinados:
                if os.path.exists(path):
                    story.append(Spacer(1, 12))
                    img = Image(path, width=16*cm, height=9.6*cm)
                    img.hAlign = 'CENTER'
                    story.append(img)
                    story.append(Spacer(1, 12))

        try:
            if (metricas_equipes is not None and not metricas_equipes.empty and
                metricas_equipes_sm is not None and not metricas_equipes_sm.empty):

                # --- TME (séries por equipe)
                story.append(Spacer(1, 12))
                paths_series = criar_grafico_equipes_tme_series(metricas_equipes, metricas_equipes_sm, temp_dir)
                for p in paths_series:
                    if os.path.exists(p):
                        img = Image(p, width=16*cm, height=9.6*cm)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        story.append(Spacer(1, 12))

                # --- Recebidos (barras por equipe)
                story.append(Spacer(1, 6))
                paths_rec = criar_grafico_equipes_barras(
                    metricas_equipes, metricas_equipes_sm, temp_dir,
                    coluna='Recebidos', titulo='Recebidos por Equipe — Semana Anterior x Semana Atual'
                )
                for p in paths_rec:
                    if os.path.exists(p):
                        img = Image(p, width=16*cm, height=9.6*cm)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        story.append(Spacer(1, 12))

                # --- % Abandonos (barras por equipe)
                story.append(Spacer(1, 6))
                paths_abd = criar_grafico_equipes_barras(
                    metricas_equipes, metricas_equipes_sm, temp_dir,
                    coluna='% Abandonos', titulo='% Abandonos por Equipe — Semana Anterior x Semana Atual'
                )
                for p in paths_abd:
                    if os.path.exists(p):
                        img = Image(p, width=16*cm, height=9.6*cm)
                        img.hAlign = 'CENTER'
                        story.append(img)
                        story.append(Spacer(1, 12))
                
                # # --- Abandonos (barras por equipe)
                # story.append(Spacer(1, 6))
                # paths_abd = criar_grafico_equipes_barras(
                #     metricas_equipes, metricas_equipes_sm, temp_dir,
                #     coluna='Abandonos', titulo='Abandonos por Equipe — Semana Anterior x Semana Atual'
                # )
                # for p in paths_abd:
                #     if os.path.exists(p):
                #         img = Image(p, width=16*cm, height=9.6*cm)
                #         img.hAlign = 'CENTER'
                #         story.append(img)
                #         story.append(Spacer(1, 12))

        except Exception as e:
            story.append(Paragraph(
                f"<font color='red'>Aviso:</font> não foi possível gerar a visão consolidada/individual por equipes. Detalhes: {e}",
                styles['Normal']
            ))
    story.append(PageBreak())

    # === Seção de Incidentes (apenas para setor Suporte) ===
    if setor == 'Suporte' and incidentes_dados is not None and not incidentes_dados.empty:
        story.append(Paragraph("Incidentes - P2 da Última Semana", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Criar lista de incidentes em formato simples
        incidentes_texto = f"<b>Total de Incidentes:</b> {len(incidentes_dados)}<br/><br/>"
        incidentes_texto += "<b>Lista de Incidentes:</b><br/>"
        
        # Formatar cada incidente no formato solicitado: numero - descricao_curta - produto - data_abertura
        for _, row in incidentes_dados.iterrows():
            numero = str(row.get('numero', 'N/A'))
            descricao = str(row.get('descricao_curta', 'N/A'))
            produto = str(row.get('produto', 'N/A'))
            data_abertura = str(row.get('data_abertura', 'N/A'))
            
            # Formatar data se necessário
            try:
                if data_abertura != 'N/A':
                    # Se for datetime, formatar para dd/mm/yyyy
                    if hasattr(data_abertura, 'strftime'):
                        data_abertura = data_abertura.strftime('%d/%m/%Y')
                    elif isinstance(data_abertura, str) and len(data_abertura) > 10:
                        # Se for string com timestamp, pegar apenas a data
                        data_abertura = data_abertura[:10]
                        from datetime import datetime
                        dt = datetime.strptime(data_abertura, '%Y-%m-%d')
                        data_abertura = dt.strftime('%d/%m/%Y')
            except:
                pass  # Manter o valor original se houver erro na formatação
            
            incidentes_texto += f"• <b>{numero}</b> - {descricao} - {produto} - {data_abertura}<br/><br/>"
        
        # Adicionar o texto formatado ao PDF
        estilo_incidentes = ParagraphStyle(
            name='IncidentesStyle', 
            fontName='Helvetica', 
            fontSize=10, 
            leading=14, 
            spaceAfter=10,
            leftIndent=20
        )
        story.append(Paragraph(incidentes_texto, estilo_incidentes))
        story.append(Spacer(1, 18))
        story.append(PageBreak())

    # === Volumetria total
    tabela_df(metricas_total, "Volumetria total do ano vigente:", cor="#051534")
    story.append(Spacer(1, 18))

    # === Inserir análise semanal x média anual
    if content_md_second_anl:
        html = markdown.markdown(content_md_second_anl)
        titulo_md = Paragraph("Analise da Semana Atual X Média Anual:", styles['Heading2'])
        story.append(titulo_md)
        estilo_md = ParagraphStyle(name='MarkdownStyle', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10)
        for linha in html.split("\n"):
            if linha.strip():
                story.append(Paragraph(linha, estilo_md))

    story.append(PageBreak())

    # === Seção NPS
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Relatório Semanal de Atendimento</b><br/>NPS: {setor}", styles['Title']))
    
    if metricas_nps is not None:
        tabela_df(metricas_nps, "NPS da Semana Atual:")
        story.append(Spacer(1, 12))

    if metricas_nps_sm is not None:
        tabela_df(metricas_nps_sm, "NPS da Semana Anterior:")
        story.append(Spacer(1, 12))
    
    # GRÁFICO NPS POR LINHA
    if metricas_nps is not None and metricas_nps_sm is not None:
        graficos_nps = criar_grafico_nps_linha(metricas_nps, metricas_nps_sm, temp_dir, setor)
        for path in graficos_nps:
            if os.path.exists(path):
                story.append(Spacer(1, 12))
                img = Image(path, width=16*cm, height=9.6*cm)
                img.hAlign = 'CENTER'
                story.append(img)
                story.append(Spacer(1, 12))

    # === Inserir análise NPS
    if content_md_third_anl:
        story.append(PageBreak())
        html = markdown.markdown(content_md_third_anl)
        titulo_md = Paragraph("Analise NPS da Semana Atual X NPS da Semana Anterior:", styles['Heading2'])
        story.append(titulo_md)
        estilo_md = ParagraphStyle(name='MarkdownStyle', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10)
        for linha in html.split("\n"):
            if linha.strip():
                story.append(Paragraph(linha, estilo_md))

    # === Inserir análise dos comentários ===
    if content_md_fourth_anl:
        html = markdown.markdown(content_md_fourth_anl)
        titulo_md = Paragraph("Análise dos Comentários:", styles['Heading2'])
        story.append(Spacer(1, 12))
        story.append(titulo_md)
        estilo_md = ParagraphStyle(name='MarkdownStyle', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=10)
        for linha in html.split("\n"):
            if linha.strip():
                story.append(Paragraph(linha, estilo_md))

    # === Seção WOZ ===
    if analise_woz:
        if setor == 'Suporte':
            # Quebra de página para iniciar seção WOZ
            story.append(PageBreak())
            
            # Título da seção WOZ
            titulo_woz = Paragraph("Análise WOZ", styles['Heading1'])
            story.append(titulo_woz)
            story.append(Spacer(1, 18))
            
            # Criar DataFrames para as tabelas WOZ
            df_woz_atual, df_woz_anterior = criar_dataframe_woz(analise_woz)
            
            # Verificar se há dados para mostrar
            if not df_woz_atual.empty or not df_woz_anterior.empty:
                
                # === TABELA SEMANA ATUAL ===
                if not df_woz_atual.empty:
                    if 'taxa_resolucao_atual' in analise_woz:
                        titulo_tabela_atual = "Taxa de Resolução WOZ - Semana Atual"
                    else:
                        titulo_tabela_atual = "Volume de Protocolos WOZ Resolvidos - Semana Atual"
                    
                    tabela_df(df_woz_atual, titulo_tabela_atual)
                    story.append(Spacer(1, 12))
                    story.append(PageBreak())
                
                # === TABELA SEMANA ANTERIOR ===
                # if not df_woz_anterior.empty:
                #     if 'taxa_resolucao_anterior' in analise_woz:
                #         titulo_tabela_anterior = "Taxa de Resolução WOZ - Semana Anterior"
                #     else:
                #         titulo_tabela_anterior = "Volume de Protocolos WOZ Resolvidos - Semana Anterior"
                    
                #     tabela_df(df_woz_anterior, titulo_tabela_anterior)
                #     story.append(Spacer(1, 18))
                #     story.append(PageBreak())
                
                # Criar e adicionar gráfico WOZ
                grafico_woz_path = criar_grafico_woz(analise_woz, temp_dir)
                if grafico_woz_path and os.path.exists(grafico_woz_path):
                    try:
                        img_woz = Image(grafico_woz_path, width=18*cm, height=12*cm)
                        img_woz.hAlign = 'CENTER'
                        story.append(img_woz)
                        story.append(Spacer(1, 12))
                    except Exception as e:
                        print(f"Erro ao adicionar gráfico WOZ: {e}")
                
                # Usar análise WOZ gerada por IA se disponível, senão usar resumo estatístico
                if analise_woz_ia:
                    # Converter markdown da IA para HTML simples
                    resumo_texto = analise_woz_ia.strip()
                    
                    # Remover possíveis títulos markdown primeiro
                    resumo_texto = re.sub(r'^#{1,6}\s*', '', resumo_texto, flags=re.MULTILINE)
                    
                    # Substituir **texto** por <b>texto</b> (negrito)
                    resumo_texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', resumo_texto)
                    
                    # Substituir quebras de linha excessivas por espaços
                    resumo_texto = re.sub(r'\n+', ' ', resumo_texto)
                    
                    # Limpar espaços múltiplos
                    resumo_texto = re.sub(r'\s+', ' ', resumo_texto).strip()
                elif 'taxa_resolucao_atual' in analise_woz:
                    # Resumo com taxas de resolução
                    total_casos_atual = sum(dados['total_casos'] for dados in analise_woz['taxa_resolucao_atual'].values())
                    total_resolvidos_atual = sum(dados['casos_resolvidos'] for dados in analise_woz['taxa_resolucao_atual'].values())
                    
                    total_casos_anterior = sum(dados['total_casos'] for dados in analise_woz['taxa_resolucao_anterior'].values())
                    total_resolvidos_anterior = sum(dados['casos_resolvidos'] for dados in analise_woz['taxa_resolucao_anterior'].values())
                    
                    taxa_geral_atual = (total_resolvidos_atual / total_casos_atual * 100) if total_casos_atual > 0 else 0
                    taxa_geral_anterior = (total_resolvidos_anterior / total_casos_anterior * 100) if total_casos_anterior > 0 else 0
                    
                    variacao_taxa = taxa_geral_atual - taxa_geral_anterior
                    
                    resumo_texto = f"<b>Resumo WOZ:</b> Na semana atual foram analisados {total_casos_atual} casos WOZ, "
                    resumo_texto += f"dos quais {total_resolvidos_atual} foram resolvidos automaticamente "
                    resumo_texto += f"(taxa de resolução: {taxa_geral_atual:.1f}%). "
                    resumo_texto += f"Na semana anterior: {total_casos_anterior} casos, {total_resolvidos_anterior} resolvidos "
                    resumo_texto += f"(taxa: {taxa_geral_anterior:.1f}%). "
                    resumo_texto += f"Variação na taxa: {variacao_taxa:+.1f} pontos percentuais."
                else:
                    # Fallback para resumo original
                    total_atual = sum(analise_woz['semana_atual'].values())
                    total_anterior = sum(analise_woz['semana_anterior'].values())
                    diferenca_total = total_atual - total_anterior
                    
                    if total_anterior > 0:
                        variacao_total = ((total_atual - total_anterior) / total_anterior) * 100
                        resumo_texto = f"<b>Resumo:</b> Total de {total_atual} protocolos resolvidos automaticamente na semana atual, "
                        resumo_texto += f"comparado a {total_anterior} na semana anterior. "
                        resumo_texto += f"Variação de {diferenca_total:+d} protocolos ({variacao_total:+.1f}%)."
                    else:
                        resumo_texto = f"<b>Resumo:</b> Total de {total_atual} protocolos resolvidos automaticamente na semana atual."
                
                resumo_paragraph = Paragraph(resumo_texto, styles['Normal'])
                story.append(resumo_paragraph)
            # =========== Caso Seja WOZ de Cobrança remove as quebras de páginas.
        else:
            # Quebra de página para iniciar seção WOZ - Cobrança
            story.append(PageBreak())
            
            # Título da seção WOZ
            titulo_woz = Paragraph("Análise WOZ", styles['Heading1'])
            story.append(titulo_woz)
            story.append(Spacer(1, 12))
                
            # Criar DataFrames para as tabelas WOZ
            df_woz_atual, df_woz_anterior = criar_dataframe_woz(analise_woz)
            
            # Verificar se há dados para mostrar
            if not df_woz_atual.empty or not df_woz_anterior.empty:
                
                # === TABELA SEMANA ATUAL ===
                if not df_woz_atual.empty:
                    if 'taxa_resolucao_atual' in analise_woz:
                        titulo_tabela_atual = "Taxa de Resolução WOZ - Semana Atual"
                    else:
                        titulo_tabela_atual = "Volume de Protocolos WOZ Resolvidos - Semana Atual"
                    
                    tabela_df(df_woz_atual, titulo_tabela_atual)
                    story.append(Spacer(1, 12))
                
                # === TABELA SEMANA ANTERIOR ===
                # if not df_woz_anterior.empty:
                #     if 'taxa_resolucao_anterior' in analise_woz:
                #         titulo_tabela_anterior = "Taxa de Resolução WOZ - Semana Anterior"
                #     else:
                #         titulo_tabela_anterior = "Volume de Protocolos WOZ Resolvidos - Semana Anterior"
                    
                #     tabela_df(df_woz_anterior, titulo_tabela_anterior)
                #     story.append(Spacer(1, 12))
                
                # Criar e adicionar gráfico WOZ
                grafico_woz_path = criar_grafico_woz(analise_woz, temp_dir)
                if grafico_woz_path and os.path.exists(grafico_woz_path):
                    try:
                        img_woz = Image(grafico_woz_path, width=18*cm, height=12*cm)
                        img_woz.hAlign = 'CENTER'
                        story.append(img_woz)
                        story.append(Spacer(1, 12))
                    except Exception as e:
                        print(f"Erro ao adicionar gráfico WOZ: {e}")
                
                # Usar análise WOZ gerada por IA se disponível, senão usar resumo estatístico
                if analise_woz_ia:
                    # Converter markdown da IA para HTML simples
                    resumo_texto = analise_woz_ia.strip()
                    
                    # Remover possíveis títulos markdown primeiro
                    resumo_texto = re.sub(r'^#{1,6}\s*', '', resumo_texto, flags=re.MULTILINE)
                    
                    # Substituir **texto** por <b>texto</b> (negrito)
                    resumo_texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', resumo_texto)
                    
                    # Substituir quebras de linha excessivas por espaços
                    resumo_texto = re.sub(r'\n+', ' ', resumo_texto)
                    
                    # Limpar espaços múltiplos
                    resumo_texto = re.sub(r'\s+', ' ', resumo_texto).strip()
                elif 'taxa_resolucao_atual' in analise_woz:
                    # Resumo com taxas de resolução
                    total_casos_atual = sum(dados['total_casos'] for dados in analise_woz['taxa_resolucao_atual'].values())
                    total_resolvidos_atual = sum(dados['casos_resolvidos'] for dados in analise_woz['taxa_resolucao_atual'].values())
                    
                    total_casos_anterior = sum(dados['total_casos'] for dados in analise_woz['taxa_resolucao_anterior'].values())
                    total_resolvidos_anterior = sum(dados['casos_resolvidos'] for dados in analise_woz['taxa_resolucao_anterior'].values())
                    
                    taxa_geral_atual = (total_resolvidos_atual / total_casos_atual * 100) if total_casos_atual > 0 else 0
                    taxa_geral_anterior = (total_resolvidos_anterior / total_casos_anterior * 100) if total_casos_anterior > 0 else 0
                    
                    variacao_taxa = taxa_geral_atual - taxa_geral_anterior
                    
                    resumo_texto = f"<b>Resumo WOZ:</b> Na semana atual foram analisados {total_casos_atual} casos WOZ, "
                    resumo_texto += f"dos quais {total_resolvidos_atual} foram resolvidos automaticamente "
                    resumo_texto += f"(taxa de resolução: {taxa_geral_atual:.1f}%). "
                    resumo_texto += f"Na semana anterior: {total_casos_anterior} casos, {total_resolvidos_anterior} resolvidos "
                    resumo_texto += f"(taxa: {taxa_geral_anterior:.1f}%). "
                    resumo_texto += f"Variação na taxa: {variacao_taxa:+.1f} pontos percentuais."
                else:
                    # Fallback para resumo original
                    total_atual = sum(analise_woz['semana_atual'].values())
                    total_anterior = sum(analise_woz['semana_anterior'].values())
                    diferenca_total = total_atual - total_anterior
                    
                    if total_anterior > 0:
                        variacao_total = ((total_atual - total_anterior) / total_anterior) * 100
                        resumo_texto = f"<b>Resumo:</b> Total de {total_atual} protocolos resolvidos automaticamente na semana atual, "
                        resumo_texto += f"comparado a {total_anterior} na semana anterior. "
                        resumo_texto += f"Variação de {diferenca_total:+d} protocolos ({variacao_total:+.1f}%)."
                    else:
                        resumo_texto = f"<b>Resumo:</b> Total de {total_atual} protocolos resolvidos automaticamente na semana atual."
                
                resumo_paragraph = Paragraph(resumo_texto, styles['Normal'])
                story.append(resumo_paragraph)

    # === Rodapé ===
    def rodape(canvas, doc):
        from datetime import datetime
        canvas.saveState()
        largura, altura = A4
        canvas.setFillColor(colors.HexColor("#2b343c"))
        canvas.rect(0, 0, largura, 1.3 * cm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica', 9)
        canvas.drawString(2 * cm, 0.5 * cm, f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(largura - 2 * cm, 0.5 * cm, f"Página {doc.page}")
        canvas.restoreState()

    # === Construção do PDF ===
    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2.5*cm
    )
    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    
    # Limpar arquivos temporários
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        # Log do erro caso necessário, mas continua execução
        print(f"Aviso: Não foi possível limpar arquivos temporários: {e}")