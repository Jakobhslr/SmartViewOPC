FROM python:3.11-slim

WORKDIR /app

# Abhängigkeiten zuerst (Layer-Caching)
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

# Quellcode kopieren
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Datenbankverzeichnis anlegen
RUN mkdir -p data

EXPOSE 5000

CMD ["uv", "run", "python", "backend/api.py"]
