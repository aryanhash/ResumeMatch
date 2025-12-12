# AutoApply AI Backend Dockerfile
FROM python:3.11-slim

# SECURITY: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies
# Note: LaTeX (texlive) is required for professional resume PDF generation
# If LaTeX is not needed, you can remove texlive packages to reduce image size
RUN apt-get update && apt-get install -y \
    curl \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# SECURITY: Change ownership to non-root user
RUN chown -R appuser:appuser /app

# SECURITY: Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check (using Python instead of curl to avoid needing curl)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

