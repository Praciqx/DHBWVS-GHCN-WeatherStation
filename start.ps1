# Variables
$directoryPath = ".\WeatherStation"
$dockerComposeUrl = "https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/docker-compose.yml"
$databaseDownloadUrl = "https://www.swisstransfer.com/api/download/d98ded26-7923-4196-a14b-d49ca872d839"

# Remove existing directory if it exists
if (Test-Path $directoryPath) {
    Remove-Item -Path $directoryPath -Recurse -Force
}

# Create a new directory and navigate into it
New-Item -Path $directoryPath -ItemType Directory | Out-Null
Set-Location $directoryPath

# Download the database
Write-Host "Datenbank wird heruntergeladen."
Invoke-WebRequest -Uri $databaseDownloadUrl -OutFile ".\database.zip"

# Extract the database
Write-Host "Datenbank wird entpackt."
Expand-Archive -Path ".\database.zip" -DestinationPath ".\database" -Force
Expand-Archive -Path ".\database\database.zip" -DestinationPath . -Force

# Download the docker-compose file
Invoke-WebRequest -Uri $dockerComposeUrl -OutFile ".\docker-compose.yml"

# Pull Docker images and start containers
Write-Host "Images werden heruntergeladen und Container erstellt."
docker compose up -d

# Remove unnecessary files
Remove-Item ".\database.zip"
Remove-Item ".\database\database.zip"
Remove-Item ".\docker-compose.yml"

# Wait for the web application to start and then open it
while ($true) {
    try {
        $response = Invoke-WebRequest -Uri http://localhost:5000 -Method Head -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Start-Process http://localhost:5000
            break
        }
    } catch {
        Write-Host "Anwendung wird gestartet..."
    }
    Start-Sleep -Seconds 5
}
