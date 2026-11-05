FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV DATABASE_URL=postgresql://flyhigh:flyhigh@db:5432/flyhigh
EXPOSE 8000
CMD ["sh", "-c", "python -m app.seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
