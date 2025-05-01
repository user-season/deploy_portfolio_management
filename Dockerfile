# 1. Sử dụng image base
FROM python:3.11-slim-bullseye

# 2. Thiết lập biến môi trường để tối ưu hóa Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 3. Thư mục làm việc tại /app
WORKDIR /app

# 4. Copy file requirements và cài dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
apt-get install -y postgresql-client && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# 5. Copy mã nguồn vào /app
COPY . .

# 6. Làm cho entrypoint.sh có quyền thực thi
RUN chmod +x ./entrypoint.sh


# 7. Sử dụng entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# 8. Chạy server
CMD ["gunicorn", "--chdir", "/app/src", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
