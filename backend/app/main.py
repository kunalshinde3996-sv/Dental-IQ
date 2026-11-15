"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.database import create_db_and_tables
from app.routers import (
    academic,
    admin,
    allocation,
    analytics,
    auth,
    cases,
    faculty,
    intelligence,
    overview,
    patients,
    students,
    trust,
)

settings = get_settings()  # validates secrets; raises ConfigError on unsafe production settings
logger = logging.getLogger("dental_iq")
VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.create_tables_on_startup:  # never in production: Alembic owns the schema there
        create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=VERSION,
    description=(
        "Dental-IQ: one supervised clinical case feeds the patient's EHR, the student's competency "
        "log and population data. Includes population analytics, explainable risk models, smart "
        "allocation, audit trail and FHIR export.\n\n"
        "Click **Authorize** and log in with a demo account (see README) to try endpoints. "
        "All data is synthetic."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
)

# Compress JSON responses: analytics/alert payloads are 50-110 KB uncompressed.
app.add_middleware(GZipMiddleware, minimum_size=1024)
# Bearer tokens (not cookies) => no credentials needed; origins come only from CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",  # health records must not be cached by shared proxies
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
    return response


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error: %s", exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Request conflicts with existing data (duplicate or invalid reference)"},
    )


for router in (auth.router, patients.router, cases.router, students.router, faculty.router,
               academic.router, admin.router, analytics.router, intelligence.router,
               allocation.router, trust.router, overview.router):
    app.include_router(router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "environment": settings.app_env}
