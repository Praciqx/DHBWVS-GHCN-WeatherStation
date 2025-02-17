from flask import Flask, render_template, request,jsonify
import folium
import psycopg2
import gzip
import io
import pandas as pd
import requests

app = Flask(__name__)

#Klasse zum Erstellen und automatisch beenden Connection
class DatabaseConnection:
    def __enter__(self):
        self.connection = psycopg2.connect(database="dhbwvsghcn", user="admin", password="secretpassword", host="db", port=5432)
        self.cursor = self.connection.cursor()
        return self.cursor
    
    def __exit__(self,t,d,g):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


@app.route('/')
def index():
    default_lat, default_lon = 48.0594, 8.4641
    default_radius = 5000
    karte_html = create_map(default_lat, default_lon, default_radius,0)
    return render_template("index.html", karte_html=karte_html)

@app.route('/get_stations')
def get_stations():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', type=float)
    stations = request.args.get('stations', type=int)
    return jsonify(map_html=create_map(lat,lon,radius,stations))

def create_map(lat, lon, radius,stations):
    karte = folium.Map(location=[lat, lon], zoom_start=11,attributionControl=0)

    folium.Marker(location=[lat, lon], popup="Zentrum").add_to(karte)

    beispiel_stationen = [
        {"name": "Station 1", "lat": lat + 0.01, "lon": lon + 0.01},
        {"name": "Station 2", "lat": lat - 0.01, "lon": lon - 0.01},
        {"name": "Station 3", "lat": lat + 0.02, "lon": lon + 0.02}]

    for station in beispiel_stationen:
        folium.Marker(
            location=[station["lat"], station["lon"]],
            popup=f"<b>{station['name']}",
            tooltip=station["name"], icon = folium.Icon(color="red")).add_to(karte)

    folium.Circle(
        location=[lat, lon],
        radius=radius*1000,
        color="blue",
        fill=True,
        fill_opacity=0.4).add_to(karte)
    karte._id = "station_map"
          
    return karte._repr_html_()

def create_tables():
    with DatabaseConnection() as cursor:
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS "station" (
                    "station_id" character(25) PRIMARY KEY,
                    "latitude" NUMERIC(7,4) NOT NULL,
                    "longitude" NUMERIC(7,4) NOT NULL,
                    "station_name" character(100) NOT NULL
            );''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS stationdata (
                data_id SERIAL primary key,
                station_id character(25) NOT NULL,
                measure_date DATE NOT NULL,
                measure_type VARCHAR(10) NOT NULL, 
                measure_value integer NOT NULL,
                season INTEGER GENERATED ALWAYS AS (
                    CASE 
                        WHEN EXTRACT(MONTH FROM measure_date) IN (12, 1, 2) THEN 1
                        WHEN EXTRACT(MONTH FROM measure_date) IN (3, 4, 5) THEN 2
                        WHEN EXTRACT(MONTH FROM measure_date) IN (6, 7, 8) THEN 3
                        WHEN EXTRACT(MONTH FROM measure_date) IN (9, 10, 11) THEN 4
                    END
                ) STORED,
                UNIQUE (station_id, measure_date,measure_type)
            );''')
            cursor.connection.commit()
        except Exception as ex:
            print(ex)

def get_ghcn_stations(file_path):
    with DatabaseConnection() as cursor:
        try:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM station)")
            exists = cursor.fetchone()[0]
            if not exists:
                with open(file_path, 'r') as file:
                    for line in file:
                        data = line.strip().split()
                        if len(data) < 4: 
                            continue
                        
                        station_id = data[0]
                        latitude = data[1]
                        longitude = data[2]
                        station_name = data[4]
                        cursor.execute('''
                            INSERT INTO station (station_id, latitude, longitude, station_name) ON CONFLICT (station_id, latitude, longitude, station_name)
                            DO NOTHING VALUES (%s, %s, %s, %s)
                        ''', (station_id, latitude, longitude, station_name))
            cursor.connection.commit()
        except Exception as ex:
            print(ex)

def get_ghcn_data_by_year(year):
    gzipped_file = download_file(year)
    print("test")
    if gzipped_file:
        with DatabaseConnection() as cursor:
            try:
                with gzip.open(gzipped_file, "rt", encoding="utf-8") as f:
                    df = pd.read_csv(f, delimiter=",", header=None, usecols=[0,1,2,3], names=["station_id", "measure_date", "measure_type", "measure_value"])
                    df = df[df["measure_type"].isin(["TMAX", "TMIN"])]
                    df["measure_date"] = pd.to_datetime(df["measure_date"].astype(str), format='%Y%m%d')

                    for _, row in df.iterrows():
                        cursor.execute("""
                            INSERT INTO stationdata (station_id, measure_date, measure_type, measure_value)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (station_id,measure_date,measure_type) 
                            DO NOTHING
                        """, (row["station_id"], row["measure_date"], row["measure_type"], row["measure_value"]))
                
                cursor.connection.commit()
                print("Daten erfolgreich in die Datenbank eingefügt.")
            except Exception as ex:
                print(f"Fehler beim Verarbeiten der Datei: {ex}")   

def download_file(year):
    baseURLbyYear = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_year/PLACEHOLDER.csv.gz"
    print("Herunterladen der {year} Datei.")
    baseURLbyYear = baseURLbyYear.replace("PLACEHOLDER",year)
    print(baseURLbyYear)
    response = requests.get(baseURLbyYear)
    print(response)
    response.raise_for_status()
    print("Herunterladen abgeschlossen")
    return io.BytesIO(response.content)

create_tables()
get_ghcn_stations("./data/ghcnd-stations.txt")
get_ghcn_data_by_year("2024")

if __name__ == "__main__":
    app.run(debug=True)

