FROM python:3.11-slim

WORKDIR /app

# system deps for curl/jq if needed
RUN apt-get update && apt-get install -y curl jq gcc && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

# Run uvicorn (adjust import if your app module is different)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
