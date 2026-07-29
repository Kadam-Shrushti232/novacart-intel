# NovaCart Intelligence Layer

A scoped AI/LLM prototype for semantic document retrieval and multi-hop reasoning over enterprise data (orders, refunds, support tickets, supplier reports, shipment logs).

## Quick Start

### Prerequisites
- Docker & Docker Compose
- API keys: OpenAI (for embeddings), Anthropic (for reasoning)

### Setup & Run

1. **Clone the repo**
   ```bash
   git clone https://github.com/Kadam-Shrushti232/novacart-intel.git
   cd novacart-intel
   ```

2. **Create `.env` from template**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

3. **Build and run**
   ```bash
   docker-compose up --build
   ```

The API will be available at `http://localhost:8000`.

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

## Architecture

- **Ingestion**: Load documents, chunk, embed, and index to Chroma (embedded)
- **Retrieval**: Semantic search + metadata filtering
- **Agent**: Tool-based reasoning with source citation
- **API**: FastAPI with API key auth

## Technology Stack

- Backend: Python, FastAPI
- Vector Store: Chroma (embedded)
- Embeddings: OpenAI text-embedding-3-small
- Reasoning: Anthropic Claude (tool use)
- Deployment: Docker + docker-compose
- Testing: pytest

## Project Structure

```
.
├── app/
│   ├── api/              # API endpoints
│   ├── ingestion/        # Document loading & chunking
│   ├── retrieval/        # Search & filtering
│   ├── agent/            # Tool-based reasoning
│   ├── core/             # Config, auth, models
│   └── main.py           # FastAPI app
├── data/synthetic/       # Synthetic dataset
├── tests/                # Unit & integration tests
├── docker/               # Docker utilities
├── docs/                 # Architecture & design docs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Development

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run tests
pytest tests/

# Run app locally (requires .env with API keys)
uvicorn app.main:app --reload
```

## Known Limitations

- Single API key (no user/role separation)
- Chroma persisted locally (not production-ready)
- Synthetic dataset only (15-20 documents for demo)
- No fine-tuning or model training

## Future Work

- Multi-user auth & session management
- Distributed vector store (e.g., Pinecone, Weaviate)
- Fine-tuned embeddings & reasoning models
- Web UI / chat interface
- Monitoring & observability
