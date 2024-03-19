# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gke_databases_postgres_pgvector_manifests_02_imports]
from pgvector.psycopg import register_vector
import psycopg
import os
import sys
import csv
from fastembed import TextEmbedding
from typing import List
import numpy as np
# [END gke_databases_postgres_pgvector_manifests_02_imports]

def main(query_string):
# [START gke_databases_postgres_pgvector_manifests_02_create_connection]
    conn = psycopg.connect(
        dbname="app",
        host="gke-pg-cluster-rw.pg-ns",
        user=os.environ.get("CLIENTUSERNAME"),
        password=os.environ.get("CLIENTPASSWORD"),
        autocommit=True)
# [END gke_databases_postgres_pgvector_manifests_02_create_connection]

# [START gke_databases_postgres_pgvector_manifests_02_create_table]
    register_vector(conn)
    conn.execute('DROP TABLE IF EXISTS documents;')
    conn.execute('CREATE TABLE documents (id bigserial PRIMARY KEY, author text, title text, description text, embedding vector(384));')
# [END gke_databases_postgres_pgvector_manifests_02_create_table]

# [START gke_databases_postgres_pgvector_manifests_02_create_collection]
    books = [*csv.DictReader(open('/usr/local/dataset/dataset.csv'))]
# [END gke_databases_postgres_pgvector_manifests_02_create_collection]

# [START gke_databases_postgres_pgvector_manifests_02_prepare_doc]
    descriptions = [doc["description"] for doc in books]
    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en")
    embeddings: List[np.ndarray] = list(embedding_model.embed(descriptions))
# [END gke_databases_postgres_pgvector_manifests_02_prepare_doc]
   
# [START gke_databases_postgres_pgvector_manifests_02_insert_into_table]
    for i, doc in enumerate(books):
        conn.execute('INSERT INTO documents (author, title, description, embedding) VALUES (%s, %s, %s, %s)', (doc["author"], doc["title"], doc["description"], embeddings[i]))
# [END gke_databases_postgres_pgvector_manifests_02_insert_into_table]
  
# [START gke_databases_postgres_pgvector_manifests_02_handle_query]
    query_vector = list(embedding_model.embed([query_string]))[0]
    response = conn.execute('SELECT title, author, description FROM documents ORDER BY embedding <-> %s LIMIT 2', (query_vector,)).fetchall()
    for hit in response:
        print("Title: {}, Author: {}".format(hit[0], hit[1]))
        print(hit[2])
        print("---------")
# [END gke_databases_postgres_pgvector_manifests_02_handle_query]   

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_string = " ".join(sys.argv[1:])
        print("Querying pgvector for: ", query_string)
        main(query_string)
    else:
        print("Please provide a query string as an argument.")

