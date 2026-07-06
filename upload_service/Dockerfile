FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 cookbook && \
    useradd --uid 10001 --gid cookbook --no-create-home cookbook && \
    mkdir -p /data/uploads && \
    chown -R cookbook:cookbook /data/uploads

COPY --chown=cookbook:cookbook app.py .

USER cookbook

EXPOSE 8790

CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8790", "--no-server-header"]
