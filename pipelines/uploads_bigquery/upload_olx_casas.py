from pathlib import Path
from typing import List, Optional

from google.cloud import bigquery, storage

PROJECT_ID = "radar-imobiliario"
DATASET_ID = "real_estate"
BUCKET_NAME = "real-estate-raw-dev"

LOCAL_OUTPUT_DIR = "/home/gui_adm/radar-imobiliario-app/pipelines/coletores/output"
GCS_PREFIX = "olx/casas"

STAGE_TABLE = "raw_olx_stage"
HISTORICO_TABLE = "raw_olx_historico"

CASAS_STAGE_TABLE = "raw_olx_casas_stage"
CASAS_HISTORICO_TABLE = "raw_olx_casas_historico"

NOVOS_TABLE = "raw_olx_novos"
ATUALIZADOS_TABLE = "raw_olx_atualizados"
REMOVIDOS_TABLE = "raw_olx_removidos"

BASE_SCHEMA = [
    bigquery.SchemaField("id_imovel", "STRING"),
    bigquery.SchemaField("titulo", "STRING"),
    bigquery.SchemaField("descricao", "STRING"),
    bigquery.SchemaField("tipo_imovel", "STRING"),
    bigquery.SchemaField("finalidade", "STRING"),
    bigquery.SchemaField("preco_anunciado", "FLOAT"),
    bigquery.SchemaField("condominio", "FLOAT"),
    bigquery.SchemaField("iptu", "FLOAT"),
    bigquery.SchemaField("area_total_m2", "FLOAT"),
    bigquery.SchemaField("area_construida_m2", "FLOAT"),
    bigquery.SchemaField("quartos", "INT64"),
    bigquery.SchemaField("banheiros", "INT64"),
    bigquery.SchemaField("vagas_garagem", "INT64"),
    bigquery.SchemaField("bairro", "STRING"),
    bigquery.SchemaField("cidade", "STRING"),
    bigquery.SchemaField("estado", "STRING"),
    bigquery.SchemaField("endereco_texto", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT"),
    bigquery.SchemaField("longitude", "FLOAT"),
    bigquery.SchemaField("anunciante", "STRING"),
    bigquery.SchemaField("fonte", "STRING"),
    bigquery.SchemaField("url_anuncio", "STRING"),
    bigquery.SchemaField("imagem_principal_url", "STRING"),
    bigquery.SchemaField("imagens_urls", "STRING"),
    bigquery.SchemaField("qtd_imagens", "INT64"),
    bigquery.SchemaField("data_coleta", "DATE"),
    bigquery.SchemaField("ativo", "BOOL"),
]

HISTORICO_SCHEMA = BASE_SCHEMA + [
    bigquery.SchemaField("data_primeira_captura", "DATE"),
    bigquery.SchemaField("data_ultima_captura", "DATE"),
    bigquery.SchemaField("data_ultima_execucao", "DATETIME"),
]

EVENT_SCHEMA = BASE_SCHEMA + [
    bigquery.SchemaField("tipo_evento", "STRING"),
    bigquery.SchemaField("data_execucao", "DATETIME"),
]

UPDATED_EVENT_SCHEMA = EVENT_SCHEMA + [
    bigquery.SchemaField("campos_alterados", "STRING"),
]


def ensure_dataset(bq_client: bigquery.Client) -> None:
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    bq_client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset garantido: {dataset_ref}")


def ensure_table(bq_client: bigquery.Client, table_name: str, schema: list[bigquery.SchemaField]) -> None:
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    try:
        table = bq_client.get_table(table_ref)
        existing = {field.name for field in table.schema}
        missing = [field for field in schema if field.name not in existing]

        if missing:
            table.schema = list(table.schema) + missing
            bq_client.update_table(table, ["schema"])
            print(f"Schema atualizado: {table_ref}")
        else:
            print(f"Tabela OK: {table_ref}")

    except Exception:
        table = bigquery.Table(table_ref, schema=schema)
        bq_client.create_table(table)
        print(f"Tabela criada: {table_ref}")


def list_files(pattern: str) -> List[Path]:
    path = Path(LOCAL_OUTPUT_DIR)

    if not path.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {LOCAL_OUTPUT_DIR}")

    return sorted(path.glob(pattern))


def latest_file(pattern: str) -> Optional[Path]:
    files = list_files(pattern)
    return files[-1] if files else None


def upload_to_gcs(storage_client: storage.Client, local_file: Path, folder: str) -> str:
    bucket = storage_client.bucket(BUCKET_NAME)
    object_name = f"{GCS_PREFIX}/{folder}/{local_file.name}"

    blob = bucket.blob(object_name)
    blob.upload_from_filename(str(local_file))

    uri = f"gs://{BUCKET_NAME}/{object_name}"
    print(f"Upload GCS: {uri}")
    return uri


def load_csv_to_bq(
    bq_client: bigquery.Client,
    gcs_uri: str,
    table_name: str,
    schema: list[bigquery.SchemaField],
    write_disposition: str = bigquery.WriteDisposition.WRITE_APPEND,
) -> None:
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=False,
        schema=schema,
        write_disposition=write_disposition,
        field_delimiter=",",
        encoding="UTF-8",
        allow_quoted_newlines=True,
        quote_character='"',
        max_bad_records=0,
    )

    job = bq_client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result()
    print(f"Carga concluída: {table_ref}")


def run_merge_geral(bq_client: bigquery.Client) -> None:
    query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{HISTORICO_TABLE}` T
    USING (
      SELECT * EXCEPT(rn)
      FROM (
        SELECT
          *,
          ROW_NUMBER() OVER (
            PARTITION BY id_imovel
            ORDER BY data_coleta DESC
          ) AS rn
        FROM `{PROJECT_ID}.{DATASET_ID}.{CASAS_STAGE_TABLE}`
        WHERE id_imovel IS NOT NULL
      )
      WHERE rn = 1
    ) S
    ON T.id_imovel = S.id_imovel

    WHEN MATCHED THEN
      UPDATE SET
        T.titulo = S.titulo,
        T.descricao = S.descricao,
        T.tipo_imovel = S.tipo_imovel,
        T.finalidade = S.finalidade,
        T.preco_anunciado = S.preco_anunciado,
        T.condominio = S.condominio,
        T.iptu = S.iptu,
        T.area_total_m2 = S.area_total_m2,
        T.area_construida_m2 = S.area_construida_m2,
        T.quartos = S.quartos,
        T.banheiros = S.banheiros,
        T.vagas_garagem = S.vagas_garagem,
        T.bairro = S.bairro,
        T.cidade = S.cidade,
        T.estado = S.estado,
        T.endereco_texto = S.endereco_texto,
        T.latitude = S.latitude,
        T.longitude = S.longitude,
        T.anunciante = S.anunciante,
        T.fonte = S.fonte,
        T.url_anuncio = S.url_anuncio,
        T.imagem_principal_url = S.imagem_principal_url,
        T.imagens_urls = S.imagens_urls,
        T.qtd_imagens = S.qtd_imagens,
        T.data_coleta = S.data_coleta,
        T.ativo = TRUE,
        T.data_ultima_captura = S.data_coleta,
        T.data_ultima_execucao = CURRENT_DATETIME()

    WHEN NOT MATCHED THEN
      INSERT (
        id_imovel,
        titulo,
        descricao,
        tipo_imovel,
        finalidade,
        preco_anunciado,
        condominio,
        iptu,
        area_total_m2,
        area_construida_m2,
        quartos,
        banheiros,
        vagas_garagem,
        bairro,
        cidade,
        estado,
        endereco_texto,
        latitude,
        longitude,
        anunciante,
        fonte,
        url_anuncio,
        imagem_principal_url,
        imagens_urls,
        qtd_imagens,
        data_coleta,
        ativo,
        data_primeira_captura,
        data_ultima_captura,
        data_ultima_execucao
      )
      VALUES (
        S.id_imovel,
        S.titulo,
        S.descricao,
        S.tipo_imovel,
        S.finalidade,
        S.preco_anunciado,
        S.condominio,
        S.iptu,
        S.area_total_m2,
        S.area_construida_m2,
        S.quartos,
        S.banheiros,
        S.vagas_garagem,
        S.bairro,
        S.cidade,
        S.estado,
        S.endereco_texto,
        S.latitude,
        S.longitude,
        S.anunciante,
        S.fonte,
        S.url_anuncio,
        S.imagem_principal_url,
        S.imagens_urls,
        S.qtd_imagens,
        S.data_coleta,
        TRUE,
        S.data_coleta,
        S.data_coleta,
        CURRENT_DATETIME()
      )
    """

    job = bq_client.query(query)
    job.result()
    print("MERGE concluído em raw_olx_historico.")


def main() -> None:
    storage_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)

    ensure_dataset(bq_client)

    ensure_table(bq_client, STAGE_TABLE, BASE_SCHEMA)
    ensure_table(bq_client, CASAS_STAGE_TABLE, BASE_SCHEMA)
    ensure_table(bq_client, HISTORICO_TABLE, HISTORICO_SCHEMA)
    ensure_table(bq_client, CASAS_HISTORICO_TABLE, HISTORICO_SCHEMA)
    ensure_table(bq_client, NOVOS_TABLE, EVENT_SCHEMA)
    ensure_table(bq_client, ATUALIZADOS_TABLE, UPDATED_EVENT_SCHEMA)
    ensure_table(bq_client, REMOVIDOS_TABLE, EVENT_SCHEMA)

    full_file = latest_file("imoveis_olx_casas_full_*.csv")
    historico_file = Path(LOCAL_OUTPUT_DIR) / "imoveis_olx_casas_historico.csv"
    novos_file = latest_file("imoveis_olx_casas_novos_*.csv")
    atualizados_file = latest_file("imoveis_olx_casas_atualizados_*.csv")
    removidos_file = latest_file("imoveis_olx_casas_removidos_*.csv")

    if not full_file:
        print("Nenhum arquivo imoveis_olx_casas_full_*.csv encontrado.")
        return

    print(f"Arquivo full selecionado: {full_file}")
    full_uri = upload_to_gcs(storage_client, full_file, "full")

    load_csv_to_bq(bq_client, full_uri, STAGE_TABLE, BASE_SCHEMA, bigquery.WriteDisposition.WRITE_APPEND)
    load_csv_to_bq(bq_client, full_uri, CASAS_STAGE_TABLE, BASE_SCHEMA, bigquery.WriteDisposition.WRITE_APPEND)

    run_merge_geral(bq_client)

    if historico_file.exists():
        historico_uri = upload_to_gcs(storage_client, historico_file, "historico")
        load_csv_to_bq(
            bq_client,
            historico_uri,
            CASAS_HISTORICO_TABLE,
            HISTORICO_SCHEMA,
            bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
    else:
        print(f"Histórico de casas não encontrado: {historico_file}")

    if novos_file:
        novos_uri = upload_to_gcs(storage_client, novos_file, "eventos/novos")
        load_csv_to_bq(bq_client, novos_uri, NOVOS_TABLE, EVENT_SCHEMA, bigquery.WriteDisposition.WRITE_APPEND)
    else:
        print("Nenhum arquivo de casas novas encontrado.")

    if atualizados_file:
        atualizados_uri = upload_to_gcs(storage_client, atualizados_file, "eventos/atualizados")
        load_csv_to_bq(bq_client, atualizados_uri, ATUALIZADOS_TABLE, UPDATED_EVENT_SCHEMA, bigquery.WriteDisposition.WRITE_APPEND)
    else:
        print("Nenhum arquivo de casas atualizadas encontrado.")

    if removidos_file:
        removidos_uri = upload_to_gcs(storage_client, removidos_file, "eventos/removidos")
        load_csv_to_bq(bq_client, removidos_uri, REMOVIDOS_TABLE, EVENT_SCHEMA, bigquery.WriteDisposition.WRITE_APPEND)
    else:
        print("Nenhum arquivo de casas removidas encontrado.")

    print("Processo de carga das casas finalizado com sucesso.")


if __name__ == "__main__":
    main()
