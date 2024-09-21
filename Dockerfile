# Use the official Python Alpine image
FROM python:alpine

# Set environment variables (can be overridden at runtime)
ENV UPLOAD_ROOT=/upload_root
ENV UPLOAD_DELAY_SECONDS=60
ENV CONCURRENCY=4

# these shouldn't be overriden (but shouldn't matter if they are)
ENV WATCHED_DIRECTORY=/watched
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV REDIS_SET=files_to_upload

# Install required packages
RUN apk update && \
    apk add --no-cache redis bash curl && \
    rm -rf /var/cache/apk/*

# Install inotify-tools from the edge testing repository
RUN echo "@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache inotify-tools@testing

# Install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --root-user-action=ignore --no-cache-dir -r /app/requirements.txt

# Create the working directory
WORKDIR /app

# Copy the Python script and entrypoint script into the container
COPY upload_files.py /app/upload_files.py
COPY entrypoint.sh /app/entrypoint.sh
COPY healthcheck.sh /app/healthcheck.sh

RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 CMD /app/healthcheck.sh

# Set the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
