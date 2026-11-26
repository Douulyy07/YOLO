# Image de MaintAI : le code et ses bibliothèques, sans les données ni le modèle.
# Construire : docker build -t maintai:0.4.0 .

FROM python:3.11-slim

WORKDIR /app

# Les bibliothèques d'abord : cette étape lente reste en cache tant que requirements-docker.txt ne change pas
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Le code ensuite : il change souvent, donc il vient en dernier
COPY maintai ./maintai
COPY ui ./ui

# Où le modèle et les données seront montés au lancement (volumes)
ENV MAINTAI_MODELS_DIR=/app/models \
    MAINTAI_DATA_PATH=/app/data/sensors.csv

EXPOSE 8000
CMD ["uvicorn", "maintai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]