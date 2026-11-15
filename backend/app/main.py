"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.database import create_db_and_tables
from app.routers import academic, admin, allocation, analytics, auth, cases, faculty, intelligence, patients, students

settings = get_settings()
logger = logging.getLogger("dental_iq")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Dental-IQ: one supervised clinical case feeds the patient's EHR, the student's competency "
        "log and population data.\n\n"
        "**Phase 1:** auth, patients, cases + FDI tooth findings, approvals, quotas, attendance, marks.\n\n"
        "Click **Authorize** and log in with a demo account (see README) to try endpoints."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error: %s", exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Request conflicts with existing data (duplicate or invalid reference)"},
    )


for router in (auth.router, patients.router, cases.router, students.router, faculty.router,
               academic.router, admin.router, analytics.router, intelligence.router,
               allocation.router):
    app.include_router(router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
