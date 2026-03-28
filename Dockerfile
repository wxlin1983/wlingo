# Stage 1: run tests
# If any test fails, the build stops here.
FROM python:3.11-slim AS test

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest httpx

COPY src/ src/
COPY tests/ tests/

RUN pytest tests/ -v && touch /tmp/tests-passed


# Stage 2: production image
# Only runtime code is copied — no test files or test dependencies.
FROM python:3.11-slim

WORKDIR /app

# Referencing the test stage forces Docker to build it (and run pytest) before
# continuing. If any test fails, the build stops here.
COPY --from=test /tmp/tests-passed /tmp/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/static static/
COPY src/wlingo wlingo/
COPY src/templates templates/
COPY src/vocabulary vocabulary/

EXPOSE 8002

CMD ["uvicorn", "wlingo.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
