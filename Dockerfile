# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chmod +x /app/scripts/*.py

# Collect static files (will be done at runtime in production)
# RUN python manage.py collectstatic --noinput

# Create a non-root user to run the application
RUN useradd -m -u 1000 medipredict_user && \
    chown -R medipredict_user:medipredict_user /app

USER medipredict_user

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "disease_app.wsgi:application"]