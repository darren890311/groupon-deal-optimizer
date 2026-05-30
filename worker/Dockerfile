# Python analyzer worker — needs Chromium for Playwright, so it must be a
# container (this is the one service that genuinely requires Docker).
FROM python:3.13-slim

WORKDIR /app

# Install deps, then Chromium + its OS libraries via Playwright.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

# Cloud Run injects $PORT (defaults to 8080). Bind 0.0.0.0 so it's reachable.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
