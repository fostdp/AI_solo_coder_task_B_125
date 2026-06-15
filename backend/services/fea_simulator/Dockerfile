FROM pagoda-base:latest

LABEL service="fea-simulator"

WORKDIR /app

COPY common/ common/
COPY core/ core/
COPY simulation/ simulation/
COPY services/fea_simulator/main.py main.py

ENV SERVICE_NAME=fea_simulator
EXPOSE 8002

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8002", \
     "-w", "1", \
     "--timeout", "300", \
     "--access-logfile", "-"]
