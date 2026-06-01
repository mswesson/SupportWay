FROM python:3.14-slim AS base

WORKDIR /app/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip cache purge && rm requirements.txt

COPY src/ ./src/
COPY alembic.ini ./

ARG VERSION
ARG BUILD_NUMBER
ENV SUPPORT_SERVICE_VERSION=${VERSION}
ENV SUPPORT_BUILD_NUMBER=${BUILD_NUMBER}
ENV NUM_OF_WORKERS=1

CMD ["sh", "-c", "fastapi run src/main.py --port 8080 --workers ${NUM_OF_WORKERS}"]

FROM base AS production
