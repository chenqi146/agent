import sys
import os
from elasticsearch import Elasticsearch
import json

def debug_es():
    # Configuration from application.yaml
    hosts = [{"host": "127.0.0.1", "port": 9200, "scheme": "http"}]
    auth = ("elastic", "123123")
    index_name = "pg-agent-memory"

    print(f"Connecting to Elasticsearch at {hosts}...")
    try:
        es = Elasticsearch(hosts=hosts, basic_auth=auth)
        if not es.ping():
            print("Error: Could not ping Elasticsearch.")
            return

        print("Connected to Elasticsearch.")
        
        # 1. List indices
        indices = es.cat.indices(format="json")
        print("\n=== Indices ===")
        found_index = False
        for idx in indices:
            print(f"Name: {idx['index']}, Docs: {idx['docs.count']}")
            if idx['index'] == index_name:
                found_index = True
        
        if not found_index:
            print(f"\nWARNING: Index '{index_name}' NOT FOUND!")
            return

        # 2. Count documents
        count = es.count(index=index_name)
        print(f"\n=== Document Count in '{index_name}' ===")
        print(f"Count: {count['count']}")

        # 3. Search last 10 documents
        print(f"\n=== Last 10 Documents in '{index_name}' ===")
        resp = es.search(index=index_name, body={
            "query": {"match_all": {}},
            "sort": [{"created_at": {"order": "desc"}}],
            "size": 10
        })
        
        hits = resp['hits']['hits']
        if not hits:
            print("No documents found.")
        else:
            for hit in hits:
                source = hit['_source']
                print(f"ID: {hit['_id']}")
                print(f"Time: {source.get('time', 'N/A')}")
                print(f"Fact: {source.get('fact', 'N/A')}")
                print(f"Detail: {source.get('detail', 'N/A')[:50]}...") # Truncate detail
                print("-" * 20)

        # 4. Search for "摄像头"
        print(f"\n=== Search for '摄像头' in '{index_name}' ===")
        search_body = {
            "query": {
                "multi_match": {
                    "query": "摄像头",
                    "fields": ["fact", "detail"]
                }
            }
        }
        resp = es.search(index=index_name, body=search_body)
        hits = resp['hits']['hits']
        if not hits:
            print("No matches for '摄像头'.")
        else:
            print(f"Found {len(hits)} matches:")
            for hit in hits:
                source = hit['_source']
                print(f"ID: {hit['_id']}")
                print(f"Fact: {source.get('fact', 'N/A')}")
                print("-" * 20)

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_es()
