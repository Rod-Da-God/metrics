FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgeos-dev \
    libgeos++-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /metrics

COPY src/ ./src/

ENV PYTHONPATH=/metrics

CMD ["python", "src/main.py"]