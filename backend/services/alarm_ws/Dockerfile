FROM pagoda-base:latest

LABEL service="alarm-ws"

WORKDIR /app

COPY common/ common/
COPY core/ core/
COPY alerts/ alerts/
COPY services/alarm_ws/main.py main.py

ENV SERVICE_NAME=alarm_ws
EXPOSE 8004

CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8004", \
     "-w", "2", \
     "--timeout", "60", \
     "--access-logfile", "-"]
