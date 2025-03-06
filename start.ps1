Write-Host "docker-compose.yml wird heruntergeladen."
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/docker-compose.yml" -OutFile ".\docker-compose.yml"
Write-Host "Images werden heruntergeladen und Container erstellt."
docker compose up -d
Write-Host "Container sind erstellt und fahren nun hoch, Website http://localhost:5000 wird in 5 Sekunden aufgerufen."
Start-Sleep -Seconds 5
Start-Process "http://localhost:5000"