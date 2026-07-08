# Base stage: official python slim runtime
FROM python:3.10-slim

# Prevent python from writing pyc files to disk and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install system dependencies (build-essential, procps for psutil)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install python modules from both backend and engine
COPY backend/requirements.txt ./backend_requirements.txt
COPY engine/requirements.txt ./engine_requirements.txt

RUN pip install --no-cache-dir -r ./backend_requirements.txt
RUN pip install --no-cache-dir -r ./engine_requirements.txt

# Copy source codes
COPY backend/app/ ./app/
COPY engine/ ./engine/
COPY model/ ./model/
COPY backend/.env .

# Download basic spaCy language model for NER (en_core_web_sm)
RUN python -m spacy download en_core_web_sm

# Expose port
EXPOSE 8000

# Run Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
