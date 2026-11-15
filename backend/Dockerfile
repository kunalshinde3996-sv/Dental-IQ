# syntax=docker/dockerfile:1
# Dental-IQ API: FastAPI + SQLModel + scikit-learn.
# Migrations run on container start (docker-entrypoint.sh); tables are never auto-created in production.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    AUTO_CREATE_TABLES=false

WORKDIR /app

COPY requirements.txt .
# Optional extra CA (build secret, never stored in the image) for networks with TLS-inspecting
# proxies / antivirus. Set EXTRA_CA_CERT=/path/to/root.pem in .env; empty by default.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
        cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca-bundle.pem \
        && export PIP_CERT=/tmp/ca-bundle.pem; \
    fi \
    && pip install -r requirements.txt \
    && rm -f /tmp/ca-bundle.pem

COPY . .
# Unprivileged user; ml/artifacts is a volume mount point it must own (models are written by the seed).
RUN useradd --create-home --uid 10001 dentaliq \
    && mkdir -p /app/ml/artifacts \
    && chown -R dentaliq:dentaliq /app \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh
USER dentaliq

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
