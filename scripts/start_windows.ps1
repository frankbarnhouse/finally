param(
    [switch]$Build,
    [switch]$Open
)

$ErrorActionPreference = "Stop"

$ImageName = "finally"
$ContainerName = "finally-app"
$VolumeName = "finally-data"
$Port = 8000

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# Check Docker is running
try {
    docker info *> $null
} catch {
    Write-Error "Docker is not running. Please start Docker and try again."
    exit 1
}

# Build image if forced or if image doesn't exist
$needsBuild = $Build
if (-not $needsBuild) {
    docker image inspect $ImageName *> $null
    if ($LASTEXITCODE -ne 0) {
        $needsBuild = $true
    }
}

if ($needsBuild) {
    Write-Host "Building $ImageName image..."
    docker build -t $ImageName $ProjectDir
}

# Check if container is already running
$running = docker ps --format '{{.Names}}' | Where-Object { $_ -eq $ContainerName }
if ($running) {
    Write-Host "FinAlly is already running at http://localhost:$Port"
    exit 0
}

# Remove any stopped container with the same name
docker rm $ContainerName 2>$null | Out-Null

# Run the container
docker run -d `
    --name $ContainerName `
    -v "${VolumeName}:/app/db" `
    -p "${Port}:8000" `
    --env-file "$ProjectDir\.env" `
    $ImageName

Write-Host "FinAlly is running at http://localhost:$Port"

# Open browser if requested
if ($Open) {
    Start-Process "http://localhost:$Port"
}
