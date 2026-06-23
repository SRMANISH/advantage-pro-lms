FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .

EXPOSE 8000

# Default (production) command. docker-compose overrides this for local dev.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
