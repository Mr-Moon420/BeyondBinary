# ── Stage 1: Runtime Environment ──────────────────────────────────────────────
FROM python:3.11-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    HOME=/home/user

# Install system dependencies (build-essential, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Hugging Face Spaces requirement UID 1000)
RUN useradd -m -u 1000 user
WORKDIR $HOME/app

# Install CPU-optimized PyTorch first (~200MB download instead of heavy 2.5GB CUDA)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install (filtering torch to retain CPU wheel)
COPY --chown=user:user requirements.txt .
RUN grep -v "^torch" requirements.txt > reqs_no_torch.txt && \
    pip install --no-cache-dir -r reqs_no_torch.txt && \
    python -m spacy download en_core_web_sm

# Install Playwright Chromium & OS browser dependencies for web scraping
RUN playwright install --with-deps chromium || true

# Copy full application code & static assets
COPY --chown=user:user . .

# Ensure user permissions
RUN mkdir -p /home/user/.cache && chown -R user:user /home/user
USER user

# Warm-up pre-cache for lightweight neural models (reduces first-request cold start)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

EXPOSE 10000

# Launch FastAPI via Uvicorn binding dynamically to Render's $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
