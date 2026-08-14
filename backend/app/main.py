from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.db.session import init_db

logger = logging.getLogger(__name__)
settings = get_settings()
UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    try:
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        (UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
        (UPLOAD_ROOT / "documents").mkdir(parents=True, exist_ok=True)
        (UPLOAD_ROOT / "certificates").mkdir(parents=True, exist_ok=True)
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.exception("Database init failed: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": exc.detail.get("message") if isinstance(exc.detail, dict) else str(exc.detail),
            "data": exc.detail.get("details") if isinstance(exc.detail, dict) else None,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    message = exc.detail
    if isinstance(message, dict):
        message = message.get("message", str(message))
    return JSONResponse(
        status_code=exc.status_code,
        content={"statusCode": exc.status_code, "message": message, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "message": "Validation error",
            "data": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"statusCode": 500, "message": "Internal server error", "data": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
(UPLOAD_ROOT / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")
app.include_router(api_router)
