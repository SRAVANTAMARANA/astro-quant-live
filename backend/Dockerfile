# backend/Dockerfile (Alpine)
FROM python:3.11-alpine

WORKDIR /app

# Install curl and jq and build deps for python wheels
RUN apk add --no-cache \
    curl \
    jq \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Upgrade pip
RUN pip install --upgrade pip

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
