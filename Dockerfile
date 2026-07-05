# Stage 0: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_ROOT_PATH=
ENV VITE_ROOT_PATH=$VITE_ROOT_PATH
RUN npm run build


# Stage 1: run tests
# If any test fails, the build stops here.
FROM python:3.13-slim AS test

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest httpx fakeredis

COPY src/ src/
COPY tests/ tests/
# Provide the built frontend so the SPA catch-all route can serve index.html
COPY --from=frontend-build /frontend/dist/ src/static/

RUN pytest tests/ -v && touch /tmp/tests-passed


# Stage 2: production image
# Only runtime code — no test files or test dependencies.
FROM python:3.13-slim

WORKDIR /app

# Referencing the test stage forces Docker to build it (and run pytest) before
# continuing. If any test fails, the build stops here.
COPY --from=test /tmp/tests-passed /tmp/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/wlingo wlingo/
COPY src/vocabulary vocabulary/
COPY --from=frontend-build /frontend/dist/ static/

EXPOSE 8002

CMD ["uvicorn", "wlingo.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
