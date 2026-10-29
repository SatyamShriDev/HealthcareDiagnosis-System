import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (register tables)
from .config import settings
from .database import Base, engine
from .routers import auth, features, predictions
from .services import prediction_service

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates tables on first start
    yield


app = FastAPI(title="Heart Risk Prediction (educational demo)", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth.router)
app.include_router(features.router)
app.include_router(predictions.router)


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": prediction_service.get_model_info()["available"]}
