from pathlib import Path
from typing import List

from google.cloud import bigquery, storage


PROJECT_ID = "radar-imobiliario"
DATASET_ID = "real_estate"
BUCKET_NAME = "real-estate-raw-dev"

LOCAL_OUTPUT_DIR = "/home/gui_adm/radar-imobiliario-app/pipelines/coletores/output"
GCS_PREFIX = "olx/stage"

STAGE_TABLE = "raw_olx_stage"
HISTORICO_TABLE = "raw_olx_historico"


SCHEMA = [
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

HISTORICO_SCHEMA = SCHEMA + [
    bigquery.SchemaField("data_primeira_captura", "DATE"),
    bigquery.SchemaField("data_ultima_captura", "DATE"),
    bigquery.SchemaField("data_ultima_execucao", "DATETIME"),
]


def ensure_dataset(bq_client):
    dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset.location = "US"
    bq_client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset garantido: {PROJECT_ID}.{DATASET_ID}")


def ensure_table(bq_client, table_name: str, schema):
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


def list_full_files() -> List[Path]:
    path = Path(LOCAL_OUTPUT_DIR)

    if not path.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {LOCAL_OUTPUT_DIR}")

    return sorted(path.glob("imoveis_olx_full_*.csv"))


def upload_to_gcs(storage_client, local_file: Path) -> str:
    bucket = storage_client.bucket(BUCKET_NAME)
    object_name = f"{GCS_PREFIX}/{local_file.name}"

    blob = bucket.blob(object_name)
    blob.upload_from_filename(str(local_file))

    uri = f"gs://{BUCKET_NAME}/{object_name}"
    print(f"Upload GCS: {uri}")

    return uri


def load_to_stage(bq_client, gcs_uri: str):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{STAGE_TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=False,
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        field_delimiter=",",
        encoding="UTF-8",
        allow_quoted_newlines=True,
        quote_character='"',
        max_bad_records=0,
    )

    job = bq_client.load_table_from_uri(
        gcs_uri,
        table_ref,
        job_config=job_config,
    )

    job.result()
    print(f"Carga concluída na stage: {table_ref}")


def run_merge(bq_client):
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
            FROM `{PROJECT_ID}.{DATASET_ID}.{STAGE_TABLE}`
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


def main():
    storage_client = storage.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)

    ensure_dataset(bq_client)

    ensure_table(bq_client, STAGE_TABLE, SCHEMA)
    ensure_table(bq_client, HISTORICO_TABLE, HISTORICO_SCHEMA)

    files = list_full_files()

    if not files:
        print("Nenhum arquivo imoveis_olx_full_*.csv encontrado.")
        return

    latest_file = files[-1]
    print(f"Arquivo selecionado para carga: {latest_file}")

    gcs_uri = upload_to_gcs(storage_client, latest_file)

    load_to_stage(bq_client, gcs_uri)

    run_merge(bq_client)

    print("Processo profissional finalizado com sucesso.")


if __name__ == "__main__":
    main()