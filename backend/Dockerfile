FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system app && useradd --system --create-home --gid app app
ENV HF_HOME=/home/app/.cache/huggingface
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts
COPY docker/production-entrypoint.sh /usr/local/bin/production-entrypoint
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 10 \
    torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 10 .
RUN chmod 0755 /usr/local/bin/production-entrypoint \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /home/app
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
