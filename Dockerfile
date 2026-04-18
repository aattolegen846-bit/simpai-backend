FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=5001

# Install system dependencies (for psycopg2 or other C-extensions if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' simpai && chown -R simpai:simpai /app
USER simpai

# Expose the application port
EXPOSE 5001

# Start the application using Gunicorn with the professional config
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]
