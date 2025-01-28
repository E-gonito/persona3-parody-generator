FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Create separate directories
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    expect \
    tzdata \
    dos2unix && \
    pip3 install requests python-dotenv

# Create user and set permissions
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app

# Copy all files
COPY . .

# Fix Windows line endings and permissions
RUN dos2unix /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]