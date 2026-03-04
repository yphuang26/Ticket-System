FROM python:3.10-slim

WORKDIR /code

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 預設啟動 web（可被 docker-compose 覆蓋）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
