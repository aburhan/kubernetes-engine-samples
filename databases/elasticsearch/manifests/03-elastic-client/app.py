@@ -1,3 +1,5 @@
#!/usr/bin/env python

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
@@ -12,20 +14,25 @@
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gke_databases_elasticsearch_manifests_03_imports]
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import os
import csv
from fastembed import TextEmbedding
from typing import List
import numpy as np
# [END gke_databases_elasticsearch_manifests_03_imports]

def main(query_string):

# [START gke_databases_elasticsearch_manifests_03_create_client]
    client = Elasticsearch(['https://elasticsearch-ha-es-http:9200'], verify_certs=True, 
    ca_certs='/usr/local/cert/ca.crt',
    basic_auth=("elastic",
    os.getenv("PW"))
    )
# [END gke_databases_elasticsearch_manifests_03_create_client]

    # Create a collection
# [START gke_databases_elasticsearch_manifests_03_create_collection]
    books = [*csv.DictReader(open('/usr/local/dataset/dataset.csv'))]
    descriptions = [doc["description"] for doc in books]
    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en")
    embeddings: List[np.ndarray] = list(embedding_model.embed(descriptions))
# [END gke_databases_elasticsearch_manifests_03_create_collection]

# [START gke_databases_elasticsearch_manifests_03_create_schema]
    index_scheme = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1
    },
    "mappings": {
        "dynamic": "true",
        "_source": {
        "enabled": "true"
        },
        "properties": {
        "title": {
            "type": "text"
        },
        "author": {
            "type": "text"
        },
        "publishDate": {
            "type": "text"
        },
        "description": {
            "type": "text"
        },
        "description_vector": {
            "type": "dense_vector",
            "dims": 384
        }
        }
    }
    }
    client.indices.create(index="books", body=index_scheme)
# [END gke_databases_elasticsearch_manifests_03_create_schema]

# [START gke_databases_elasticsearch_manifests_03_prepare_doc]
    documents: list[dict[str, any]] = []

    for i, doc in enumerate(books):
        book = doc
        book["_op_type"] = "index"
        book["_index"] = "books"
        book["description_vector"] = embeddings[i]
        documents.append(book)
# [END gke_databases_elasticsearch_manifests_03_prepare_doc]

# [START gke_databases_elasticsearch_manifests_03_add_to_collection]
    # Upload data 
    bulk(client, documents)
# [END gke_databases_elasticsearch_manifests_03_add_to_collection]

    # Query the collection
# [START gke_databases_elasticsearch_manifests_03_define_query_function]
    def handle_query(query, limit):
        query_vector = list(embedding_model.embed([query]))[0]
        script_query = {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'description_vector') + 1.0",
                    "params": {"query_vector": query_vector}
                }
            }
        }
        response = client.search(
            index="books",
            body={
                "size": limit,
                "query": script_query,
                "_source": {"includes": ["description", "title", "author", "body"]}
            }
        )   
        for hit in response["hits"]["hits"]:
            print("Title: {}, Author: {}, score: {}".format(hit["_source"]["title"], hit["_source"]["author"], hit["_score"]))
            print(hit["_source"]["description"])
            print("---------")
# [END gke_databases_elasticsearch_manifests_03_define_query_function]

# [START gke_databases_elasticsearch_manifests_03_query_collection]
    handle_query("anti-utopia and totalitarian society", 2)
# [END gke_databases_elasticsearch_manifests_03_query_collection]
if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_string = " ".join(sys.argv[1:])