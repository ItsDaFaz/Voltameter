# Use Python 3.11 (better stability with discord.py)
FROM python:3.11-slim-bookworm

# Set up environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining files
COPY . .

# Create non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import socket; socket.create_connection(('localhost', 8080), timeout=2)" || exit 1

CMD ["python", "bot.py"]