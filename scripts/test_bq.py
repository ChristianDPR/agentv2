# test_bq.py
from google.cloud import bigquery

client = bigquery.Client()

q = "SELECT COUNT(*) AS total FROM rosy-sky-364021.dataset_sura_pe_sbx_dmc_ro.temp_fprod_trs"
rows = list(client.query(q).result())

print(rows[0]["total"])
