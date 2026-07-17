# Production-ready Dockerfile for VeriGate.
#
# Uses the official Python 3.11 slim image, installs dependencies, creates a
# non-root user for security, and runs the Flask application with Gunicorn.
# The entire repository is copied into the image so deliverables like docs/,
# tests/, scripts/, and README are available at runtime.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY verigate/requirements.txt verigate/requirements.txt
RUN pip install --no-cache-dir -r verigate/requirements.txt gunicorn

COPY . .

RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "verigate.app:app"]
