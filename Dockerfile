FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WELLPACK_DATA_DIR=/app/data FREE_DEMO=true WEB_SEARCH_ENABLED=false AUTO_SCAN=false MAX_PAID_REQUESTS_PER_DAY=0
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 wellpack && mkdir -p /app/data && chown wellpack:wellpack /app/data
COPY --chown=wellpack:wellpack app.py security.py ./
COPY --chown=wellpack:wellpack engine/ ./engine/
COPY --chown=wellpack:wellpack static/ ./static/
COPY --chown=wellpack:wellpack frontend-release/ ./frontend-release/
COPY --chown=wellpack:wellpack build_frontend.py ./
USER wellpack
RUN python build_frontend.py
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
