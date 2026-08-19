FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create working directory
WORKDIR /fwdbot
COPY . /fwdbot

# Make start script executable
RUN chmod +x /fwdbot/start.sh

CMD ["/bin/bash", "/fwdbot/start.sh"]
