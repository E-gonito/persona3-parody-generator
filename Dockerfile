FROM ubuntu:22.04

# Set global environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    APP_ENV=production \
    DEBUG_MODE=0

WORKDIR /usr/src

# Install dependencies as root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    expect \
    tzdata && \
    pip3 install requests python-dotenv

# Create user and set permissions BEFORE switching
RUN useradd --create-home appuser && \
    mkdir -p /usr/src && \
    chown -R appuser:appuser /usr/src

# Copy files while still root
COPY . . 

# Set permissions while still root
RUN chmod +x docker-entrypoint.sh

# Switch to appuser
USER appuser

# Final command
ENTRYPOINT ["/usr/src/docker-entrypoint.sh"] 