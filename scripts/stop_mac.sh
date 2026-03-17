#!/usr/bin/env bash
set -e

CONTAINER_NAME="finally-app"

# Stop the container (ignore error if not running)
docker stop "$CONTAINER_NAME" 2>/dev/null || true

# Remove the container (ignore error if not found)
docker rm "$CONTAINER_NAME" 2>/dev/null || true

echo "FinAlly stopped. Data preserved in Docker volume."
