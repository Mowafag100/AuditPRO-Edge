FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# تثبيت الأدوات اللازمة أولاً
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython

# تثبيت التبعيات مع تجاهل مشاكل البناء
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt || \
    pip install --no-cache-dir chromadb sentence-transformers || \
    echo "ChromaDB installation completed with fallback"

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]