FROM pagoda-base:latest

LABEL service="damage-detector"

WORKDIR /app

COPY common/ common/
COPY core/ core/
COPY damage_detection/ damage_detection/
COPY services/damage_detector/main.py main.py

ENV SERVICE_NAME=damage_detector
EXPOSE 8003

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8003", \
     "-w", "1", \
     "--timeout", "120", \
     "--access-logfile", "-"]
