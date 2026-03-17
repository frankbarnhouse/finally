#!/usr/bin/env bash
set -e

IMAGE_NAME="finally"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Parse flags
FORCE_BUILD=false
OPEN_BROWSER=false
for arg in "$@"; do
    case "$arg" in
        --build) FORCE_BUILD=true ;;
        --open)  OPEN_BROWSER=true ;;
    esac
done

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build image if forced or if image doesn't exist
if [ "$FORCE_BUILD" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building $IMAGE_NAME image..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR"
fi

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "FinAlly is already running at http://localhost:$PORT"
    exit 0
fi

# Remove any stopped container with the same name
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Run the container
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME":/app/db \
    -p "$PORT":8000 \
    --env-file "$PROJECT_DIR/.env" \
    "$IMAGE_NAME"

echo "FinAlly is running at http://localhost:$PORT"

# Open browser if requested
if [ "$OPEN_BROWSER" = true ]; then
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:$PORT"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:$PORT"
    fi
fi
