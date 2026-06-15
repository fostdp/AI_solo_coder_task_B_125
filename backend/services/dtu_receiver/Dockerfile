FROM pagoda-base:latest

LABEL service="dtu-receiver"

WORKDIR /app

COPY common/ common/
COPY core/ core/
COPY api/ api/
COPY config_loader_ref.py .
COPY services/dtu_receiver/main.py main.py

ENV SERVICE_NAME=dtu_receiver
EXPOSE 8001

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8001", \
     "-w", "2", \
     "--timeout", "30", \
     "--access-logfile", "-"]
