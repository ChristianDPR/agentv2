# test_bq.py
import os
from google.cloud import bigquery

project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEX_AI_PROJECT")
dataset = os.getenv("BIGQUERY_DEFAULT_DATASET", "rosy-sky-364021.dataset_sura_pe_sbx_dmc_ro")

client = bigquery.Client(project=project)

table = f"{dataset}.tmp_fprod_trs"
query = f"SELECT COUNT(*) AS total FROM `{table}`"
rows = list(client.query(query).result())

print(rows[0]["total"])
