# Variables
$directoryPath = ".\WeatherStation"
$databaseDownloadUrl = "https://www.swisstransfer.com/api/download/5050501b-e2f8-446f-8efe-e5497f965fef"
$databaseZipPath = ".\database.zip"
$databaseExtractPath = ".\database"
$dockerComposeUrl = "https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/docker-compose.yml"
$dockerComposePath = ".\docker-compose.yml"
$webAppUrl = "http://localhost:5000"

# Remove existing directory if it exists
if (Test-Path $directoryPath) {
    Remove-Item -Path $directoryPath -Recurse -Force
}

# Create a new directory and navigate into it
New-Item -Path $directoryPath -ItemType Directory | Out-Null
Set-Location $directoryPath

# Download the database
Write-Host "Datenbank wird heruntergeladen..."
try {
    Invoke-WebRequest -Uri $databaseDownloadUrl -OutFile $databaseZipPath -ErrorAction Stop
} catch {
    Write-Host "Fehler beim Herunterladen der Datenbank."
    exit 1
}

# Extract the database
Write-Host "Datenbank wird entpackt..."
Expand-Archive -Path $databaseZipPath -DestinationPath $databaseExtractPath -Force
Expand-Archive -Path "$databaseExtractPath\database.zip" -DestinationPath . -Force

# Download the docker-compose file
Write-Host "docker-compose.yml wird heruntergeladen..."
try {
    Invoke-WebRequest -Uri $dockerComposeUrl -OutFile $dockerComposePath -ErrorAction Stop
} catch {
    Write-Host "Fehler beim Herunterladen der docker-compose.yml."
    exit 1
}

# Pull Docker images and start containers
Write-Host "Images werden heruntergeladen und Container erstellt..."
docker compose up -d

# Remove unnecessary files
Write-Host "Installationsdateien werden entfernt..."
Remove-Item $databaseZipPath
Remove-Item "$databaseExtractPath\database.zip"
Remove-Item $dockerComposePath

# Wait for the web application to start and then open it
Write-Host "Warte auf den Start der Anwendung..."
while ($true) {
    try {
        $response = Invoke-WebRequest -Uri $webAppUrl -Method Head -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "Anwendung erfolgreich gestartet!"
            Start-Process $webAppUrl
            break
        }
    } catch {
        Write-Host "Anwendung wird gestartet..."
    }
    Start-Sleep -Seconds 5
}
