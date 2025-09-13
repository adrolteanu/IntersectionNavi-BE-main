# ──────────────────────────────────────────────────────────────────────────────
# File: Dockerfile
#
# Builds a base image that installs SUMO (CLI always; GUI only if
# INSTALL_GUI=true is passed at build time).
# ──────────────────────────────────────────────────────────────────────────────
ARG INSTALL_GUI=false
FROM ubuntu:22.04

# avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# ──────────────────────────────────────────────────────────────────────────────
# System‐level dependencies
# ──────────────────────────────────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-pip python3-dev build-essential \
      curl wget git netcat-openbsd \
      sumo sumo-tools \
    && if [ "$INSTALL_GUI" = "true" ]; then \
         apt-get install -y sumo-gui \
           libxrender1 libxrandr2 libxcursor1 \
           libxinerama1 libxi6 libglib2.0-0; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# ──────────────────────────────────────────────────────────────────────────────
# Python dependencies
# ──────────────────────────────────────────────────────────────────────────────
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt Rtree pyproj

# ──────────────────────────────────────────────────────────────────────────────
# Copy application
# ──────────────────────────────────────────────────────────────────────────────
COPY . /app

# ──────────────────────────────────────────────────────────────────────────────
# Expose Flask port
# ──────────────────────────────────────────────────────────────────────────────
EXPOSE 5000

# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint: wait a bit for Mongo, then launch the headless engine
# ──────────────────────────────────────────────────────────────────────────────
CMD ["sh", "-c", "sleep 5 && python3 headless.py"]
