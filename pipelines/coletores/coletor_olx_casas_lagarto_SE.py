import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# Coletor específico para CASAS à venda em Lagarto/SE.
# Usa a URL canônica da OLX para casas à venda em Lagarto/SE.
# Mantém o mesmo layout de colunas do coletor de terrenos para carregar na mesma raw_olx_historico.
BASE_URL = "https://www.olx.com.br/imoveis/venda/casas/estado-se/sergipe/outras-cidades/lagarto"

# IMPORTANTE:
# usar histórico separado para casas, para não marcar terrenos como removidos.
HISTORICAL_CSV = "output/imoveis_olx_casas_lagarto_historico.csv"

CIDADE_ALVO = "Lagarto"
ESTADO_ALVO = "SE"
MIN_PRECO_VENDA = 30000

TERMOS_ALUGUEL = re.compile(
    r"(aluguel|alugar|aluga\s*-?\s*se|loca[cç][aã]o|mensal|por\s+m[eê]s|para\s+alugar|/aluguel|para-alugar)",
    flags=re.IGNORECASE,
)


FIELDS = [
    "id_imovel",
    "titulo",
    "descricao",
    "tipo_imovel",
    "finalidade",
    "preco_anunciado",
    "condominio",
    "iptu",
    "area_total_m2",
    "area_construida_m2",
    "quartos",
    "banheiros",
    "vagas_garagem",
    "bairro",
    "cidade",
    "estado",
    "endereco_texto",
    "latitude",
    "longitude",
    "anunciante",
    "fonte",
    "url_anuncio",
    "imagem_principal_url",
    "imagens_urls",
    "qtd_imagens",
    "data_coleta",
    "ativo",
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def safe_image_url(value) -> str:
    if not value:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in ["url", "@id", "contentUrl", "src"]:
            if value.get(key):
                return str(value.get(key)).strip()

    return ""


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None

    matches = re.findall(r"R\$\s*[\d\.\,]+", text, flags=re.IGNORECASE)
    if not matches:
        return None

    return parse_money_value(matches[0])


def parse_money_value(text: str) -> Optional[float]:
    if not text:
        return None

    cleaned = re.sub(r"[^\d,\.]", "", str(text))

    if not cleaned:
        return None

    cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_all_prices(text: str) -> list[float]:
    if not text:
        return []

    valores = []
    matches = re.findall(r"R\$\s*[\d\.\,]+", text, flags=re.IGNORECASE)

    for match in matches:
        valor = parse_money_value(match)
        if valor is not None:
            valores.append(valor)

    return valores


def escolher_preco_venda(price_text: str, full_text: str, json_price=None) -> Optional[float]:
    """
    Extrai o preço de venda evitando pegar condomínio, IPTU, parcelas ou aluguel.
    Prioridade:
    1. preço do JSON-LD;
    2. bloco específico de preço do anúncio;
    3. primeiro valor do body acima do mínimo de venda.
    """
    if json_price not in (None, "", "None"):
        try:
            valor_json = float(json_price)
            if valor_json >= MIN_PRECO_VENDA:
                return valor_json
        except Exception:
            pass

    preco_bloco = parse_price(price_text) if price_text else None
    if preco_bloco is not None and preco_bloco >= MIN_PRECO_VENDA:
        return preco_bloco

    candidatos = [v for v in parse_all_prices(full_text) if v >= MIN_PRECO_VENDA]

    if candidatos:
        return candidatos[0]

    return preco_bloco


def parse_area(text: str) -> Optional[float]:
    if not text:
        return None

    matches = re.findall(r"(\d+(?:[\.,]\d+)?)\s*m²", text.lower())

    if not matches:
        return None

    try:
        return float(matches[0].replace(",", "."))
    except ValueError:
        return None


def parse_area_by_labels(labels: list[str], text: str) -> Optional[float]:
    """
    Busca área próxima de rótulos específicos.
    Útil para casas, onde podem existir área construída, área útil, área total e área do terreno.
    """
    if not text:
        return None

    text_lower = text.lower()

    for label in labels:
        pattern = rf"{label}\s*[:\-]?\s*(\d+(?:[\.,]\d+)?)\s*m²"
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", "."))
            except ValueError:
                continue

    return None


def extract_house_areas(full_text: str) -> tuple[Optional[float], Optional[float]]:
    """
    Para casas:
    - area_total_m2 tenta representar área do terreno/área total.
    - area_construida_m2 tenta representar área construída/útil.
    Se só existir uma área no anúncio, preenche area_total_m2 com ela.
    """
    area_construida = parse_area_by_labels(
        [
            "área construída",
            "area construida",
            "área útil",
            "area util",
            "área privativa",
            "area privativa",
            "construída",
            "construida",
        ],
        full_text,
    )

    area_total = parse_area_by_labels(
        [
            "área total",
            "area total",
            "área do terreno",
            "area do terreno",
            "terreno",
            "lote",
        ],
        full_text,
    )

    primeira_area = parse_area(full_text)

    if area_total is None:
        area_total = primeira_area

    if area_construida is None:
        area_construida = primeira_area

    return area_total, area_construida


def parse_int_feature(pattern: str, text: str) -> Optional[int]:
    if not text:
        return None

    match = re.search(pattern, text.lower())

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def parse_money_by_label(label: str, text: str) -> Optional[float]:
    pattern = rf"{label}\s*R\$\s*[\d\.\,]+"
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        return None

    return parse_price(match.group(0))


def normalize_tipo_imovel(title: str) -> str:
    t = (title or "").lower()

    if "casa" in t or "sobrado" in t or "residencial" in t:
        return "casa"
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "apart" in t:
        return "apartamento"
    if "chácara" in t or "chacara" in t:
        return "chacara"

    # Como este coletor já navega na categoria de casas, usamos casa como fallback.
    return "casa"


def extract_id_from_url(url: str) -> str:
    if not url:
        return ""

    match = re.search(r"-([0-9]{6,})$", url)
    if match:
        return match.group(1)

    match = re.search(r"([0-9]{6,})", url)
    if match:
        return match.group(1)

    return url


def get_row_unique_key(row: dict) -> str:
    id_imovel = str(row.get("id_imovel") or "").strip()
    url_anuncio = str(row.get("url_anuncio") or "").strip()

    if id_imovel:
        return f"id::{id_imovel}"
    if url_anuncio:
        return f"url::{url_anuncio}"

    return ""


def normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_float_str(value) -> str:
    if value in (None, "", "None"):
        return ""
    try:
        return f"{float(value):.6f}"
    except Exception:
        return str(value).strip()


def build_comparison_signature(row: dict) -> str:
    parts = []

    for field in FIELDS:
        if field in [
            "preco_anunciado",
            "condominio",
            "iptu",
            "area_total_m2",
            "area_construida_m2",
            "latitude",
            "longitude",
        ]:
            parts.append(normalize_float_str(row.get(field)))
        else:
            parts.append(normalize_text(row.get(field)))

    return "||".join(parts)


def get_changed_fields(old_row: dict, new_row: dict) -> str:
    changed = []

    for field in FIELDS:
        old_val = old_row.get(field)
        new_val = new_row.get(field)

        if field in [
            "preco_anunciado",
            "condominio",
            "iptu",
            "area_total_m2",
            "area_construida_m2",
            "latitude",
            "longitude",
        ]:
            if normalize_float_str(old_val) != normalize_float_str(new_val):
                changed.append(field)
        else:
            if normalize_text(old_val) != normalize_text(new_val):
                changed.append(field)

    return ", ".join(changed)


def save_csv(rows: list[dict], output_path: str) -> None:
    if not rows:
        raise ValueError("Nenhum registro encontrado para exportar.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_csv_rows(csv_path: str) -> list[dict]:
    path = Path(csv_path)

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_index(rows: list[dict]) -> dict[str, dict]:
    indexed = {}

    for row in rows:
        key = get_row_unique_key(row)
        if key:
            indexed[key] = row

    return indexed


def deduplicate_rows(rows: list[dict]) -> list[dict]:
    unique = []
    seen = set()

    for row in rows:
        key = get_row_unique_key(row)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        unique.append(row)

    return unique


def prepare_historical_row(row: dict, data_execucao: str) -> dict:
    historical_row = {field: row.get(field) for field in FIELDS}
    historical_row["ativo"] = True
    historical_row["data_primeira_captura"] = row.get("data_coleta")
    historical_row["data_ultima_captura"] = row.get("data_coleta")
    historical_row["data_ultima_execucao"] = data_execucao
    return historical_row


def merge_historical_data(
    previous_rows: list[dict],
    current_rows: list[dict],
    removed_keys: set[str],
    data_execucao: str,
) -> list[dict]:
    previous_index = build_index(previous_rows)
    current_index = build_index(current_rows)

    merged = []
    all_keys = set(previous_index.keys()) | set(current_index.keys())

    for key in all_keys:
        prev_row = previous_index.get(key)
        curr_row = current_index.get(key)

        if curr_row:
            if prev_row:
                merged_row = {field: curr_row.get(field) for field in FIELDS}
                merged_row["ativo"] = True
                merged_row["data_primeira_captura"] = (
                    prev_row.get("data_primeira_captura")
                    or prev_row.get("data_coleta")
                    or curr_row.get("data_coleta")
                )
                merged_row["data_ultima_captura"] = curr_row.get("data_coleta")
                merged_row["data_ultima_execucao"] = data_execucao
            else:
                merged_row = prepare_historical_row(curr_row, data_execucao)

            merged.append(merged_row)

        elif prev_row and key in removed_keys:
            merged_row = dict(prev_row)
            merged_row["ativo"] = False
            merged_row["data_ultima_execucao"] = data_execucao
            merged.append(merged_row)

    return deduplicate_rows(merged)


def compare_snapshots(previous_rows: list[dict], current_rows: list[dict], data_execucao: str):
    previous_index = build_index(previous_rows)
    current_index = build_index(current_rows)

    previous_keys = set(previous_index.keys())
    current_keys = set(current_index.keys())

    new_keys = current_keys - previous_keys
    removed_keys = previous_keys - current_keys
    common_keys = current_keys & previous_keys

    new_rows = []
    updated_rows = []
    removed_rows = []

    for key in new_keys:
        row = dict(current_index[key])
        row["tipo_evento"] = "novo"
        row["data_execucao"] = data_execucao
        new_rows.append(row)

    for key in common_keys:
        old_row = previous_index[key]
        new_row = current_index[key]

        if build_comparison_signature(old_row) != build_comparison_signature(new_row):
            row = dict(new_row)
            row["tipo_evento"] = "atualizado"
            row["data_execucao"] = data_execucao
            row["campos_alterados"] = get_changed_fields(old_row, new_row)
            updated_rows.append(row)

    for key in removed_keys:
        row = dict(previous_index[key])
        row["tipo_evento"] = "removido"
        row["data_execucao"] = data_execucao
        row["ativo"] = False
        removed_rows.append(row)

    consolidated_history = merge_historical_data(
        previous_rows=previous_rows,
        current_rows=current_rows,
        removed_keys=removed_keys,
        data_execucao=data_execucao,
    )

    return new_rows, updated_rows, removed_rows, consolidated_history


def save_debug_files(page, prefix: str = "debug_olx") -> None:
    Path("debug").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    html_path = Path("debug") / f"{prefix}_{timestamp}.html"
    png_path = Path("debug") / f"{prefix}_{timestamp}.png"

    try:
        html_path.write_text(page.content(), encoding="utf-8")
        print(f"HTML salvo em: {html_path}")
    except Exception as e:
        print(f"Falha ao salvar HTML: {e}")

    try:
        page.screenshot(path=str(png_path), full_page=True)
        print(f"Screenshot salva em: {png_path}")
    except Exception as e:
        print(f"Falha ao salvar screenshot: {e}")


def accept_cookies_if_visible(page) -> None:
    possible_buttons = [
        "button:has-text('Aceitar')",
        "button:has-text('Aceito')",
        "button:has-text('Continuar')",
        "button:has-text('Ok')",
        "button:has-text('OK')",
        "button:has-text('Entendi')",
        "button:has-text('Fechar')",
        "button:has-text('Concordo')",
    ]

    for selector in possible_buttons:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1500):
                locator.click(timeout=2500)
                page.wait_for_timeout(1500)
                print(f"Botão clicado: {selector}")
                return
        except Exception:
            continue


def try_get_text(page, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                text = locator.inner_text(timeout=3000).strip()
                if text:
                    return text
        except Exception:
            continue
    return ""


def extract_location_from_text(text: str) -> tuple[str, str, str]:
    """
    Extrai bairro/cidade/estado a partir do texto do detalhe.
    Importante: não assume Lagarto como cidade quando o anúncio é de outra cidade.
    Isso evita gravar anúncio de Barra dos Coqueiros, Aracaju etc. como se fosse Lagarto.
    """
    bairro = ""
    cidade = ""
    estado = ""

    if not text:
        return bairro, cidade, estado

    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]

    # Padrões mais comuns na OLX:
    # "Centro, Lagarto - SE"
    # "Lagarto - SE"
    # "Barra dos Coqueiros - SE"
    # "Sergipe, Lagarto" / "Lagarto, Centro"
    for line in lines:
        match = re.search(r"^(.+?),\s*([^,\-]+?)\s*-\s*([A-Z]{2})$", line, flags=re.IGNORECASE)
        if match:
            parte1 = match.group(1).strip()
            parte2 = match.group(2).strip()
            uf = match.group(3).upper().strip()

            estado = uf
            cidade = parte2
            bairro = parte1 if parte1.lower() != parte2.lower() else ""
            return bairro, cidade, estado

        match = re.search(r"^([^,\-]+?)\s*-\s*([A-Z]{2})$", line, flags=re.IGNORECASE)
        if match:
            cidade = match.group(1).strip()
            estado = match.group(2).upper().strip()
            return bairro, cidade, estado

        match = re.search(rf"^{re.escape(CIDADE_ALVO)}\s*,\s*(.*?)$", line, flags=re.IGNORECASE)
        if match:
            cidade = CIDADE_ALVO
            estado = ESTADO_ALVO
            bairro_extraido = match.group(1).strip()
            if bairro_extraido and bairro_extraido.upper() != ESTADO_ALVO:
                bairro = bairro_extraido
            return bairro, cidade, estado

    # Fallback conservador: só assume Lagarto se o texto tiver menção explícita.
    texto_lower = text.lower()
    if CIDADE_ALVO.lower() in texto_lower and ESTADO_ALVO.lower() in texto_lower:
        return bairro, CIDADE_ALVO, ESTADO_ALVO

    return bairro, cidade, estado


def is_target_city(title: str, description: str, full_text: str, url: str, bairro: str = "", cidade: str = "", estado: str = "") -> bool:
    """
    Confirma se o anúncio pertence à cidade alvo.
    Usa primeiro cidade/UF extraídas da localização do anúncio. Só usa título/descrição como fallback.
    """
    cidade_norm = clean_text(cidade).lower()
    estado_norm = clean_text(estado).upper()

    if cidade_norm:
        return cidade_norm == CIDADE_ALVO.lower() and (not estado_norm or estado_norm == ESTADO_ALVO)

    texto_curto = " ".join([str(title or ""), str(description or ""), str(url or ""), str(bairro or "")]).lower()
    return CIDADE_ALVO.lower() in texto_curto


def texto_contexto_indica_cidade_alvo(texto: str) -> bool:
    """Valida se o texto visível do card/link indica Lagarto/SE."""
    if not texto:
        return False

    t = clean_text(texto).lower()
    return (
        CIDADE_ALVO.lower() in t
        or f"{CIDADE_ALVO.lower()} - {ESTADO_ALVO.lower()}" in t
        or f"{CIDADE_ALVO.lower()}/{ESTADO_ALVO.lower()}" in t
    )


def is_rental_or_invalid_sale(title: str, description: str, url: str, price: Optional[float]) -> bool:
    """
    Evita aluguel/locação sem usar o body completo da OLX.
    O body completo costuma trazer links/menu com termos como aluguel, o que fazia todos os anúncios serem ignorados.
    """
    texto_busca = " ".join(
        [
            str(title or ""),
            str(description or ""),
            str(url or ""),
        ]
    ).lower()

    if TERMOS_ALUGUEL.search(texto_busca):
        return True

    if price is None:
        return True

    try:
        if float(price) < MIN_PRECO_VENDA:
            return True
    except Exception:
        return True

    return False


def extract_json_ld_data(page) -> dict:
    data = {}

    try:
        scripts = page.locator("script[type='application/ld+json']").all()

        for script in scripts:
            try:
                content = script.inner_text()
                parsed = json.loads(content)
                items = parsed if isinstance(parsed, list) else [parsed]

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    if item.get("name"):
                        data["titulo_json"] = item.get("name")

                    if item.get("description"):
                        data["descricao_json"] = item.get("description")

                    if item.get("image"):
                        image = item.get("image")

                        if isinstance(image, list):
                            data["imagens_json"] = image
                        else:
                            data["imagens_json"] = [image]

                    offers = item.get("offers")
                    if isinstance(offers, dict) and offers.get("price"):
                        data["preco_json"] = offers.get("price")

                    geo = item.get("geo")
                    if isinstance(geo, dict):
                        data["latitude"] = geo.get("latitude")
                        data["longitude"] = geo.get("longitude")

            except Exception:
                continue

    except Exception:
        pass

    return data


def extract_images(page) -> list[str]:
    images = []

    try:
        raw_images = page.locator("img").evaluate_all(
            """imgs => imgs.map(img => ({
                src: img.src || '',
                currentSrc: img.currentSrc || '',
                dataSrc: img.getAttribute('data-src') || '',
                dataOriginal: img.getAttribute('data-original') || '',
                srcset: img.getAttribute('srcset') || '',
                alt: img.alt || ''
            }))"""
        )

        for img in raw_images:
            possible_sources = [
                img.get("src"),
                img.get("currentSrc"),
                img.get("dataSrc"),
                img.get("dataOriginal"),
            ]

            srcset = img.get("srcset") or ""
            if srcset:
                first_srcset = srcset.split(",")[0].strip().split(" ")[0]
                possible_sources.append(first_srcset)

            for src in possible_sources:
                if not isinstance(src, str):
                    continue

                src = src.strip()

                if not src:
                    continue

                src_lower = src.lower()

                valid_source = (
                    "olx" in src_lower
                    or "cloudfront" in src_lower
                    or "img.olx" in src_lower
                    or "apollo" in src_lower
                    or "akamai" in src_lower
                )

                if not valid_source:
                    continue

                blocked = ["logo", "icon", "avatar", "profile", "placeholder", "sprite"]

                if any(block in src_lower for block in blocked):
                    continue

                if src not in images:
                    images.append(src)

    except Exception:
        pass

    return images


def extract_description(page, full_text: str, json_data: dict) -> str:
    selectors = [
        "[data-testid='ad-description']",
        "section:has-text('Descrição')",
        "div:has-text('Descrição')",
    ]

    text = try_get_text(page, selectors)

    if text:
        return clean_text(text)

    if json_data.get("descricao_json"):
        return clean_text(json_data.get("descricao_json"))

    match = re.search(
        r"Descrição\s*(.*?)(?:Detalhes|Localização|Publicado|Denunciar|R\$)",
        full_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return clean_text(match.group(1))

    return ""


def extract_seller_name(full_text: str) -> str:
    patterns = [
        r"Anunciante\s*(.*?)\s*(?:No OLX|Publicado|Ver telefone)",
        r"Publicado por\s*(.*?)\s*(?:No OLX|Publicado|Ver telefone)",
        r"Vendedor\s*(.*?)\s*(?:No OLX|Publicado|Ver telefone)",
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(1))[:120]

    return ""


def print_page_debug(page) -> None:
    try:
        print("URL atual:", page.url)
    except Exception:
        print("Não foi possível ler a URL atual.")

    try:
        print("Título da página:", page.title())
    except Exception:
        print("Não foi possível ler o título da página.")

    try:
        body_text = page.locator("body").inner_text()
        print("\nTrecho do body:")
        print(body_text[:2000])
    except Exception as e:
        print(f"Não foi possível ler o body da página: {e}")


def build_page_url(page_num: int) -> str:
    """
    Monta a URL paginada da OLX.
    Para a URL canônica sem query string, a paginação usa ?o=2, ?o=3...
    Se futuramente BASE_URL tiver query string, usa &o=2 automaticamente.
    """
    if page_num <= 1:
        return BASE_URL

    separador = "&" if "?" in BASE_URL else "?"
    return f"{BASE_URL}{separador}o={page_num}"


def is_probable_listing_url(link: str) -> bool:
    if not link:
        return False

    link_lower = link.lower()

    if "olx.com.br" not in link_lower:
        return False

    blocked_patterns = [
        "/account",
        "/chat",
        "/favoritos",
        "/ajuda",
        "/anunciar",
        "/autos-e-pecas",
        "/eletronicos-e-celulares",
        "/servicos",
        "/moda-e-beleza",
        "/para-a-sua-casa",
        "/moveis",
    ]

    for pattern in blocked_patterns:
        if pattern in link_lower:
            return False

    if link_lower.rstrip("/") == BASE_URL.lower().rstrip("/"):
        return False

    if re.search(r"[?&]o=\d+", link_lower):
        return False

    if re.search(r"-\d{6,}", link_lower):
        return True

    if ("/terrenos" in link_lower or "/lotes" in link_lower) and re.search(r"\d{6,}", link_lower):
        return True

    return False


def normalize_listing_url(link: str) -> str:
    link = link.strip()

    if "#" in link:
        link = link.split("#")[0]

    if "?" in link:
        link = link.split("?")[0]

    return link.rstrip("/")


def collect_listing_links(page) -> list[str]:
    print("Aguardando carregamento dos anúncios...")

    try:
        page.wait_for_timeout(8000)
        page.wait_for_selector("a", timeout=20000)
    except PlaywrightTimeoutError:
        print("A página carregou, mas não foi possível localizar links. Salvando debug.")
        save_debug_files(page, prefix="debug_olx_sem_links")
        return []

    for i in range(12):
        print(f"Scroll {i + 1}/12")
        page.mouse.wheel(0, 4500)
        page.wait_for_timeout(1800)

    try:
        all_links = page.locator("a").evaluate_all(
            """els => els.map(el => {
                const card = el.closest('li, article, section, div[data-testid], div');
                return {
                    href: el.href || '',
                    text: (el.innerText || '').trim(),
                    cardText: card ? (card.innerText || '').trim() : ''
                };
            })"""
        )
    except Exception as e:
        print(f"Erro ao extrair anchors da página: {e}")
        save_debug_files(page, prefix="debug_olx_anchor_error")
        return []

    print(f"Total bruto de anchors encontrados: {len(all_links)}")

    cleaned_links = []
    seen = set()
    candidatos_fora_contexto = 0

    for item in all_links:
        raw_link = (item.get("href") or "").strip()

        if not raw_link:
            continue

        if not is_probable_listing_url(raw_link):
            continue

        texto_card = " ".join([
            str(item.get("text") or ""),
            str(item.get("cardText") or ""),
        ])

        # A OLX costuma misturar patrocinados/recomendados de outras cidades na página.
        # Aqui a gente mantém somente links cujo card/texto visível indica Lagarto.
        if not texto_contexto_indica_cidade_alvo(texto_card):
            candidatos_fora_contexto += 1
            continue

        link = normalize_listing_url(raw_link)

        if link not in seen:
            seen.add(link)
            cleaned_links.append(link)

    print(f"Quantidade de links de anúncio encontrados para {CIDADE_ALVO}/{ESTADO_ALVO}: {len(cleaned_links)}")
    print(f"Links ignorados por não indicarem {CIDADE_ALVO}/{ESTADO_ALVO} no card: {candidatos_fora_contexto}")
    return cleaned_links


def extract_detail(page, url: str) -> Optional[dict]:
    print(f"Abrindo detalhe: {url}")

    try:
        page.goto(url, wait_until="commit", timeout=90000)
    except PlaywrightTimeoutError:
        print("Timeout no detalhe do anúncio. Salvando debug.")
        save_debug_files(page, prefix="debug_olx_detalhe_timeout")
        return None

    page.wait_for_timeout(6000)
    accept_cookies_if_visible(page)

    try:
        full_text = page.locator("body").inner_text()
    except Exception:
        return None

    lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    if not lines:
        return None

    json_data = extract_json_ld_data(page)
    imagens = extract_images(page)

    if json_data.get("imagens_json"):
        for img in json_data["imagens_json"]:
            url_imagem = safe_image_url(img)

            if url_imagem and url_imagem not in imagens:
                imagens.insert(0, url_imagem)

    imagens = [safe_image_url(img) for img in imagens]
    imagens = [img for img in imagens if img]

    title = try_get_text(
        page,
        [
            "h1",
            "[data-testid='ad-title']",
            "title",
        ],
    )

    if not title:
        title = json_data.get("titulo_json") or ""

    if not title:
        for line in lines[:30]:
            lower = line.lower()
            if len(line) > 10 and "olx" not in lower and "publicado em" not in lower:
                title = line[:250]
                break

    if not title:
        title = lines[0][:250]

    price_text = try_get_text(
        page,
        [
            "[data-testid='ad-price']",
            "h2",
            "span:has-text('R$')",
            "div:has-text('R$')",
        ],
    )

    preco = escolher_preco_venda(
        price_text=price_text,
        full_text=full_text,
        json_price=json_data.get("preco_json"),
    )

    descricao = extract_description(page, full_text, json_data)

    area_total, area_construida = extract_house_areas(full_text)

    quartos = parse_int_feature(r"(\d+)\s+quarto", full_text)
    banheiros = parse_int_feature(r"(\d+)\s+banheiro", full_text)
    vagas = parse_int_feature(r"(\d+)\s+vaga", full_text)

    condominio = parse_money_by_label("condom[ií]nio", full_text)
    iptu = parse_money_by_label("iptu", full_text)

    bairro, cidade, estado = extract_location_from_text(full_text)

    endereco_texto = ""
    for line in lines:
        line_lower = line.lower()
        if CIDADE_ALVO.lower() in line_lower and ESTADO_ALVO.lower() in line_lower:
            endereco_texto = line
            break

    latitude = json_data.get("latitude")
    longitude = json_data.get("longitude")

    anunciante = extract_seller_name(full_text)

    if not is_target_city(title, descricao, full_text, url, bairro, cidade, estado):
        print(f"Anúncio ignorado por estar fora de {CIDADE_ALVO}/{ESTADO_ALVO}: {url}")
        return None

    if is_rental_or_invalid_sale(title, descricao, url, preco):
        print(f"Anúncio ignorado por parecer aluguel ou venda inválida: {url} | preço extraído: {preco}")
        return None

    return {
        "id_imovel": extract_id_from_url(url),
        "titulo": clean_text(title)[:250],
        "descricao": descricao[:4000],
        "tipo_imovel": normalize_tipo_imovel(title),
        "finalidade": "venda",
        "preco_anunciado": preco,
        "condominio": condominio,
        "iptu": iptu,
        "area_total_m2": area_total,
        "area_construida_m2": area_construida,
        "quartos": quartos,
        "banheiros": banheiros,
        "vagas_garagem": vagas,
        "bairro": bairro,
        "cidade": cidade,
        "estado": estado,
        "endereco_texto": endereco_texto,
        "latitude": latitude,
        "longitude": longitude,
        "anunciante": anunciante,
        "fonte": "olx_playwright",
        "url_anuncio": url,
        "imagem_principal_url": imagens[0] if imagens else "",
        "imagens_urls": "|".join(imagens),
        "qtd_imagens": len(imagens),
        "data_coleta": datetime.now().date().isoformat(),
        "ativo": True,
    }


def collect_links_from_all_pages(page, max_pages: int) -> list[str]:
    all_links = []
    seen = set()
    empty_pages_in_sequence = 0

    for page_num in range(1, max_pages + 1):
        url = build_page_url(page_num)

        print("\n" + "=" * 70)
        print(f"Coletando página {page_num} de {max_pages}")
        print(f"URL: {url}")

        try:
            page.goto(url, wait_until="commit", timeout=90000)
            page.wait_for_timeout(5000)
            accept_cookies_if_visible(page)
        except PlaywrightTimeoutError:
            print(f"Timeout ao abrir a página {page_num}. Pulando.")
            continue

        if page_num == 1:
            print_page_debug(page)

        page_links = collect_listing_links(page)

        if not page_links:
            empty_pages_in_sequence += 1
            print(f"Nenhum link encontrado na página {page_num}.")

            if empty_pages_in_sequence >= 2:
                print("Duas páginas seguidas sem anúncios. Encerrando paginação.")
                break

            continue

        empty_pages_in_sequence = 0

        novos = 0

        for link in page_links:
            if link not in seen:
                seen.add(link)
                all_links.append(link)
                novos += 1

        print(f"Links novos adicionados nesta página: {novos}")
        print(f"Total acumulado de links únicos: {len(all_links)}")

    return all_links


def main() -> None:
    timestamp_execucao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_arquivo = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    previous_rows = load_csv_rows(HISTORICAL_CSV)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            viewport={"width": 1440, "height": 900},
        )

        page = context.new_page()
        page.set_default_timeout(30000)

        max_pages = 10
        max_valid_items = 800

        links = collect_links_from_all_pages(page, max_pages=max_pages)

        if not links:
            print("Nenhum link de anúncio encontrado.")
            browser.close()
            return

        print(f"\nTOTAL FINAL de links únicos coletados: {len(links)}")

        current_rows = []

        total_links = len(links)
        for i, url in enumerate(links, start=1):
            if len(current_rows) >= max_valid_items:
                print(f"Meta de {max_valid_items} anúncios válidos atingida. Encerrando coleta.")
                break

            try:
                print(f"[{i}/{total_links}] Coletando anúncio: {url} | válidos até agora: {len(current_rows)}")
                detail = extract_detail(page, url)

                if detail:
                    current_rows.append(detail)
                    print(f"Registro válido adicionado. Total válido: {len(current_rows)}")

                time.sleep(2)

            except Exception as e:
                print(f"Erro ao coletar {url}: {e}")

        browser.close()

    current_rows = deduplicate_rows(current_rows)

    if not current_rows:
        print("Nenhum registro final foi coletado.")
        return

    new_rows, updated_rows, removed_rows, consolidated_history = compare_snapshots(
        previous_rows=previous_rows,
        current_rows=current_rows,
        data_execucao=timestamp_execucao,
    )

    full_output_path = f"output/imoveis_olx_casas_lagarto_full_{timestamp_arquivo}.csv"
    new_output_path = f"output/imoveis_olx_casas_lagarto_novos_{timestamp_arquivo}.csv"
    updated_output_path = f"output/imoveis_olx_casas_lagarto_atualizados_{timestamp_arquivo}.csv"
    removed_output_path = f"output/imoveis_olx_casas_lagarto_removidos_{timestamp_arquivo}.csv"

    save_csv(current_rows, full_output_path)
    print(f"Arquivo completo gerado: {full_output_path}")
    print(f"Quantidade total coletada nesta execução: {len(current_rows)}")

    if new_rows:
        save_csv(new_rows, new_output_path)
        print(f"Arquivo de anúncios novos gerado: {new_output_path}")
        print(f"Quantidade de anúncios novos: {len(new_rows)}")
    else:
        print("Nenhum anúncio novo encontrado nesta execução.")

    if updated_rows:
        save_csv(updated_rows, updated_output_path)
        print(f"Arquivo de anúncios atualizados gerado: {updated_output_path}")
        print(f"Quantidade de anúncios atualizados: {len(updated_rows)}")
    else:
        print("Nenhum anúncio atualizado encontrado nesta execução.")

    if removed_rows:
        save_csv(removed_rows, removed_output_path)
        print(f"Arquivo de anúncios removidos gerado: {removed_output_path}")
        print(f"Quantidade de anúncios removidos: {len(removed_rows)}")
    else:
        print("Nenhum anúncio removido encontrado nesta execução.")

    if consolidated_history:
        save_csv(consolidated_history, HISTORICAL_CSV)
        print(f"Histórico consolidado atualizado em: {HISTORICAL_CSV}")
        print(f"Total de registros no histórico consolidado: {len(consolidated_history)}")
    else:
        print("Histórico consolidado ficou vazio, nada foi salvo.")


if __name__ == "__main__":
    main()