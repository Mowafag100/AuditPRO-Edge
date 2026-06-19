# استخدام نسخة خفيفة من بايثون
FROM python:3.11-slim

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# تثبيت المكتبات اللازمة للنظام

# استبدل السطر القديم بهذا السطر
RUN apt-get update && apt-get install -y libgl1 && rm -rf /var/lib/apt/lists/*
# نسخ ملفات المتطلبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود المصدري
COPY main.py .

# تشغيل السيرفر
CMD ["python", "main.py"]
