import os
import re
import html
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from google.cloud import bigquery

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AVAILABLE = True
except Exception:
    VERTEX_AVAILABLE = False

st.set_page_config(
    page_title="Radar Imobiliário",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
:root {
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #0f172a;
    --muted: #64748b;
    --border: #e2e8f0;
    --green: #15803d;
    --green-soft: #dcfce7;
    --orange: #f97316;
    --blue-soft: #eaf4ff;
    --shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
}

.block-container {
    padding: 1.2rem 1.6rem 2rem 1.6rem;
    max-width: 100%;
}

header[data-testid="stHeader"] {
    background: rgba(248, 250, 252, 0.9);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #0f172a 55%, #052e16 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
    width: 285px !important;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stSlider label {
    font-size: 0.78rem !important;
    font-weight: 700 !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] * {
    color: #0f172a !important;
}

.main-header {
    display: grid;
    grid-template-columns: minmax(230px, 0.9fr) minmax(360px, 1.5fr) auto;
    gap: 28px;
    align-items: center;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 26px 30px;
    margin: 0 0 22px 0;
    box-shadow: var(--shadow);
}

.brand-box {
    display: flex;
    align-items: center;
    gap: 16px;
}

.logo-mark {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: linear-gradient(135deg, #ecfccb, #ffffff 55%, #ffedd5);
    border: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--green);
    font-size: 28px;
    font-weight: 900;
}

.brand-title {
    font-size: 31px;
    font-weight: 900;
    letter-spacing: 6px;
    color: var(--text);
    line-height: 1;
}

.brand-subtitle {
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 5px;
    color: var(--green);
    margin-top: 7px;
}

.header-title {
    font-size: 24px;
    font-weight: 900;
    color: var(--text);
    line-height: 1.25;
}

.orange { color: var(--orange); }
.green { color: #65a30d; }

.header-caption {
    margin-top: 8px;
    font-size: 14px;
    color: var(--muted);
}

.status-pill {
    justify-self: end;
    background: #f8fafc;
    border: 1px solid var(--border);
    color: #1e293b;
    border-radius: 999px;
    padding: 13px 18px;
    font-size: 13px;
    font-weight: 800;
    white-space: nowrap;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(130px, 1fr));
    gap: 14px;
    margin-bottom: 22px;
}

.kpi-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
    min-height: 108px;
}

.kpi-label {
    font-size: 13px;
    color: var(--muted);
    font-weight: 700;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 34px;
    line-height: 1;
    color: var(--text);
    font-weight: 850;
}

.kpi-note {
    font-size: 12px;
    color: var(--green);
    margin-top: 8px;
    font-weight: 700;
}

.section-title {
    display: flex;
    justify-content: space-between;
    align-items: end;
    margin: 18px 0 12px 0;
}

.section-title h2 {
    font-size: 25px;
    margin: 0;
    color: var(--text);
}

.section-title p {
    margin: 4px 0 0 0;
    color: var(--muted);
    font-size: 14px;
}

.property-card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.075);
    min-height: 590px;
}

.property-img {
    height: 172px;
    overflow: hidden;
    background: linear-gradient(135deg, #14532d 0%, #f97316 100%);
}

.property-img img {
    width: 100%;
    height: 172px;
    object-fit: cover;
    display: block;
}

.property-img-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
}

.property-img-placeholder-content {
    width: 100%;
    height: 172px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 28px;
    font-weight: 900;
    text-align: center;
}

.property-img-placeholder-content span {
    font-size: 13px;
    letter-spacing: 0.5px;
}

.property-body {
    padding: 16px 18px 18px 18px;
}

.badge-forte, .badge-media, .badge-fraca {
    display: inline-block;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 900;
    margin-bottom: 12px;
}

.badge-forte {
    background: #15803d;
    color: white;
}

.badge-media {
    background: #f97316;
    color: white;
}

.badge-fraca {
    background: #64748b;
    color: white;
}

.property-title {
    color: var(--text);
    font-size: 18px;
    line-height: 1.22;
    font-weight: 850;
    min-height: 66px;
    margin-bottom: 10px;
}

.property-meta {
    color: #475569;
    font-size: 13px;
    line-height: 1.55;
    margin-bottom: 11px;
}

.property-price {
    color: var(--text);
    font-size: 29px;
    font-weight: 900;
    margin: 13px 0 2px 0;
}

.property-m2 {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 10px;
}

.discount-box {
    background: var(--blue-soft);
    border: 1px solid #dbeafe;
    border-radius: 12px;
    padding: 10px 12px;
    color: #075985;
    font-size: 13px;
    font-weight: 800;
    margin: 10px 0;
}

.similar-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 10px 12px;
    color: #166534;
    font-size: 12px;
    font-weight: 750;
    margin: 10px 0;
}

.warning-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 12px;
    padding: 10px 12px;
    color: #9a3412;
    font-size: 12px;
    font-weight: 750;
    margin: 10px 0;
}

.score-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 1px solid var(--border);
    padding-top: 13px;
    margin-top: 13px;
}

.score-circle {
    width: 48px;
    height: 48px;
    border-radius: 999px;
    border: 4px solid #65a30d;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #166534;
    font-weight: 900;
    background: #f7fee7;
}

.score-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
}

.score-text {
    color: #166534;
    font-size: 13px;
    font-weight: 800;
}

.feature-card {
    background: white;
    border-radius: 18px;
    padding: 22px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    min-height: 135px;
}

.feature-card h3 {
    color: var(--text);
    font-size: 18px;
    margin-bottom: 8px;
}

.feature-card p {
    color: #475569;
    font-size: 14px;
}

.stTabs [data-baseweb="tab-list"] {
    background: #ffffff;
    border-radius: 16px;
    padding: 8px;
    border: 1px solid var(--border);
    box-shadow: 0 8px 20px rgba(15,23,42,0.06);
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 850;
    border-radius: 12px;
    padding: 10px 14px;
}

div[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 12px;
}

@media (max-width: 1200px) {
    .main-header {
        grid-template-columns: 1fr;
        gap: 12px;
    }
    .status-pill {
        justify-self: start;
    }
    .kpi-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 760px) {
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .brand-title {
        font-size: 24px;
    }
}

div[data-testid="stImage"] img {
    border-radius: 14px;
    max-height: 172px;
    object-fit: cover;
}

/* ─── ABA OPORTUNIDADES EM CARDS ─────────────────────────────────────────── */
.op-filter-help {
    color: #64748b;
    font-size: 13px;
    margin-top: -4px;
    margin-bottom: 12px;
}

div[data-testid="stImage"] img {
    border-radius: 14px;
    max-height: 172px;
    object-fit: cover;
}

/* ─── INTELIGÊNCIA REGIONAL EXECUTIVA ─────────────────────────────────────── */
.regional-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(170px, 1fr));
    gap: 14px;
    margin: 14px 0 18px 0;
}

.regional-kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
    min-height: 126px;
}

.regional-kpi-label {
    font-size: 13px;
    color: #64748b;
    font-weight: 800;
    margin-bottom: 8px;
}

.regional-kpi-title {
    font-size: 22px;
    line-height: 1.05;
    color: #0f172a;
    font-weight: 950;
    margin-bottom: 10px;
}

.regional-kpi-value {
    font-size: 26px;
    line-height: 1;
    font-weight: 950;
}

.regional-green { color: #15803d; }
.regional-blue { color: #2563eb; }
.regional-orange { color: #f97316; }
.regional-purple { color: #7c3aed; }

@media (max-width: 1200px) {
    .regional-kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}


/* ─── DUPLICADOS EXECUTIVO ───────────────────────────────────────────────── */
.dup-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
}

.dup-icon {
    width: 44px;
    height: 44px;
    border-radius: 999px;
    background: #15803d;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 23px;
    font-weight: 900;
}

.dup-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(190px, 1fr));
    gap: 14px;
    margin: 18px 0 18px 0;
}

.dup-kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
    min-height: 120px;
}

.dup-kpi-label {
    font-size: 13px;
    color: #64748b;
    font-weight: 800;
    margin-bottom: 8px;
}

.dup-kpi-value {
    font-size: 30px;
    line-height: 1;
    color: #0f172a;
    font-weight: 950;
}

.dup-kpi-note {
    margin-top: 10px;
    color: #15803d;
    font-size: 12px;
    font-weight: 800;
}

.dup-section-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
    margin-bottom: 16px;
}

.compare-card-red {
    border: 1px solid #fecaca;
    background: #fffafa;
    border-radius: 16px;
    padding: 14px;
}

.compare-card-green {
    border: 1px solid #bbf7d0;
    background: #f7fff9;
    border-radius: 16px;
    padding: 14px;
}

.compare-price-red {
    font-size: 27px;
    font-weight: 950;
    color: #dc2626;
}

.compare-price-green {
    font-size: 27px;
    font-weight: 950;
    color: #15803d;
}

.compare-saving {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 18px;
    padding: 18px;
    text-align: center;
}

@media (max-width: 1200px) {
    .dup-kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}


/* ─── IA / CHAT EXECUTIVO ───────────────────────────────────────────────── */
.ai-panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.055);
    margin-bottom: 16px;
}

.ai-question-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 14px;
    min-height: 120px;
}

.ai-question-title {
    color: #0f172a;
    font-weight: 900;
    font-size: 15px;
    margin-bottom: 8px;
}

.ai-question-text {
    color: #475569;
    font-size: 13px;
    line-height: 1.45;
}

.ai-answer {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 18px;
    padding: 18px;
    color: #0f172a;
    line-height: 1.55;
}

</style>
""", unsafe_allow_html=True)

PROJECT_ID = "radar-imobiliario"
DATASET = "real_estate"
VIEW = "vw_oportunidades_web"
MART_BAIRROS = "mart_bairros_inteligencia"

VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
VERTEX_FALLBACK_MODELS = [
    modelo.strip()
    for modelo in os.getenv(
        "VERTEX_FALLBACK_MODELS",
        "gemini-2.5-flash,gemini-2.0-flash-001,gemini-2.0-flash-lite-001"
    ).split(",")
    if modelo.strip()
]

if VERTEX_MODEL not in VERTEX_FALLBACK_MODELS:
    VERTEX_FALLBACK_MODELS.insert(0, VERTEX_MODEL)

client = bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=600)
def carregar_dados():
    query = f"""
        SELECT
            id_imovel,
            titulo,
            descricao,
            tipo_imovel,
            finalidade,
            preco_anunciado,
            area_total_m2,
            area_construida_m2,
            quartos,
            banheiros,
            vagas_garagem,
            bairro,
            cidade,
            estado,
            latitude,
            longitude,
            fonte,
            url_anuncio,
            imagem_principal_url,
            qtd_imagens,
            data_coleta,
            preco_m2,
            media_preco_m2_regiao,
            mediana_preco_m2_regiao,
            qtd_imoveis_regiao,
            criterio_comparacao,
            percentual_abaixo_mediana,
            chave_similaridade,
            qtd_anuncios_similares,
            menor_preco_grupo,
            maior_preco_grupo,
            media_preco_grupo,
            diferenca_para_menor_preco,
            percentual_acima_menor_preco_grupo,
            possivel_duplicado,
            menor_preco_entre_similares,
            score_preco,
            score_imagem,
            score_area,
            score_dados,
            score_duplicidade,
            score_oportunidade,
            classificacao_oportunidade,
            motivo_oportunidade,
            liquidez_bairro,
            perfil_bairro,
            nivel_valorizacao,
            score_bairro,
            resumo_bairro,

            preco_inicial,
            preco_atual,
            variacao_preco_absoluta,
            percentual_queda_preco,
            dias_anunciado,
            qtd_quedas_preco,
            classificacao_queda_preco,
            sinal_negociacao,

            qtd_novos,
            qtd_removidos,
            qtd_atualizados,
            qtd_atualizacoes_preco,
            taxa_absorcao_pct,
            classificacao_movimento,
            liquidez_real,
            score_liquidez_real,
            resumo_liquidez,

            score_final_radar,
            classificacao_final_radar,
            motivo_final_radar
        FROM `{PROJECT_ID}.{DATASET}.{VIEW}`
        WHERE preco_anunciado IS NOT NULL
          AND preco_m2 IS NOT NULL
          AND preco_anunciado >= 30000
          AND LOWER(TRIM(CAST(finalidade AS STRING))) LIKE '%venda%'
          AND NOT REGEXP_CONTAINS(
              LOWER(CONCAT(
                  IFNULL(CAST(titulo AS STRING), ''), ' ',
                  IFNULL(CAST(descricao AS STRING), ''), ' ',
                  IFNULL(CAST(url_anuncio AS STRING), '')
              )),
              r'(aluguel|alugar|locacao|locação|mensal|por mes|por mês|/aluguel|para-alugar|para alugar)'
          )
          AND imagem_principal_url IS NOT NULL
          AND TRIM(CAST(imagem_principal_url AS STRING)) != ''
          AND LOWER(TRIM(CAST(imagem_principal_url AS STRING))) NOT IN ('0', 'none', 'null', 'nan', 'sem imagem', 'sem_imagem', '-')
          AND REGEXP_CONTAINS(TRIM(CAST(imagem_principal_url AS STRING)), r'^https?://')
        ORDER BY score_final_radar DESC
        LIMIT 5000
    """
    return client.query(query).to_dataframe()


@st.cache_data(ttl=600)
def carregar_bairros_inteligencia():
    query = f"""
        SELECT
          cidade,
          bairro,
          tipo_imovel,
          qtd_anuncios AS qtd_imoveis,
          preco_medio_anunciado AS preco_medio,
          preco_medio_m2 AS preco_m2_medio,
          preco_mediano_m2 AS preco_m2_mediano,
          CAST(NULL AS FLOAT64) AS desconto_medio,
          score_bairro AS score_medio,
          score_bairro AS score_maximo,
          CAST(NULL AS INT64) AS qtd_oportunidades_fortes,
          CAST(NULL AS INT64) AS qtd_oportunidades_medias,
          media_imagens AS qtd_com_imagem,
          ultima_coleta AS data_ultima_coleta,
          liquidez_bairro,
          perfil_bairro,
          nivel_valorizacao,
          score_bairro,
          resumo_bairro
        FROM `{PROJECT_ID}.{DATASET}.{MART_BAIRROS}`
    """
    return client.query(query).to_dataframe()


def normalizar_preco(valor, finalidade=None):
    if pd.isna(valor):
        return valor
    try:
        valor_float = float(valor)
    except Exception:
        return valor
    finalidade_txt = "" if finalidade is None or pd.isna(finalidade) else str(finalidade).lower()
    if "venda" in finalidade_txt and 0 < valor_float < 1000:
        return valor_float * 1000
    return valor_float



def filtrar_apenas_venda(df_base, preco_minimo=30000):
    """
    Remove anúncios de aluguel que entram indevidamente como venda.
    A regra combina:
    - finalidade contendo venda;
    - preço mínimo compatível com imóvel de venda;
    - bloqueio por palavras típicas de locação no título/descrição/URL.
    """
    if df_base is None or df_base.empty:
        return df_base

    df_filtrado = df_base.copy()

    if "preco_anunciado" in df_filtrado.columns:
        preco_num = pd.to_numeric(df_filtrado["preco_anunciado"], errors="coerce").fillna(0)
        df_filtrado = df_filtrado[preco_num >= preco_minimo].copy()

    if "preco_anunciado_corrigido" in df_filtrado.columns:
        preco_corrigido_num = pd.to_numeric(df_filtrado["preco_anunciado_corrigido"], errors="coerce").fillna(0)
        df_filtrado = df_filtrado[preco_corrigido_num >= preco_minimo].copy()

    if "finalidade" in df_filtrado.columns:
        finalidade_txt = df_filtrado["finalidade"].fillna("").astype(str).str.lower()
        df_filtrado = df_filtrado[finalidade_txt.str.contains("venda", regex=False, na=False)].copy()

    partes_texto = []
    for col in ["titulo", "descricao", "url_anuncio", "finalidade"]:
        if col in df_filtrado.columns:
            partes_texto.append(df_filtrado[col].fillna("").astype(str))

    if partes_texto:
        texto_busca = partes_texto[0]
        for parte in partes_texto[1:]:
            texto_busca = texto_busca + " " + parte

        texto_busca = texto_busca.str.lower()
        padrao_aluguel = r"aluguel|alugar|locacao|locação|mensal|por mes|por mês|/aluguel|para-alugar|para alugar"
        df_filtrado = df_filtrado[
            ~texto_busca.str.contains(padrao_aluguel, regex=True, na=False)
        ].copy()

    return df_filtrado


def moeda(valor):
    if pd.isna(valor):
        return "-"
    try:
        return f"R$ {float(valor):,.0f}".replace(",", ".")
    except Exception:
        return "-"


def moeda_abreviado(valor):
    """Formata valor de forma abreviada: 7.6M, 590k, etc."""
    if pd.isna(valor):
        return "-"
    try:
        v = float(valor)
        if v >= 1_000_000:
            return f"R$ {v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"R$ {v/1_000:.0f}k"
        return f"R$ {v:.0f}"
    except Exception:
        return "-"


def percentual(valor):
    if pd.isna(valor):
        return "-"
    try:
        return f"{float(valor):.1f}%"
    except Exception:
        return "-"


def texto_limpo(valor, padrao="Não informado"):
    if pd.isna(valor) or str(valor).strip() == "":
        return padrao
    return str(valor)


def badge_classificacao(valor):
    texto = str(valor).upper()
    if "FORTE" in texto:
        return "badge-forte"
    if "MEDIA" in texto or "MÉDIA" in texto:
        return "badge-media"
    return "badge-fraca"


def tratar_url_imagem(valor):
    """
    Normaliza a URL da imagem antes de renderizar no Streamlit.
    Evita tentar carregar valores inválidos como 0, None, nan, null ou texto vazio.
    Também trata casos em que a origem venha com mais de uma URL no mesmo campo.
    """
    if valor is None or pd.isna(valor):
        return None

    url = str(valor).strip()

    if not url:
        return None

    url_lower = url.lower()
    if url_lower in ["0", "none", "nan", "null", "sem imagem", "sem_imagem", "-"]:
        return None

    # Se vier mais de uma URL no mesmo campo, pega a primeira válida.
    partes = re.split(r"[|,;\n\r\t ]+", url)
    for parte in partes:
        parte = parte.strip().strip('"').strip("'")
        if parte.startswith("http://") or parte.startswith("https://"):
            return parte

    return None


def imagem_placeholder_html():
    return """
    <div class="property-img property-img-placeholder">
        <div class="property-img-placeholder-content">
            🏠<br>
            <span>Sem imagem</span>
        </div>
    </div>
    """


def html_imagem(url):
    url_tratada = tratar_url_imagem(url)

    if url_tratada:
        url_segura = html.escape(url_tratada, quote=True)
        return f"""
        <div class="property-img">
            <img
                src="{url_segura}"
                referrerpolicy="no-referrer"
                loading="lazy"
                onerror="this.parentElement.innerHTML='<div class=&quot;property-img-placeholder-content&quot;>🏠<br><span>Sem imagem</span></div>'; this.parentElement.classList.add('property-img-placeholder');"
            >
        </div>
        """

    return imagem_placeholder_html()


def render_imagem_imovel(url):
    """
    Renderiza imagem por HTML para permitir referrerpolicy e fallback.
    Isso evita o ícone quebrado quando a origem bloqueia st.image ou quando a URL vem inválida.
    """
    st.markdown(html_imagem(url), unsafe_allow_html=True)


# ─── PALETA DE CORES RADAR ────────────────────────────────────────────────────
RADAR_GREEN      = "#15803d"
RADAR_GREEN_MID  = "#22c55e"
RADAR_GREEN_SOFT = "#86efac"
RADAR_BLUE       = "#1e40af"
RADAR_BLUE_MID   = "#3b82f6"
RADAR_ORANGE     = "#f97316"
RADAR_MUTED      = "#94a3b8"
RADAR_DARK       = "#0f172a"
RADAR_BORDER     = "#e2e8f0"
RADAR_BG         = "#f8fafc"

CHART_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=RADAR_DARK),
    hoverlabel=dict(
        bgcolor="white",
        bordercolor=RADAR_BORDER,
        font_size=13,
        font_family="Inter, sans-serif"
    )
)
MARGIN_DEFAULT = dict(l=12, r=12, t=50, b=20)

XAXIS_STYLE = dict(
    showgrid=False,
    zeroline=False,
    linecolor=RADAR_BORDER,
    tickfont=dict(size=12, color="#64748b"),
    title_font=dict(size=13, color="#64748b")
)

YAXIS_STYLE = dict(
    showgrid=True,
    gridcolor="#f1f5f9",
    gridwidth=1,
    zeroline=False,
    linecolor=RADAR_BORDER,
    tickfont=dict(size=12, color="#64748b"),
    title_font=dict(size=13, color="#64748b")
)


def normalizar_cidade(nome):
    """Corrige variações de grafia no nome da cidade (ex: Largato → Lagarto)."""
    import unicodedata
    s = str(nome).strip()
    # Remove acentos e coloca em minúsculo para comparação
    sem_acento = unicodedata.normalize("NFD", s)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn").lower()
    # Mapa de correções conhecidas
    correcoes = {
        "largato": "Lagarto",
        "lagarto": "Lagarto",
    }
    return correcoes.get(sem_acento, s)


def grafico_oportunidades_por_cidade(df):
    """
    Gráfico de barras: Oportunidades por cidade.
    Melhorias: cores por intensidade, rótulos nas barras, linha de média,
    hover rico, cantos arredondados.
    """
    df = df.copy()
    df["cidade_norm"] = df["cidade"].apply(normalizar_cidade)

    dados = (
        df.groupby("cidade_norm", as_index=False)
        .agg(qtd=("id_imovel", "count"), score_medio=("score_oportunidade", "mean"))
        .rename(columns={"cidade_norm": "cidade"})
        .sort_values("qtd", ascending=False)
    )

    if dados.empty:
        return None

    media = dados["qtd"].mean()

    # Escala de cor: verde mais intenso quanto maior a quantidade
    max_qtd = dados["qtd"].max()
    cores = [
        f"rgba(21,128,61,{0.35 + 0.65 * (v / max_qtd):.2f})"
        for v in dados["qtd"]
    ]

    fig = go.Figure()

    # Barras
    fig.add_trace(go.Bar(
        x=dados["cidade"],
        y=dados["qtd"],
        marker=dict(
            color=cores,
            line=dict(width=0),
            cornerradius=8
        ),
        text=[str(int(v)) for v in dados["qtd"]],
        textposition="outside",
        textfont=dict(size=13, color=RADAR_DARK, family="Inter, sans-serif"),
        customdata=dados[["score_medio"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Oportunidades: <b>%{y}</b><br>"
            "Score médio: <b>%{customdata[0]:.1f}</b><extra></extra>"
        ),
        name=""
    ))

    # Linha de média
    fig.add_hline(
        y=media,
        line=dict(color=RADAR_ORANGE, width=1.5, dash="dot"),
        annotation_text=f"  média {media:.0f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color=RADAR_ORANGE)
    )

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="Oportunidades por cidade", font=dict(size=16, color=RADAR_DARK), x=0),
        height=400,
        showlegend=False,
        xaxis=dict(**XAXIS_STYLE, title=""),
        yaxis=dict(**YAXIS_STYLE, title="Qtd. de oportunidades"),
        bargap=0.35,
        margin=MARGIN_DEFAULT
    )

    return fig


def grafico_top_bairros_score(df):
    """
    Gráfico de barras horizontal: Top 10 bairros por score médio.
    Melhorias: rótulos de valor, hover rico com desconto e preço médio,
    cores por intensidade, linha de média.
    """
    df = df.copy()
    df["cidade"] = df["cidade"].apply(normalizar_cidade)
    dados = (
        df.groupby(["cidade", "bairro"], as_index=False)
        .agg(
            qtd=("id_imovel", "count"),
            score_medio=("score_oportunidade", "mean"),
            desconto_medio=("percentual_abaixo_mediana", "mean"),
            preco_medio=("preco_anunciado_corrigido", "mean")
        )
        .sort_values("score_medio", ascending=False)
        .head(10)
    )

    if dados.empty:
        return None

    dados["regiao"] = dados["bairro"] + " · " + dados["cidade"]
    dados = dados.sort_values("score_medio", ascending=True)  # ascendente p/ barras horizontais

    media = dados["score_medio"].mean()
    max_score = dados["score_medio"].max()
    cores = [
        f"rgba(21,128,61,{0.30 + 0.70 * (v / max_score):.2f})"
        for v in dados["score_medio"]
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=dados["regiao"],
        x=dados["score_medio"],
        orientation="h",
        marker=dict(
            color=cores,
            line=dict(width=0),
            cornerradius=6
        ),
        text=[f"{v:.1f}" for v in dados["score_medio"]],
        textposition="outside",
        textfont=dict(size=12, color=RADAR_DARK, family="Inter, sans-serif"),
        customdata=dados[["qtd", "desconto_medio", "preco_medio"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score médio: <b>%{x:.1f}</b><br>"
            "Oportunidades: <b>%{customdata[0]:.0f}</b><br>"
            "Desconto médio: <b>%{customdata[1]:.1f}%</b><br>"
            "Preço médio: <b>R$ %{customdata[2]:,.0f}</b><extra></extra>"
        ),
        name=""
    ))

    # Linha de média vertical
    fig.add_vline(
        x=media,
        line=dict(color=RADAR_ORANGE, width=1.5, dash="dot"),
        annotation_text=f"  média {media:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color=RADAR_ORANGE)
    )

    n = len(dados)
    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="Top 10 bairros · score médio", font=dict(size=16, color=RADAR_DARK), x=0),
        height=max(380, n * 42 + 80),
        showlegend=False,
        xaxis=dict(**XAXIS_STYLE, title="Score médio"),
        yaxis=dict(**{**YAXIS_STYLE, "showgrid": False, "title": "", "tickfont": dict(size=12)}),
        bargap=0.3,
        margin=dict(l=12, r=60, t=50, b=20)
    )

    return fig


def grafico_score_componentes(df):
    """
    Gráfico de barras: Score médio por componente.
    Melhorias: cor distinta por componente, rótulos, hover.
    """
    componentes = ["Preço", "Imagem", "Área", "Dados", "Duplicidade"]
    colunas     = ["score_preco", "score_imagem", "score_area", "score_dados", "score_duplicidade"]
    cores_comp  = [RADAR_GREEN, RADAR_BLUE_MID, RADAR_ORANGE, "#8b5cf6", "#06b6d4"]

    valores = [df[c].mean() for c in colunas]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=componentes,
        y=valores,
        marker=dict(
            color=cores_comp,
            line=dict(width=0),
            cornerradius=8
        ),
        text=[f"{v:.1f}" for v in valores],
        textposition="outside",
        textfont=dict(size=13, color=RADAR_DARK, family="Inter, sans-serif"),
        hovertemplate="<b>%{x}</b><br>Score médio: <b>%{y:.1f}</b><extra></extra>",
        name=""
    ))

    media_geral = sum(valores) / len(valores)
    fig.add_hline(
        y=media_geral,
        line=dict(color=RADAR_MUTED, width=1.2, dash="dot"),
        annotation_text=f"  média {media_geral:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color=RADAR_MUTED)
    )

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="Score médio por componente", font=dict(size=16, color=RADAR_DARK), x=0),
        height=420,
        showlegend=False,
        xaxis=dict(**XAXIS_STYLE, title=""),
        yaxis=dict(**YAXIS_STYLE, title="Score médio", range=[0, max(valores) * 1.20]),
        bargap=0.40,
        margin=MARGIN_DEFAULT
    )

    return fig


def grafico_top_bairros_regional(df, cor_por="cidade"):
    """
    Gráfico de barras: top bairros por score médio (aba Região), colorido por cidade.
    """
    df = df.copy()
    df["cidade"] = df["cidade"].apply(normalizar_cidade)
    dados = (
        df.groupby(["cidade", "bairro"], as_index=False)
        .agg(
            qtd=("id_imovel", "count"),
            score_medio=("score_oportunidade", "mean"),
            desconto_medio=("percentual_abaixo_mediana", "mean"),
            possiveis_dup=("possivel_duplicado", "sum")
        )
        .sort_values("score_medio", ascending=False)
        .head(20)
    )

    if dados.empty:
        return None

    cidades_unicas = dados["cidade"].unique()
    paleta = [RADAR_GREEN, RADAR_BLUE_MID, RADAR_ORANGE, "#8b5cf6", "#06b6d4",
              "#ec4899", "#f59e0b", "#10b981", "#ef4444", "#6366f1"]
    cor_map = {c: paleta[i % len(paleta)] for i, c in enumerate(cidades_unicas)}
    cores = [cor_map[c] for c in dados["cidade"]]

    media = dados["score_medio"].mean()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dados["bairro"],
        y=dados["score_medio"],
        marker=dict(color=cores, line=dict(width=0), cornerradius=8),
        text=[f"{v:.1f}" for v in dados["score_medio"]],
        textposition="outside",
        textfont=dict(size=11, color=RADAR_DARK),
        customdata=dados[["qtd", "desconto_medio", "possiveis_dup", "cidade"]].values,
        hovertemplate=(
            "<b>%{x}</b> · %{customdata[3]}<br>"
            "Score médio: <b>%{y:.1f}</b><br>"
            "Oportunidades: <b>%{customdata[0]:.0f}</b><br>"
            "Desconto médio: <b>%{customdata[1]:.1f}%</b><br>"
            "Possíveis duplicados: <b>%{customdata[2]:.0f}</b><extra></extra>"
        ),
        name=""
    ))

    fig.add_hline(
        y=media,
        line=dict(color=RADAR_ORANGE, width=1.5, dash="dot"),
        annotation_text=f"  média {media:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color=RADAR_ORANGE)
    )

    # Legenda manual por cidade
    for cidade, cor in cor_map.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=cor, symbol="square"),
            name=cidade,
            showlegend=True
        ))

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="Top bairros por score médio", font=dict(size=16, color=RADAR_DARK), x=0),
        height=460,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(**XAXIS_STYLE, title="", tickangle=-30),
        yaxis=dict(**YAXIS_STYLE, title="Score médio", range=[0, dados["score_medio"].max() * 1.18]),
        bargap=0.35,
        margin=dict(l=12, r=60, t=80, b=60)
    )

    return fig


def grafico_volume_por_bairro(df):
    """
    Gráfico de barras: volume de oportunidades por bairro, colorido por cidade.
    """
    df = df.copy()
    df["cidade"] = df["cidade"].apply(normalizar_cidade)
    dados = (
        df.groupby(["cidade", "bairro"], as_index=False)
        .agg(qtd=("id_imovel", "count"), score_medio=("score_oportunidade", "mean"))
        .sort_values("qtd", ascending=False)
        .head(20)
    )

    if dados.empty:
        return None

    cidades_unicas = dados["cidade"].unique()
    paleta = [RADAR_GREEN, RADAR_BLUE_MID, RADAR_ORANGE, "#8b5cf6", "#06b6d4",
              "#ec4899", "#f59e0b", "#10b981", "#ef4444", "#6366f1"]
    cor_map = {c: paleta[i % len(paleta)] for i, c in enumerate(cidades_unicas)}
    cores = [cor_map[c] for c in dados["cidade"]]

    media = dados["qtd"].mean()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dados["bairro"],
        y=dados["qtd"],
        marker=dict(color=cores, line=dict(width=0), cornerradius=8),
        text=[str(int(v)) for v in dados["qtd"]],
        textposition="outside",
        textfont=dict(size=11, color=RADAR_DARK),
        customdata=dados[["score_medio", "cidade"]].values,
        hovertemplate=(
            "<b>%{x}</b> · %{customdata[1]}<br>"
            "Oportunidades: <b>%{y}</b><br>"
            "Score médio: <b>%{customdata[0]:.1f}</b><extra></extra>"
        ),
        name=""
    ))

    fig.add_hline(
        y=media,
        line=dict(color=RADAR_ORANGE, width=1.5, dash="dot"),
        annotation_text=f"  média {media:.0f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color=RADAR_ORANGE)
    )

    for cidade, cor in cor_map.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=cor, symbol="square"),
            name=cidade,
            showlegend=True
        ))

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="Volume de oportunidades por bairro", font=dict(size=16, color=RADAR_DARK), x=0),
        height=460,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(**XAXIS_STYLE, title="", tickangle=-30),
        yaxis=dict(**YAXIS_STYLE, title="Qtd. de oportunidades"),
        bargap=0.35,
        margin=dict(l=12, r=60, t=80, b=60)
    )

    return fig


def render_oportunidade_card(row):
    titulo = texto_limpo(row.get("titulo"), "Imóvel sem título")
    if len(titulo) > 72:
        titulo = titulo[:69] + "..."

    render_imagem_imovel(row.get("imagem_principal_url"))

    classificacao_card = row.get(
        "classificacao_final_radar",
        row.get("classificacao_oportunidade")
    )
    score_card = row.get(
        "score_final_radar",
        row.get("score_oportunidade", 0)
    )

    badge = badge_classificacao(classificacao_card)

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin:2px 0 10px 0;">
            <span class="{badge}">{texto_limpo(classificacao_card, "Sem oportunidade")}</span>
            <span style="width:48px;height:48px;border-radius:999px;
                         border:3px solid #22c55e;background:#f0fdf4;
                         color:#166534;font-weight:900;font-size:18px;
                         display:flex;align-items:center;justify-content:center;">
                {float(score_card):.0f}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"#### {titulo}")
    st.caption(f"{texto_limpo(row.get('cidade'))} • {texto_limpo(row.get('bairro'))}")
    st.caption(f"{texto_limpo(row.get('tipo_imovel'))} • {texto_limpo(row.get('finalidade'))}")
    st.markdown(f"Comparação: **{texto_limpo(row.get('criterio_comparacao'))}**")

    if "liquidez_bairro" in row.index or "nivel_valorizacao" in row.index:
        st.caption(
            f"🏙️ Liquidez bairro: {texto_limpo(row.get('liquidez_bairro'), 'N/I')} • "
            f"Perfil: {texto_limpo(row.get('perfil_bairro'), 'N/I')} • "
            f"Valorização: {texto_limpo(row.get('nivel_valorizacao'), 'N/I')}"
        )

    if "liquidez_real" in row.index:
        st.caption(
            f"📈 Liquidez real: {texto_limpo(row.get('liquidez_real'), 'N/I')} • "
            f"Movimento: {texto_limpo(row.get('classificacao_movimento'), 'N/I')}"
        )

    st.markdown(
        f"""
        <div style="font-size:30px;font-weight:900;color:#0f172a;margin-top:12px;">
            {moeda(row.get("preco_anunciado_corrigido", row.get("preco_anunciado")))}
        </div>
        <div style="font-size:13px;color:#64748b;margin-bottom:10px;">
            {moeda(row.get("preco_m2"))}/m²
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(f"{percentual(row.get('percentual_abaixo_mediana'))} abaixo da mediana")

    if bool(row.get("possivel_duplicado")):
        if bool(row.get("menor_preco_entre_similares")):
            st.success(f"Menor preço entre {row.get('qtd_anuncios_similares', 0):.0f} anúncios similares")
        else:
            st.warning(f"Possível duplicado: existe similar {moeda(row.get('diferenca_para_menor_preco'))} mais barato")

    with st.expander("Ver composição"):
        st.write(f"Score Radar final: **{float(score_card):.0f} pts**")
        st.write(f"Preço: **{row.get('score_preco', 0):.0f} pts**")
        st.write(f"Imagem: **{row.get('score_imagem', 0):.0f} pts**")
        st.write(f"Área: **{row.get('score_area', 0):.0f} pts**")
        st.write(f"Dados: **{row.get('score_dados', 0):.0f} pts**")
        st.write(f"Duplicidade: **{row.get('score_duplicidade', 0):.0f} pts**")
        if "score_bairro" in row.index:
            st.write(f"Bairro: **{row.get('score_bairro', 0):.0f} pts**")
        if "score_liquidez_real" in row.index:
            st.write(f"Liquidez real: **{row.get('score_liquidez_real', 0):.0f} pts**")
        if "score_oportunidade_tecnico" in row.index:
            st.write(f"Score técnico original: **{row.get('score_oportunidade_tecnico', 0):.0f} pts**")
        st.write(texto_limpo(row.get("motivo_oportunidade"), "Sem motivo identificado."))
        if "resumo_bairro" in row.index:
            st.write(texto_limpo(row.get("resumo_bairro"), "Sem resumo de bairro."))
        if "resumo_liquidez" in row.index:
            st.write(texto_limpo(row.get("resumo_liquidez"), "Sem resumo de liquidez."))




def render_card_oportunidade_grid(row):
    """
    Card compacto para a aba Oportunidades.
    Usa componentes nativos do Streamlit para evitar HTML bruto aparecendo na tela.
    """
    titulo = texto_limpo(row.get("titulo"), "Imóvel sem título")
    if len(titulo) > 62:
        titulo = titulo[:59] + "..."

    render_imagem_imovel(row.get("imagem_principal_url"))

    badge = badge_classificacao(row.get("classificacao_oportunidade"))
    score = row.get("score_oportunidade", 0)

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin:2px 0 8px 0;">
            <span class="{badge}">{texto_limpo(row.get("classificacao_oportunidade"), "Sem oportunidade")}</span>
            <span style="background:#f7fee7;border:2px solid #22c55e;border-radius:999px;
                         color:#166534;font-weight:900;font-size:13px;padding:6px 9px;">
                {score:.0f}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"### {titulo}")
    st.caption(f"📍 {texto_limpo(row.get('cidade'))} • {texto_limpo(row.get('bairro'))}")

    area = row.get("area_total_m2", 0)
    try:
        area_txt = f"{float(area):,.0f} m²".replace(",", ".") if float(area) > 0 else "Área não informada"
    except Exception:
        area_txt = "Área não informada"

    st.markdown(
        f"""
        <div style="font-size:28px;font-weight:900;color:#0f172a;margin-top:8px;line-height:1;">
            {moeda_abreviado(row.get("preco_anunciado_corrigido", row.get("preco_anunciado")))}
        </div>
        <div style="font-size:13px;color:#64748b;margin-top:6px;margin-bottom:8px;">
            {area_txt} • {texto_limpo(row.get("tipo_imovel"))}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info(f"↓ {percentual(row.get('percentual_abaixo_mediana'))} abaixo da mediana")

    if "liquidez_bairro" in row.index or "nivel_valorizacao" in row.index:
        st.caption(
            f"🏙️ Liquidez: {texto_limpo(row.get('liquidez_bairro'), 'N/I')} • "
            f"Valorização: {texto_limpo(row.get('nivel_valorizacao'), 'N/I')}"
        )

    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"{moeda(row.get('preco_m2'))}/m²")
    with c2:
        st.caption(f"{texto_limpo(row.get('finalidade'))}")

    if bool(row.get("possivel_duplicado")):
        if bool(row.get("menor_preco_entre_similares")):
            st.success(f"Menor preço entre {row.get('qtd_anuncios_similares', 0):.0f} similares")
        else:
            st.warning("Possível duplicado")

    if pd.notna(row.get("url_anuncio")) and str(row.get("url_anuncio")).startswith("http"):
        st.link_button("Ver anúncio ↗", row["url_anuncio"], use_container_width=True)


def preparar_inteligencia_regional(df):
    """
    Consolida métricas por bairro/cidade para a aba Região.
    """
    if df.empty:
        return pd.DataFrame()

    dados = df.copy()
    dados["cidade"] = dados["cidade"].apply(normalizar_cidade)
    dados["bairro"] = dados["bairro"].apply(lambda x: texto_limpo(x, "Não informado"))

    regional = (
        dados
        .groupby(["cidade", "bairro"], as_index=False)
        .agg(
            qtd_imoveis=("id_imovel", "count"),
            score_medio=("score_oportunidade", "mean"),
            desconto_medio=("percentual_abaixo_mediana", "mean"),
            preco_m2_medio=("preco_m2", "mean"),
            preco_medio=("preco_anunciado_corrigido", "mean"),
            anuncios_similares=("qtd_anuncios_similares", "sum"),
            possiveis_duplicados=("possivel_duplicado", "sum")
        )
    )

    regional["regiao"] = regional["bairro"] + " · " + regional["cidade"]
    regional["score_medio"] = regional["score_medio"].round(1)
    regional["desconto_medio"] = regional["desconto_medio"].round(1)
    regional["preco_m2_medio"] = regional["preco_m2_medio"].round(0)
    regional["preco_medio"] = regional["preco_medio"].round(0)

    return regional


def grafico_ranking_bairros_executivo(regional):
    """
    Ranking horizontal executivo dos melhores bairros por score médio.
    """
    dados = (
        regional
        .sort_values(["score_medio", "qtd_imoveis"], ascending=[False, False])
        .head(10)
        .sort_values("score_medio", ascending=True)
        .copy()
    )

    if dados.empty:
        return None

    fig = go.Figure()

    max_score = dados["score_medio"].max()
    cores = [
        f"rgba(21,128,61,{0.35 + 0.65 * (v / max_score):.2f})"
        for v in dados["score_medio"]
    ]

    fig.add_trace(go.Bar(
        y=dados["regiao"],
        x=dados["score_medio"],
        orientation="h",
        marker=dict(color=cores, line=dict(width=0), cornerradius=7),
        text=[f"{v:.1f}" for v in dados["score_medio"]],
        textposition="outside",
        textfont=dict(size=12, color=RADAR_DARK),
        customdata=dados[["qtd_imoveis", "desconto_medio", "preco_m2_medio", "preco_medio"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score médio: <b>%{x:.1f}</b><br>"
            "Imóveis: <b>%{customdata[0]:.0f}</b><br>"
            "Desconto médio: <b>%{customdata[1]:.1f}%</b><br>"
            "Preço médio m²: <b>R$ %{customdata[2]:,.0f}</b><br>"
            "Preço médio: <b>R$ %{customdata[3]:,.0f}</b><extra></extra>"
        ),
        name=""
    ))

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="🏆 Top 10 bairros por score médio", font=dict(size=17, color=RADAR_DARK), x=0),
        height=460,
        showlegend=False,
        xaxis=dict(**XAXIS_STYLE, title="Score médio", range=[0, max(100, dados["score_medio"].max() * 1.14)]),
        yaxis=dict(**{**YAXIS_STYLE, "showgrid": False, "title": "", "tickfont": dict(size=12)}),
        margin=dict(l=12, r=70, t=54, b=20)
    )

    return fig


def grafico_matriz_oportunidade_bairro(regional):
    """
    Matriz executiva:
    X = desconto médio
    Y = score médio
    tamanho = quantidade de imóveis.
    """
    dados = regional.copy()

    if dados.empty:
        return None

    dados["tamanho_bolha"] = dados["qtd_imoveis"].clip(lower=3, upper=dados["qtd_imoveis"].quantile(0.90))

    fig = px.scatter(
        dados,
        x="desconto_medio",
        y="score_medio",
        size="tamanho_bolha",
        color="cidade",
        hover_name="regiao",
        hover_data={
            "qtd_imoveis": True,
            "desconto_medio": ":.1f",
            "score_medio": ":.1f",
            "preco_m2_medio": ":,.0f",
            "preco_medio": ":,.0f",
            "tamanho_bolha": False
        },
        text="bairro",
        size_max=36,
        color_discrete_sequence=[
            RADAR_GREEN, RADAR_BLUE_MID, RADAR_ORANGE, "#8b5cf6",
            "#06b6d4", "#ec4899", "#f59e0b"
        ],
        labels={
            "desconto_medio": "Desconto médio (%)",
            "score_medio": "Score médio",
            "cidade": "Cidade"
        },
        title="📈 Matriz de oportunidade por bairro"
    )

    desconto_ref = dados["desconto_medio"].median()
    score_ref = dados["score_medio"].median()

    fig.add_vline(x=desconto_ref, line=dict(color=RADAR_MUTED, width=1.2, dash="dot"))
    fig.add_hline(y=score_ref, line=dict(color=RADAR_MUTED, width=1.2, dash="dot"))

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=10),
        marker=dict(line=dict(width=1, color="white"), opacity=0.82)
    )

    fig.update_layout(
        **CHART_LAYOUT_BASE,
        title=dict(text="📈 Matriz de oportunidade por bairro", font=dict(size=17, color=RADAR_DARK), x=0),
        height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(**XAXIS_STYLE, title="Desconto médio (%)"),
        yaxis=dict(**YAXIS_STYLE, title="Score médio"),
        margin=dict(l=12, r=12, t=78, b=20)
    )

    return fig


def tabela_regional_executiva(regional):
    """
    Prepara tabela final da aba regional com colunas orientadas a decisão.
    """
    tabela = regional.copy()
    tabela = tabela.sort_values(["score_medio", "desconto_medio", "qtd_imoveis"], ascending=[False, False, False])

    tabela["preco_m2_medio"] = tabela["preco_m2_medio"].apply(moeda)
    tabela["preco_medio"] = tabela["preco_medio"].apply(moeda)
    tabela["desconto_medio"] = tabela["desconto_medio"].apply(percentual)

    tabela = tabela.rename(columns={
        "bairro": "Bairro",
        "cidade": "Cidade",
        "qtd_imoveis": "Imóveis",
        "score_medio": "Score médio",
        "desconto_medio": "Desconto médio",
        "preco_m2_medio": "Preço médio m²",
        "preco_medio": "Preço médio",
        "anuncios_similares": "Anúncios similares",
        "possiveis_duplicados": "Possíveis duplicados"
    })

    return tabela[
        [
            "Bairro",
            "Cidade",
            "Score médio",
            "Desconto médio",
            "Imóveis",
            "Preço médio m²",
            "Preço médio",
            "Anúncios similares",
            "Possíveis duplicados"
        ]
    ]




def criar_contexto_ia(df_contexto, limite=80):
    """
    Gera um contexto compacto para a IA responder com base nos imóveis filtrados.
    Mantém apenas as colunas relevantes para reduzir custo e ruído.
    """
    if df_contexto.empty:
        return "Sem dados disponíveis nos filtros atuais."

    colunas_contexto = [
        "titulo",
        "cidade",
        "bairro",
        "tipo_imovel",
        "finalidade",
        "preco_anunciado_corrigido",
        "area_total_m2",
        "preco_m2",
        "mediana_preco_m2_regiao",
        "percentual_abaixo_mediana",
        "score_oportunidade",
        "score_oportunidade_tecnico",
        "score_final_radar",
        "classificacao_oportunidade",
        "classificacao_final_radar",
        "criterio_comparacao",
        "qtd_imoveis_regiao",
        "motivo_oportunidade",
        "liquidez_bairro",
        "perfil_bairro",
        "nivel_valorizacao",
        "score_bairro",
        "resumo_bairro",
        "liquidez_real",
        "score_liquidez_real",
        "taxa_absorcao_pct",
        "classificacao_movimento",
        "resumo_liquidez",
        "percentual_queda_preco",
        "dias_anunciado",
        "sinal_negociacao",
        "url_anuncio"
    ]

    colunas_existentes = [c for c in colunas_contexto if c in df_contexto.columns]

    base = (
        df_contexto[colunas_existentes]
        .sort_values("score_oportunidade", ascending=False)
        .head(limite)
        .copy()
    )

    for col in ["preco_anunciado_corrigido", "preco_m2", "mediana_preco_m2_regiao"]:
        if col in base.columns:
            base[col] = base[col].apply(lambda x: float(x) if pd.notna(x) else None)

    return base.to_csv(index=False)


def criar_contexto_bairros_ia(df_bairros, df_filtros, limite=40):
    """
    Gera contexto agregado por bairro para a IA.
    Filtra a mart de bairros pelas cidades/bairros presentes no filtro atual.
    """
    if df_bairros is None or df_bairros.empty:
        return "Sem dados agregados por bairro disponíveis."

    base = df_bairros.copy()

    if df_filtros is not None and not df_filtros.empty:
        cidades_filtro = df_filtros["cidade"].dropna().unique().tolist() if "cidade" in df_filtros.columns else []
        bairros_filtro = df_filtros["bairro"].dropna().unique().tolist() if "bairro" in df_filtros.columns else []

        if cidades_filtro:
            base = base[base["cidade"].isin(cidades_filtro)].copy()

        if bairros_filtro:
            base = base[base["bairro"].isin(bairros_filtro)].copy()

    colunas = [
        "cidade",
        "bairro",
        "qtd_imoveis",
        "preco_medio",
        "preco_m2_medio",
        "preco_m2_mediano",
        "desconto_medio",
        "score_medio",
        "score_maximo",
        "qtd_oportunidades_fortes",
        "qtd_oportunidades_medias",
        "qtd_com_imagem",
        "data_ultima_coleta",
        "liquidez_bairro",
        "perfil_bairro",
        "nivel_valorizacao",
        "score_bairro",
        "resumo_bairro"
    ]

    colunas = [c for c in colunas if c in base.columns]

    base = (
        base[colunas]
        .sort_values(["score_medio", "desconto_medio", "qtd_imoveis"], ascending=[False, False, False])
        .head(limite)
        .copy()
    )

    return base.to_csv(index=False)


def perguntar_vertex_ai(pergunta, df_contexto, df_bairros_contexto=None):
    """
    Consulta o Gemini via Vertex AI usando as credenciais do Cloud Run/ADC.
    A função tenta mais de um modelo para evitar quebra quando uma versão específica
    não está disponível no projeto, região ou conta de serviço.
    """
    if not VERTEX_AVAILABLE:
        return (
            "A biblioteca google-cloud-aiplatform não está instalada no container. "
            "Adicione `google-cloud-aiplatform` no requirements.txt, faça novo build e rode novamente."
        )

    if not pergunta or not pergunta.strip():
        return "Digite uma pergunta para a IA analisar."

    if df_contexto is None or df_contexto.empty:
        return "Não há imóveis nos filtros atuais para analisar. Ajuste os filtros e tente novamente."

    contexto = criar_contexto_ia(df_contexto)
    contexto_bairros = criar_contexto_bairros_ia(df_bairros_contexto, df_contexto)

    resumo_filtros = {
        "total_imoveis_filtrados": int(len(df_contexto)),
        "cidades": sorted(df_contexto["cidade"].dropna().unique().tolist()) if "cidade" in df_contexto.columns else [],
        "bairros": sorted(df_contexto["bairro"].dropna().unique().tolist())[:30] if "bairro" in df_contexto.columns else [],
        "tipos": sorted(df_contexto["tipo_imovel"].dropna().unique().tolist()) if "tipo_imovel" in df_contexto.columns else [],
        "score_maximo": float(df_contexto["score_oportunidade"].max()) if len(df_contexto) and "score_oportunidade" in df_contexto.columns else 0,
        "score_medio": float(df_contexto["score_oportunidade"].mean()) if len(df_contexto) and "score_oportunidade" in df_contexto.columns else 0,
        "desconto_medio": float(df_contexto["percentual_abaixo_mediana"].mean()) if len(df_contexto) and "percentual_abaixo_mediana" in df_contexto.columns else 0
    }

    prompt = f"""
Você é um analista sênior de inteligência imobiliária do produto Radar Imobiliário.

Regras obrigatórias:
1. Responda em português do Brasil.
2. Use somente os dados fornecidos no contexto.
3. Não invente bairros, preços, scores, cidades ou imóveis.
4. Quando não houver dados suficientes, diga claramente.
5. Responda como consultor de negócio, não como programador.
6. Priorize recomendações práticas para investidor, imobiliária ou comprador.
7. Cite os principais critérios usados: score, desconto, preço/m², bairro, cidade e quantidade de registros.
8. Se fizer ranking, limite a no máximo 5 itens.
9. Seja direto e executivo.

Resumo dos filtros atuais:
{resumo_filtros}

Top imóveis disponíveis em CSV:
{contexto}

Resumo agregado por bairro em CSV:
{contexto_bairros}

Pergunta do usuário:
{pergunta}

Entregue uma resposta objetiva, com:
- diagnóstico curto;
- principais evidências dos dados;
- recomendação prática;
- cuidados/limitações.
"""

    erros = []

    for modelo in VERTEX_FALLBACK_MODELS:
        try:
            vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)
            model = GenerativeModel(modelo)
            resposta = model.generate_content(prompt)

            texto = getattr(resposta, "text", None)
            if texto and str(texto).strip():
                return str(texto).strip()

            candidatos = getattr(resposta, "candidates", None)
            if candidatos:
                partes_texto = []
                for candidato in candidatos:
                    conteudo = getattr(candidato, "content", None)
                    partes = getattr(conteudo, "parts", None) if conteudo else None
                    if partes:
                        for parte in partes:
                            texto_parte = getattr(parte, "text", None)
                            if texto_parte:
                                partes_texto.append(texto_parte)

                if partes_texto:
                    return "\n".join(partes_texto).strip()

            erros.append(f"{modelo}: resposta vazia ou sem texto retornado")

        except Exception as e:
            erros.append(f"{modelo}: {str(e)}")
            continue

    return (
        "Não consegui consultar a IA pela Vertex AI.\n\n"
        f"Projeto: {PROJECT_ID}\n"
        f"Região: {VERTEX_LOCATION}\n"
        f"Modelos tentados: {', '.join(VERTEX_FALLBACK_MODELS)}\n\n"
        "Últimos erros:\n- " + "\n- ".join(erros[-3:]) + "\n\n"
        "Verifique se a API Vertex AI está habilitada, se a Service Account do Cloud Run tem a permissão "
        "Vertex AI User e se o requirements.txt contém google-cloud-aiplatform."
    )

def perguntas_sugeridas_ia():
    return [
        "Quais são os melhores bairros para investir com os filtros atuais?",
        "Quais imóveis parecem mais abaixo do mercado?",
        "Onde existe maior desconto médio e maior score?",
        "Qual cidade está com melhores oportunidades agora?",
        "Quais cuidados eu deveria ter antes de negociar esses imóveis?",
        "Monte um resumo executivo para apresentar a uma imobiliária."
    ]


# ─── CARREGAMENTO DE DADOS ────────────────────────────────────────────────────
df = carregar_dados()
df_bairros_ia = carregar_bairros_inteligencia()

# Mantém somente anúncios com URL de imagem válida.
# Isso evita cards com ícone quebrado ou anúncios sem imagem no app.
if "imagem_principal_url" in df.columns:
    df["imagem_principal_url"] = df["imagem_principal_url"].apply(tratar_url_imagem)
    df = df[df["imagem_principal_url"].notna()].copy()

# Mantém o score técnico original e passa a usar o score final como Score Radar principal
if "score_oportunidade" in df.columns:
    df["score_oportunidade_tecnico"] = df["score_oportunidade"]

if "classificacao_oportunidade" in df.columns:
    df["classificacao_oportunidade_tecnica"] = df["classificacao_oportunidade"]

if "motivo_oportunidade" in df.columns:
    df["motivo_oportunidade_tecnico"] = df["motivo_oportunidade"]

if "score_final_radar" in df.columns:
    df["score_oportunidade"] = df["score_final_radar"]

if "classificacao_final_radar" in df.columns:
    df["classificacao_oportunidade"] = df["classificacao_final_radar"]

if "motivo_final_radar" in df.columns:
    df["motivo_oportunidade"] = df["motivo_final_radar"]

df["bairro"]                   = df["bairro"].apply(lambda x: texto_limpo(x, "Não informado"))
df["cidade"]                   = df["cidade"].apply(lambda x: texto_limpo(x, "Não informado"))
df["tipo_imovel"]              = df["tipo_imovel"].apply(lambda x: texto_limpo(x, "Não informado"))
df["finalidade"]               = df["finalidade"].apply(lambda x: texto_limpo(x, "Não informado"))
df["classificacao_oportunidade"] = df["classificacao_oportunidade"].apply(lambda x: texto_limpo(x, "Sem oportunidade"))
df["criterio_comparacao"]      = df["criterio_comparacao"].apply(lambda x: texto_limpo(x, "CIDADE"))
df["motivo_oportunidade"]      = df["motivo_oportunidade"].apply(lambda x: texto_limpo(x, "Sem motivo identificado."))
for col_texto, padrao_texto in {
    "liquidez_bairro": "Não identificada",
    "perfil_bairro": "Não identificado",
    "nivel_valorizacao": "Não identificada",
    "resumo_bairro": "Sem inteligência de bairro suficiente.",
    "classificacao_queda_preco": "Sem histórico de queda",
    "sinal_negociacao": "Não identificado",
    "classificacao_movimento": "Não identificado",
    "liquidez_real": "Dados insuficientes",
    "resumo_liquidez": "Sem dados suficientes de liquidez real.",
    "classificacao_final_radar": "Sem classificação final",
    "motivo_final_radar": "Sem motivo final identificado."
}.items():
    if col_texto in df.columns:
        df[col_texto] = df[col_texto].apply(lambda x, p=padrao_texto: texto_limpo(x, p))
df["chave_similaridade"]       = df["chave_similaridade"].apply(lambda x: texto_limpo(x, "SEM_CHAVE"))

for col in [
    "score_preco", "score_imagem", "score_area", "score_dados", "score_duplicidade",
    "score_oportunidade", "qtd_anuncios_similares", "menor_preco_grupo", "maior_preco_grupo",
    "media_preco_grupo", "diferenca_para_menor_preco", "percentual_acima_menor_preco_grupo",
    "percentual_abaixo_mediana", "preco_anunciado", "preco_m2", "mediana_preco_m2_regiao",
    "area_total_m2", "score_bairro",
    "score_oportunidade_tecnico", "score_final_radar", "preco_inicial", "preco_atual",
    "variacao_preco_absoluta", "percentual_queda_preco", "dias_anunciado", "qtd_quedas_preco",
    "qtd_novos", "qtd_removidos", "qtd_atualizados", "qtd_atualizacoes_preco",
    "taxa_absorcao_pct", "score_liquidez_real"
]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["preco_anunciado_corrigido"] = df.apply(
    lambda r: normalizar_preco(r["preco_anunciado"], r["finalidade"]), axis=1
)

# Remove anúncios de aluguel que entraram como venda.
# Exemplo de problema corrigido: cards com R$ 1.000 / R$ 7.500 sendo tratados como preço de venda.
df = filtrar_apenas_venda(df, preco_minimo=30000)

df["possivel_duplicado"]        = df["possivel_duplicado"].fillna(False).astype(bool)
df["menor_preco_entre_similares"] = df["menor_preco_entre_similares"].fillna(False).astype(bool)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("assets/logo_radar.png", use_container_width=True)
    except Exception:
        st.markdown("## 🏠 RADAR")
    st.markdown("## RADAR IMOBILIÁRIO")
    st.caption("Inteligência de mercado para melhores negócios")
    st.divider()
    st.markdown("### Filtros")

    cidades_lista = sorted(df["cidade"].dropna().unique())
    cidades = st.multiselect("Cidade", cidades_lista, default=cidades_lista)
    df_cidades = df[df["cidade"].isin(cidades)] if cidades else df.copy()

    bairros_lista = sorted(df_cidades["bairro"].dropna().unique())
    bairros = st.multiselect("Bairro", bairros_lista, default=bairros_lista)

    tipos_lista = sorted(df["tipo_imovel"].dropna().unique())
    tipos = st.multiselect("Tipo de imóvel", tipos_lista, default=tipos_lista)

    classificacoes_lista = sorted(df["classificacao_oportunidade"].dropna().unique())
    classificacoes = st.multiselect("Classificação", classificacoes_lista, default=classificacoes_lista)

    criterios_lista = sorted(df["criterio_comparacao"].dropna().unique())
    criterios = st.multiselect("Comparação", criterios_lista, default=criterios_lista)

    if "liquidez_bairro" in df.columns:
        liquidez_lista = sorted(df["liquidez_bairro"].dropna().unique())
        liquidez_filtro = st.multiselect("Liquidez do bairro", liquidez_lista, default=liquidez_lista)
    else:
        liquidez_filtro = []

    if "nivel_valorizacao" in df.columns:
        valorizacao_lista = sorted(df["nivel_valorizacao"].dropna().unique())
        valorizacao_filtro = st.multiselect("Valorização do bairro", valorizacao_lista, default=valorizacao_lista)
    else:
        valorizacao_filtro = []

    if "liquidez_real" in df.columns:
        liquidez_real_lista = sorted(df["liquidez_real"].dropna().unique())
        liquidez_real_filtro = st.multiselect("Liquidez real", liquidez_real_lista, default=liquidez_real_lista)
    else:
        liquidez_real_filtro = []

    filtro_duplicado = st.selectbox(
        "Duplicidade",
        ["Todos", "Somente possíveis duplicados", "Somente menor preço entre similares"]
    )

    score_minimo    = st.slider("Score mínimo", 0, 100, 0)
    desconto_minimo = st.slider("Desconto mínimo (%)", 0, 100, 0)

    st.divider()
    st.success("MVP funcional em Google Cloud")

# ─── FILTRO PRINCIPAL ─────────────────────────────────────────────────────────
df_filtrado = df[
    (df["cidade"].isin(cidades)) &
    (df["bairro"].isin(bairros)) &
    (df["tipo_imovel"].isin(tipos)) &
    (df["classificacao_oportunidade"].isin(classificacoes)) &
    (df["criterio_comparacao"].isin(criterios)) &
    (df["liquidez_bairro"].isin(liquidez_filtro) if "liquidez_bairro" in df.columns and liquidez_filtro else True) &
    (df["nivel_valorizacao"].isin(valorizacao_filtro) if "nivel_valorizacao" in df.columns and valorizacao_filtro else True) &
    (df["liquidez_real"].isin(liquidez_real_filtro) if "liquidez_real" in df.columns and liquidez_real_filtro else True) &
    (df["score_oportunidade"] >= score_minimo) &
    (df["percentual_abaixo_mediana"] >= desconto_minimo)
].copy()

if filtro_duplicado == "Somente possíveis duplicados":
    df_filtrado = df_filtrado[df_filtrado["possivel_duplicado"] == True].copy()
if filtro_duplicado == "Somente menor preço entre similares":
    df_filtrado = df_filtrado[df_filtrado["menor_preco_entre_similares"] == True].copy()

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div class="brand-box">
        <div class="logo-mark">⌖</div>
        <div>
            <div class="brand-title">RADAR</div>
            <div class="brand-subtitle">IMOBILIÁRIO</div>
        </div>
    </div>
    <div>
        <div class="header-title">
            Encontramos <span class="orange">oportunidades.</span><br>
            Você faz o <span class="green">melhor negócio.</span>
        </div>
        <div class="header-caption">
            Inteligência imobiliária orientada por dados em Google Cloud
        </div>
    </div>
    <div class="status-pill">MVP funcional • BigQuery + Cloud Run</div>
</div>
""", unsafe_allow_html=True)

# ─── KPIs ─────────────────────────────────────────────────────────────────────
kpi_imoveis = len(df_filtrado)
kpi_cidades = df_filtrado["cidade"].nunique()
kpi_bairros = df_filtrado["bairro"].nunique()
kpi_desconto = df_filtrado["percentual_abaixo_mediana"].mean() if len(df_filtrado) else 0
kpi_score    = df_filtrado["score_oportunidade"].max() if len(df_filtrado) else 0
kpi_dup      = int(df_filtrado["possivel_duplicado"].sum()) if len(df_filtrado) else 0

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Oportunidades de Mercado</div>
        <div class="kpi-value">{kpi_imoveis:,}</div>
        <div class="kpi-note">selecionadas pela IA</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Cidades monitoradas</div>
        <div class="kpi-value">{kpi_cidades}</div>
        <div class="kpi-note">ativas</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Bairros mapeados</div>
        <div class="kpi-value">{kpi_bairros}</div>
        <div class="kpi-note">com anúncios</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Desconto médio</div>
        <div class="kpi-value">{kpi_desconto:.1f}%</div>
        <div class="kpi-note">abaixo da mediana</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Maior score</div>
        <div class="kpi-value">{kpi_score:.0f}</div>
        <div class="kpi-note">Score Radar</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Possíveis duplicados</div>
        <div class="kpi-value">{kpi_dup}</div>
        <div class="kpi-note">anúncios similares</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── ABAS ─────────────────────────────────────────────────────────────────────
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Resumo", "🔥 Oportunidades", "🗺️ Mapa",
    "📍 Região", "🧠 Inteligência"
])

# ── ABA 1: RESUMO ─────────────────────────────────────────────────────────────
with aba1:
    st.markdown("""
    <div class="section-title">
        <div>
            <h2>Top oportunidades</h2>
            <p>Imóveis com maior potencial de negócio de acordo com o Score Radar.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    top5 = df_filtrado.sort_values("score_oportunidade", ascending=False).head(5)

    if top5.empty:
        st.warning("Nenhuma oportunidade encontrada com os filtros atuais.")
    else:
        cols = st.columns(5)
        for col, (_, row) in zip(cols, top5.iterrows()):
            with col:
                with st.container(border=True):
                    render_oportunidade_card(row)
                    if pd.notna(row.get("url_anuncio")) and str(row.get("url_anuncio")).startswith("http"):
                        st.link_button("Ver anúncio ↗", row["url_anuncio"], use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        fig = grafico_oportunidades_por_cidade(df_filtrado)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o gráfico de cidades.")

    with col_g2:
        fig = grafico_top_bairros_score(df_filtrado)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o ranking de bairros.")

# ── ABA 2: OPORTUNIDADES ──────────────────────────────────────────────────────
with aba2:
    st.markdown("### 🔥 Oportunidades")
    st.markdown(
        '<div class="op-filter-help">Cards com busca, filtros rápidos, ordenação e paginação. A planilha detalhada fica recolhida no final.</div>',
        unsafe_allow_html=True
    )

    busca_col, ordenacao_col = st.columns([3, 1])

    with busca_col:
        busca_oportunidade = st.text_input(
            "Buscar",
            placeholder="Buscar imóvel, bairro, cidade ou tipo...",
            label_visibility="collapsed"
        )

    with ordenacao_col:
        ordenar_por = st.selectbox(
            "Ordenar",
            ["Maior score", "Maior desconto", "Menor preço", "Maior preço"],
            label_visibility="collapsed"
        )

    filtro_classificacao = st.radio(
        "Classificação",
        ["Todos", "Oportunidade forte", "Oportunidade média", "Fraca / sem oportunidade"],
        horizontal=True,
        label_visibility="collapsed"
    )

    df_cards = df_filtrado.copy()

    if busca_oportunidade.strip():
        termo = busca_oportunidade.strip().lower()
        df_cards = df_cards[
            df_cards["titulo"].astype(str).str.lower().str.contains(termo, na=False) |
            df_cards["bairro"].astype(str).str.lower().str.contains(termo, na=False) |
            df_cards["cidade"].astype(str).str.lower().str.contains(termo, na=False) |
            df_cards["tipo_imovel"].astype(str).str.lower().str.contains(termo, na=False)
        ].copy()

    if filtro_classificacao == "Oportunidade forte":
        df_cards = df_cards[
            df_cards["classificacao_oportunidade"].astype(str).str.upper().str.contains("FORTE", na=False)
        ].copy()
    elif filtro_classificacao == "Oportunidade média":
        df_cards = df_cards[
            df_cards["classificacao_oportunidade"].astype(str).str.upper().str.contains("MEDIA|MÉDIA", regex=True, na=False)
        ].copy()
    elif filtro_classificacao == "Fraca / sem oportunidade":
        df_cards = df_cards[
            ~df_cards["classificacao_oportunidade"].astype(str).str.upper().str.contains("FORTE|MEDIA|MÉDIA", regex=True, na=False)
        ].copy()

    if ordenar_por == "Maior score":
        df_cards = df_cards.sort_values("score_oportunidade", ascending=False)
    elif ordenar_por == "Maior desconto":
        df_cards = df_cards.sort_values("percentual_abaixo_mediana", ascending=False)
    elif ordenar_por == "Menor preço":
        df_cards = df_cards.sort_values("preco_anunciado_corrigido", ascending=True)
    elif ordenar_por == "Maior preço":
        df_cards = df_cards.sort_values("preco_anunciado_corrigido", ascending=False)

    total_cards = len(df_cards)
    por_pagina = 6
    total_paginas = max(1, (total_cards + por_pagina - 1) // por_pagina)

    pag_col1, pag_col2, pag_col3 = st.columns([1, 1, 4])

    with pag_col1:
        pagina = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=1,
            step=1
        )

    with pag_col2:
        st.metric("Encontrados", total_cards)

    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    df_pagina = df_cards.iloc[inicio:fim]

    st.caption(f"Exibindo {len(df_pagina)} de {total_cards} imóveis encontrados • Página {pagina} de {total_paginas}")

    if df_pagina.empty:
        st.warning("Nenhuma oportunidade encontrada com os filtros atuais.")
    else:
        for i in range(0, len(df_pagina), 3):
            cols = st.columns(3)
            for col, (_, row) in zip(cols, df_pagina.iloc[i:i+3].iterrows()):
                with col:
                    with st.container(border=True):
                        render_card_oportunidade_grid(row)

    with st.expander("Ver planilha detalhada"):
        df_tabela = df_cards[[
            "titulo", "cidade", "bairro", "tipo_imovel", "finalidade",
            "preco_anunciado_corrigido", "area_total_m2", "preco_m2",
            "mediana_preco_m2_regiao", "percentual_abaixo_mediana", "criterio_comparacao",
            "possivel_duplicado", "menor_preco_entre_similares", "qtd_anuncios_similares",
            "menor_preco_grupo", "maior_preco_grupo", "diferenca_para_menor_preco",
            "score_preco", "score_imagem", "score_area", "score_dados", "score_duplicidade",
            "score_oportunidade", "classificacao_oportunidade", "liquidez_bairro", "perfil_bairro", "nivel_valorizacao", "score_bairro", "qtd_imagens",
            "motivo_oportunidade", "url_anuncio"
        ]].copy()

        for c in ["preco_anunciado_corrigido", "preco_m2", "mediana_preco_m2_regiao",
                  "menor_preco_grupo", "maior_preco_grupo", "diferenca_para_menor_preco"]:
            df_tabela[c] = df_tabela[c].apply(moeda)

        df_tabela["percentual_abaixo_mediana"] = df_tabela["percentual_abaixo_mediana"].apply(percentual)

        df_tabela = df_tabela.rename(columns={
            "titulo": "Imóvel", "cidade": "Cidade", "bairro": "Bairro",
            "tipo_imovel": "Tipo", "finalidade": "Finalidade",
            "preco_anunciado_corrigido": "Preço", "area_total_m2": "Área m²",
            "preco_m2": "Preço m²", "mediana_preco_m2_regiao": "Mediana Região",
            "percentual_abaixo_mediana": "Desconto", "criterio_comparacao": "Comparação",
            "possivel_duplicado": "Possível Duplicado", "menor_preco_entre_similares": "Menor Preço Similar",
            "qtd_anuncios_similares": "Qtd. Similares", "menor_preco_grupo": "Menor Preço Grupo",
            "maior_preco_grupo": "Maior Preço Grupo", "diferenca_para_menor_preco": "Diferença Menor Preço",
            "score_preco": "Score Preço", "score_imagem": "Score Imagem",
            "score_area": "Score Área", "score_dados": "Score Dados",
            "score_duplicidade": "Score Duplicidade", "score_oportunidade": "Score Final",
            "liquidez_bairro": "Liquidez Bairro", "perfil_bairro": "Perfil Bairro",
            "nivel_valorizacao": "Valorização Bairro", "score_bairro": "Score Bairro",
            "classificacao_oportunidade": "Classificação", "qtd_imagens": "Qtd. Imagens",
            "motivo_oportunidade": "Motivo", "url_anuncio": "Anúncio"
        })

        st.dataframe(df_tabela, use_container_width=True, hide_index=True, height=550)

# ── ABA 3: MAPA ───────────────────────────────────────────────────────────────
with aba3:
    st.markdown("### 🗺️ Mapa de oportunidades")

    df_mapa = df_filtrado[df_filtrado["latitude"].notna() & df_filtrado["longitude"].notna()].copy()

    if df_mapa.empty:
        st.warning("Nenhum imóvel com latitude e longitude.")
    else:
        fig = px.scatter_mapbox(
            df_mapa,
            lat="latitude", lon="longitude",
            color="classificacao_oportunidade",
            size="score_oportunidade",
            hover_name="titulo",
            hover_data={
                "cidade": True, "bairro": True,
                "preco_anunciado_corrigido": True, "preco_m2": True,
                "percentual_abaixo_mediana": True, "possivel_duplicado": True,
                "menor_preco_entre_similares": True, "qtd_anuncios_similares": True,
                "score_preco": True, "score_imagem": True, "score_area": True,
                "score_dados": True, "score_duplicidade": True,
                "latitude": False, "longitude": False
            },
            zoom=10, height=650
        )
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
        st.plotly_chart(fig, use_container_width=True)

# ── ABA 4: REGIÃO ─────────────────────────────────────────────────────────────
with aba4:
    st.markdown("### 📍 Inteligência regional")
    st.caption("Visão executiva dos bairros com maior potencial de negócio, desconto e volume de anúncios.")

    regional_base = preparar_inteligencia_regional(df_filtrado)

    if regional_base.empty:
        st.warning("Sem dados suficientes para análise regional.")
    else:
        st.markdown("#### Filtros regionais")

        filtro_col1, filtro_col2, filtro_col3, filtro_col4 = st.columns([2.2, 1.3, 1.3, 1.3])

        with filtro_col1:
            busca_regiao = st.text_input(
                "Buscar bairro ou cidade",
                placeholder="Ex: Centro, Portal, Boituva, Lagarto...",
                key="busca_regiao"
            )

        with filtro_col2:
            score_regiao_min = st.slider(
                "Score mínimo",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key="score_regiao_min"
            )

        with filtro_col3:
            desconto_regiao_min = st.slider(
                "Desconto mínimo (%)",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key="desconto_regiao_min"
            )

        with filtro_col4:
            volume_regiao_min = st.number_input(
                "Mín. imóveis",
                min_value=0,
                value=0,
                step=1,
                key="volume_regiao_min"
            )

        filtro_col5, filtro_col6, filtro_col7 = st.columns([1.4, 1.4, 2.2])

        cidades_regiao_lista = sorted(regional_base["cidade"].dropna().unique())
        with filtro_col5:
            cidades_regiao = st.multiselect(
                "Cidade",
                cidades_regiao_lista,
                default=cidades_regiao_lista,
                key="cidades_regiao"
            )

        with filtro_col6:
            ordenar_regiao = st.selectbox(
                "Ordenar ranking",
                [
                    "Maior score",
                    "Maior desconto",
                    "Maior volume",
                    "Menor preço m²",
                    "Mais anúncios similares"
                ],
                key="ordenar_regiao"
            )

        with filtro_col7:
            st.caption("Os filtros abaixo afetam os cards, gráficos e a tabela desta aba.")

        regional = regional_base.copy()

        if cidades_regiao:
            regional = regional[regional["cidade"].isin(cidades_regiao)].copy()

        if busca_regiao.strip():
            termo_regiao = busca_regiao.strip().lower()
            regional = regional[
                regional["bairro"].astype(str).str.lower().str.contains(termo_regiao, na=False) |
                regional["cidade"].astype(str).str.lower().str.contains(termo_regiao, na=False)
            ].copy()

        regional = regional[
            (regional["score_medio"] >= score_regiao_min) &
            (regional["desconto_medio"] >= desconto_regiao_min) &
            (regional["qtd_imoveis"] >= volume_regiao_min)
        ].copy()

        if ordenar_regiao == "Maior score":
            regional = regional.sort_values(["score_medio", "qtd_imoveis"], ascending=[False, False])
        elif ordenar_regiao == "Maior desconto":
            regional = regional.sort_values(["desconto_medio", "score_medio"], ascending=[False, False])
        elif ordenar_regiao == "Maior volume":
            regional = regional.sort_values(["qtd_imoveis", "score_medio"], ascending=[False, False])
        elif ordenar_regiao == "Menor preço m²":
            regional = regional.sort_values(["preco_m2_medio", "score_medio"], ascending=[True, False])
        elif ordenar_regiao == "Mais anúncios similares":
            regional = regional.sort_values(["anuncios_similares", "qtd_imoveis"], ascending=[False, False])

        st.caption(f"{len(regional)} bairros encontrados após os filtros.")

        if regional.empty:
            st.warning("Nenhum bairro encontrado com os filtros regionais atuais.")
        else:
            melhor_bairro = regional.sort_values(["score_medio", "qtd_imoveis"], ascending=[False, False]).iloc[0]
            maior_desconto = regional.sort_values(["desconto_medio", "score_medio"], ascending=[False, False]).iloc[0]
            maior_volume = regional.sort_values(["qtd_imoveis", "score_medio"], ascending=[False, False]).iloc[0]
            mais_duplicados = regional.sort_values(["anuncios_similares", "qtd_imoveis"], ascending=[False, False]).iloc[0]

            st.markdown(f"""
            <div class="regional-kpi-grid">
                <div class="regional-kpi-card">
                    <div class="regional-kpi-label">Melhor bairro por score</div>
                    <div class="regional-kpi-title">{melhor_bairro["bairro"]}</div>
                    <div class="regional-kpi-value regional-green">{melhor_bairro["score_medio"]:.1f}</div>
                    <div class="kpi-note">{melhor_bairro["cidade"]} • score médio</div>
                </div>
                <div class="regional-kpi-card">
                    <div class="regional-kpi-label">Maior desconto médio</div>
                    <div class="regional-kpi-title">{maior_desconto["bairro"]}</div>
                    <div class="regional-kpi-value regional-blue">{maior_desconto["desconto_medio"]:.1f}%</div>
                    <div class="kpi-note">{maior_desconto["cidade"]} • abaixo da mediana</div>
                </div>
                <div class="regional-kpi-card">
                    <div class="regional-kpi-label">Maior volume de imóveis</div>
                    <div class="regional-kpi-title">{maior_volume["bairro"]}</div>
                    <div class="regional-kpi-value regional-orange">{maior_volume["qtd_imoveis"]:.0f}</div>
                    <div class="kpi-note">{maior_volume["cidade"]} • imóveis encontrados</div>
                </div>
                <div class="regional-kpi-card">
                    <div class="regional-kpi-label">Mais anúncios similares</div>
                    <div class="regional-kpi-title">{mais_duplicados["bairro"]}</div>
                    <div class="regional-kpi-value regional-purple">{mais_duplicados["anuncios_similares"]:.0f}</div>
                    <div class="kpi-note">{mais_duplicados["cidade"]} • possíveis similares</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_r1, col_r2 = st.columns([1, 1.25])

            with col_r1:
                fig = grafico_ranking_bairros_executivo(regional)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            with col_r2:
                fig = grafico_matriz_oportunidade_bairro(regional)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📋 Ranking completo dos bairros")
            st.caption("Compare os principais indicadores por bairro para decidir onde aprofundar a análise.")

            st.dataframe(
                tabela_regional_executiva(regional),
                use_container_width=True,
                hide_index=True,
                height=460
            )

# ── ABA 5: INTELIGÊNCIA ───────────────────────────────────────────────────────
with aba5:
    st.markdown("### 🧠 Inteligência com IA")
    st.caption("Faça perguntas sobre os imóveis filtrados. A IA responde usando os dados carregados do BigQuery no contexto atual.")

    st.markdown(f"""
    <div class="ai-panel">
        <b>Modelo principal:</b> {VERTEX_MODEL} • <b>Região:</b> {VERTEX_LOCATION}<br>
        <span style="color:#64748b;font-size:13px;">
            A resposta considera os filtros aplicados na lateral: cidade, bairro, tipo, classificação, score e desconto.<br>
            Fallback automático: {", ".join(VERTEX_FALLBACK_MODELS)}
        </span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Imóveis no contexto", len(df_filtrado))

    with c2:
        st.metric("Cidades", df_filtrado["cidade"].nunique())

    with c3:
        desconto_ctx = df_filtrado["percentual_abaixo_mediana"].mean() if len(df_filtrado) else 0
        st.metric("Desconto médio", percentual(desconto_ctx))

    with c4:
        score_ctx = df_filtrado["score_oportunidade"].max() if len(df_filtrado) else 0
        st.metric("Maior score", f"{score_ctx:.0f}")

    st.markdown("#### Perguntas rápidas")

    sugestoes = perguntas_sugeridas_ia()
    q1, q2, q3 = st.columns(3)

    if "pergunta_ia_texto" not in st.session_state:
        st.session_state["pergunta_ia_texto"] = ""

    with q1:
        if st.button(sugestoes[0], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[0]
        if st.button(sugestoes[1], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[1]

    with q2:
        if st.button(sugestoes[2], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[2]
        if st.button(sugestoes[3], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[3]

    with q3:
        if st.button(sugestoes[4], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[4]
        if st.button(sugestoes[5], use_container_width=True):
            st.session_state["pergunta_ia_texto"] = sugestoes[5]

    pergunta = st.text_area(
        "Pergunte para a IA",
        value=st.session_state.get("pergunta_ia_texto", ""),
        placeholder="Ex: Quais bairros de Boituva têm melhores oportunidades para investimento?",
        height=110
    )

    col_btn1, col_btn2 = st.columns([1, 4])

    with col_btn1:
        perguntar = st.button("Perguntar para IA", type="primary", use_container_width=True)

    with col_btn2:
        st.caption("Dica: quanto mais específicos os filtros da lateral, melhor a resposta da IA.")

    if perguntar:
        if df_filtrado.empty:
            st.warning("Não há imóveis nos filtros atuais para enviar como contexto para a IA.")
        elif not pergunta or not pergunta.strip():
            st.warning("Digite uma pergunta ou selecione uma das perguntas rápidas.")
        else:
            with st.spinner("Analisando dados com Vertex AI..."):
                resposta_ia = perguntar_vertex_ai(pergunta, df_filtrado, df_bairros_ia)
                st.markdown("#### Resposta da IA")
                st.markdown(
                    f'<div class="ai-answer">{html.escape(resposta_ia).replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True
                )

    with st.expander("Ver dados enviados como contexto para a IA"):
        tab_imoveis_ctx, tab_bairros_ctx = st.tabs(["Imóveis", "Bairros"])

        with tab_imoveis_ctx:
            colunas_preview = [
                "titulo",
                "cidade",
                "bairro",
                "tipo_imovel",
                "preco_anunciado_corrigido",
                "preco_m2",
                "percentual_abaixo_mediana",
                "score_oportunidade",
                "classificacao_oportunidade",
                "liquidez_bairro",
                "nivel_valorizacao",
                "score_bairro"
            ]
            colunas_preview = [c for c in colunas_preview if c in df_filtrado.columns]
            st.dataframe(
                df_filtrado[colunas_preview].sort_values("score_oportunidade", ascending=False).head(80),
                use_container_width=True,
                hide_index=True,
                height=360
            )

        with tab_bairros_ctx:
            df_bairros_preview = df_bairros_ia.copy()

            if not df_filtrado.empty:
                cidades_preview = df_filtrado["cidade"].dropna().unique().tolist()
                bairros_preview = df_filtrado["bairro"].dropna().unique().tolist()

                if cidades_preview:
                    df_bairros_preview = df_bairros_preview[df_bairros_preview["cidade"].isin(cidades_preview)].copy()

                if bairros_preview:
                    df_bairros_preview = df_bairros_preview[df_bairros_preview["bairro"].isin(bairros_preview)].copy()

            st.dataframe(
                df_bairros_preview.sort_values(["score_medio", "desconto_medio"], ascending=[False, False]).head(80),
                use_container_width=True,
                hide_index=True,
                height=360
            )

st.markdown("""
<br>
<div style="text-align:center;color:#64748b;font-size:13px;">
Radar Imobiliário • MVP funcional em Google Cloud
</div>
""", unsafe_allow_html=True)
