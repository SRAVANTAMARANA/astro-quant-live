# ============================
# Backend Dockerfile (Alpine)
# ============================

FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system tools (curl + jq + build deps for pip)
RUN apk add --no-cache \
    curl \
    jq \
    gcc \
    musl-dev \
    libffi-dev \
    && pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
