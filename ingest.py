#!/usr/bin/env python
"""Ingestion CLI: Load, chunk, embed, and index the synthetic dataset."""
import sys
import argparse
from app.ingestion.pipeline import run_ingestion_pipeline, print_summary
from app.retrieval.search import semantic_search


def main():
    parser = argparse.ArgumentParser(description="Manage document ingestion and search")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    ingest_parser = subparsers.add_parser("ingest", help="Build the index from scratch")
    ingest_parser.add_argument("--data-dir", default=".", help="Path to data directory")

    search_parser = subparsers.add_parser("search", help="Test semantic search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--source-type", help="Filter by source type")
    search_parser.add_argument("--n-results", type=int, default=5, help="Number of results")

    args = parser.parse_args()

    if args.command == "ingest" or not args.command:
        summary = run_ingestion_pipeline(data_dir=args.data_dir if args.command == "ingest" else ".")
        print_summary(summary)

    elif args.command == "search":
        where = None
        if args.source_type:
            where = {"source_type": args.source_type}

        print(f"\nSearching for: '{args.query}'")
        if where:
            print(f"Filter: {where}")
        print("-" * 60)

        results = semantic_search(query=args.query, n_results=args.n_results, where=where)

        if not results:
            print("No results found.")
        else:
            for i, result in enumerate(results, 1):
                print(f"\n[{i}] {result['id']} (distance: {result['distance']:.4f})")
                print(f"    Source: {result['metadata'].get('source_type', 'unknown')}")
                if result['metadata'].get('date'):
                    print(f"    Date: {result['metadata']['date']}")
                print(f"    Text: {result['document'][:200]}...")
                print()


if __name__ == "__main__":
    main()
