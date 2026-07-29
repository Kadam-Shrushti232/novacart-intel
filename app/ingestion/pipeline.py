from collections import defaultdict
from app.ingestion.loader import load_records
from app.ingestion.chunker import chunk_record
from app.ingestion.embedding import embed_text
from app.ingestion.index import clear_index, index_chunks
from app.core.models import Chunk


def run_ingestion_pipeline(data_dir: str = ".", clear_existing: bool = True) -> dict:
    """Run the full ingestion pipeline: load → chunk → embed → index."""
    if clear_existing:
        clear_index()

    chunks = []
    source_counts = defaultdict(int)

    print("Loading records...")
    for record in load_records(data_dir):
        source_counts[record.source_type] += 1
        chunk = chunk_record(record)

        print(f"Embedding {chunk.record_id}...", end=" ", flush=True)
        try:
            embedding = embed_text(chunk.text)
            chunk.metadata["_embedding"] = embedding
            chunks.append(chunk)
            print("✓")
        except Exception as e:
            print(f"✗ (error: {str(e)})")
            raise

    print(f"\nChunked {len(chunks)} records total")

    print("Indexing into Chroma...")
    indexed_count = index_chunks(chunks)
    print(f"Indexed {indexed_count} chunks")

    chunk_counts_by_type = defaultdict(int)
    for chunk in chunks:
        chunk_counts_by_type[chunk.source_type] += 1

    summary = {
        "total_chunks": len(chunks),
        "chunks_by_source_type": dict(chunk_counts_by_type),
    }

    return summary


def print_summary(summary: dict) -> None:
    """Pretty-print the ingestion summary."""
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total chunks indexed: {summary['total_chunks']}")
    print("\nChunks by source type:")
    for source_type, count in sorted(summary["chunks_by_source_type"].items()):
        print(f"  {source_type:20} {count:3} chunks")
    print("=" * 60)
