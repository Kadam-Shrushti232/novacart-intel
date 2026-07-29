from fastapi import FastAPI
from fastapi.responses import JSONResponse

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
        }
    })
