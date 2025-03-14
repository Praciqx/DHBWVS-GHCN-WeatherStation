<p align="center">
  <img src="https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/static/images/favicon.ico" width="10%">
</p>

<p align="center">
  Eine Anwendung zur Suche und Analyse von Wetterstationsdaten anhand geografischer Koordinaten
</p>

# Funktionen
- **Wetterstationen suchen** nach Breiten-/Längengrad & Radius
- **Analyse der Temperaturdaten pro Jahr & Jahreszeit**
- **Zeitraum frei wählbar**
- **Grafische & tabellarische Darstellung**

# Installation

**Voraussetzung:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) muss installiert sein.

Danach einfach folgenden Befehl in einer PowerShell-Konsole ausführen:

```powershell
irm "https://raw.githubusercontent.com/Praciqx/DHBWVS-GHCN-WeatherStation/main/start.ps1" | iex
```

Dies erstellt automatisch den Ordner `WeatherStation` und startet die Anwendung.

# Nutzung

Nach der Installation ist die Anwendung unter [http://localhost:5000](http://localhost:5000) erreichbar.

<p align="center">
  <img src="https://github.com/user-attachments/assets/f2688063-9cc4-4b72-a5c6-5f6e46a31f8c" width="100%">
</p>

### **1️. Stationssuche**
- Eingabe folgender Parameter: **Breitengrad, Längengrad, Radius, Anzahl Stationen & Zeitraum**
- Suche starten

<p align="center">
  <img src="https://github.com/user-attachments/assets/241e8513-197f-4be0-8104-c32a1c909af6" width="100%">
</p>

### **2️. Stationsauswahl**
Nach der Suche erscheinen alle gefundenen Stationen:

<p align="center">
  <img src="https://github.com/user-attachments/assets/b126b14c-fc66-45fb-8612-6032dc6502b9" width="100%">
</p>

### **3️. Datenanalyse**
Für jede Station stehen zwei Darstellungsarten zur Verfügung:
- **Tabellarische Ansicht** der Mittelwerte für Höchst- und Tiefsttemperaturen
- **Grafische Visualisierung** per Chart

<p align="center">
  <img src="https://github.com/user-attachments/assets/886320a9-5e13-4da4-8853-5c10c0851dd9" width="100%">
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/77658b7a-019c-449e-850a-30b02e3cc268" width="100%">
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/c2a8a5bf-8cbd-4665-9a14-dece1bb11efb" width="100%">
</p>
