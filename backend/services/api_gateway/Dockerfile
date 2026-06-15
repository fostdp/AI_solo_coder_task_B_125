FROM pagoda-base:latest

LABEL service="api-gateway"

WORKDIR /app

COPY common/ common/
COPY core/ core/
COPY api/ api/
COPY services/api_gateway/main.py main.py

ENV SERVICE_NAME=api_gateway
EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "-w", "4", \
     "--timeout", "60", \
     "--access-logfile", "-"]
