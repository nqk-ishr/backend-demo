FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --system --uid 10001 --no-create-home app
USER app
EXPOSE 3000
# --no-server-header: không khoe tên và phiên bản máy chủ trong header phản hồi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000", "--no-server-header"]
