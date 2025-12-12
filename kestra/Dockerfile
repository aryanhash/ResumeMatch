FROM kestra/kestra:latest

# Set working directory
WORKDIR /app

# Copy configuration files
# We rename it to application.yml so Kestra picks it up automatically if no env var is set
# But we will specifically point to it via env var just in case
COPY kestra-render.yml /app/kestra-render.yml

# Copy workflows to be auto-discovered (if supported) or manually available
COPY autoapplyai_pipeline.yaml /app/flows/autoapplyai_pipeline.yaml

# Expose the port
EXPOSE 8080

# Set environment variables
ENV MICRONAUT_CONFIG_FILES=/app/kestra-render.yml
ENV KESTRA_CONFIGURATION_FILE=/app/kestra-render.yml
# Ensure java uses container limits
ENV JAVA_OPTS="-XX:+ExitOnOutOfMemoryError -Xmx512m"

# Command to run Kestra Standalone
CMD ["server", "standalone"]
