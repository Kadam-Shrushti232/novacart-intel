from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.auth import verify_api_key
from app.core.models import ChatRequest, ChatResponse, DocumentUploadRequest, ErrorResponse, ToolCall
from app.core.validation import validate_document
from app.agent.agent import RetrievalAgent
from app.core.models import LoadedRecord
from app.ingestion.chunker import chunk_record
from app.ingestion.embedding import embed_text
from app.ingestion.index import index_chunks

app = FastAPI(title="NovaCart Intelligence Layer", version="0.1.0")


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"})


@app.get("/")
async def root():
    return JSONResponse({
        "name": "NovaCart Intelligence Layer",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST)",
            "upload": "/documents/upload (POST)",
        }
    })


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """Answer a question using the retrieval agent."""
    try:
        agent = RetrievalAgent()
        response = agent.ask(request.question)

        return ChatResponse(
            answer=response.final_answer,
            citations=response.cited_records,
            tool_calls=[
                ToolCall(
                    tool_name=call["tool_name"],
                    tool_input=call["tool_input"],
                    result=call["result"]
                )
                for call in response.tool_calls
            ],
            model_used=response.model_used,
        )
    except ValueError as e:
        if "OPENROUTER_API_KEY" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenRouter API key not configured"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="LLM rate limited, please try again later"
            )
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to reach LLM provider"
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM provider error"
        )


@app.post("/documents/upload", status_code=201)
async def upload_document(request: DocumentUploadRequest, api_key: str = Depends(verify_api_key)):
    """Ingest a single document: validate, chunk, embed, and index."""
    is_valid, error_msg = validate_document(request.source_type, request.data)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    try:
        loaded_record = LoadedRecord(data=request.data, source_type=request.source_type)
        chunk = chunk_record(loaded_record)

        embedding = embed_text(chunk.text)
        chunk.metadata["_embedding"] = embedding

        indexed_count = index_chunks([chunk])

        return JSONResponse({
            "status": "success",
            "record_id": chunk.record_id,
            "source_type": chunk.source_type,
            "indexed": indexed_count
        }, status_code=201)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document: {str(e)}"
        )
