# Matches .python-version (3.10) from Phase 1's environment setup.
# -slim keeps the base image smaller than the default python:3.10 image
# while still being a real Debian base (needed for apt-get below) —
# unlike -alpine, which frequently breaks ML packages (docling,
# sentence-transformers) that ship compiled C extensions.
FROM python:3.10-slim

# System libraries Docling's document-parsing pipeline needs
# (image/PDF handling pulls in some OpenCV-adjacent dependencies), plus
# curl for the HEALTHCHECK below. --no-install-recommends and the final
# apt cache cleanup keep the image from accumulating unnecessary layers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements BEFORE copying the rest of the code.
# Docker caches layers — as long as requirements.txt hasn't changed,
# this expensive install step is reused from cache on every rebuild,
# even if you've changed application code since. Reordering this after
# `COPY . .` would invalidate the pip-install cache on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 -r requirements.txt

COPY . .

# BAKED IN AT BUILD TIME, not container startup — see the Phase 13
# explanation: source documents are static, so ingesting and embedding
# them once here means every container start is instant, with no
# runtime dependency on network access or model downloads. Neither of
# these steps calls Groq — only local Docling parsing and a local/
# downloaded embedding model — so no secrets are needed at build time.
RUN python -m app.services.ingestion.pipeline
RUN python -m app.services.vector_store.build

EXPOSE 8501

# Streamlit exposes a built-in health endpoint — using it directly
# rather than hand-rolling one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# --server.address=0.0.0.0 is required: Streamlit defaults to
# localhost, which is unreachable from OUTSIDE the container. Binding
# to 0.0.0.0 means "listen on all interfaces," which is what makes
# `docker run -p 8501:8501` actually work.
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
