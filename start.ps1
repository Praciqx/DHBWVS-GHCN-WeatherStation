if (Test-Path ".\WeatherStation") {
    Remove-Item -Path ".\WeatherStation" -Recurse -Force
}
New-Item -Path ".\WeatherStation" -ItemType Directory
Set-Location .\WeatherStation
Write-Host "Datenbank wird heruntergeladen."
Invoke-WebRequest -Uri https://www.swisstransfer.com/api/download/5050501b-e2f8-446f-8efe-e5497f965fef -OutFile .\database.zip
Write-Host "Datenbank wird entpackt."
Expand-Archive -Path .\database.zip -DestinationPath .\database -Force
Expand-Archive -Path .\database/database.zip -DestinationPath . -Force
Remove-Item .\database.zip
Remove-Item .\database\database.zip
Write-Host "docker-compose.yml wird heruntergeladen."
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/docker-compose.yml" -OutFile ".\docker-compose.yml"
Write-Host "Images werden heruntergeladen und Container erstellt."
docker compose up -d
Remove-Item .\docker-compose.yml
while ($true) {
    try {
        $Response = Invoke-WebRequest -Uri http://localhost:5000 -Method Head -TimeoutSec 5
        if ($Response.StatusCode -eq 200) {
            Start-Process http://localhost:5000
            break
        }
    } catch {
        Write-Host "Anwendung wird gestartet..."
    }
    Start-Sleep -Seconds 5
}
