$ErrorActionPreference = "Stop"

$ContainerName = "finally-app"

# Stop the container (ignore error if not running)
docker stop $ContainerName 2>$null | Out-Null

# Remove the container (ignore error if not found)
docker rm $ContainerName 2>$null | Out-Null

Write-Host "FinAlly stopped. Data preserved in Docker volume."
