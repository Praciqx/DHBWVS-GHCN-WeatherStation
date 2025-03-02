from flask import Flask, render_template, request,jsonify,render_template_string
import folium
import psycopg2
from folium.map import Marker
from jinja2 import Template
import gzip
import io
import pandas as pd
import requests
from psycopg2.extras import execute_values
import json

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
    return render_template("index.html",year_range = getMinMaxYear())

def getMinMaxYear():
    return {
        "maxYear":2024,
        "minYear":1755
    }

@app.route('/get_stations')
def get_stations():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', type=float)
    station_count = request.args.get('stations', type=int)
    
    selectedstations = get_stations_within_radius(lat, lon, radius, station_count)
    stations = []
    for station_id, station_name,distance, station_lat, station_lon  in selectedstations:
        stations.append({
            "id": station_id,
            "lat": station_lat,
            "lon": station_lon,
            "address": station_name,
            "km": f"{distance}km"
        })
        
    stations_data = {
        "center": {
            "lat": lat,
            "lon": lon,
            "adress": "Zentrum",
            "radius": radius * 1000 
        },
        "stations": stations
    }
    return jsonify(stations_data)

@app.route('/get_station_data')
def get_station_data():
    stationid = request.args.get('stationid', type=str)
    datefrom = request.args.get('datefrom', type=int)
    dateto = request.args.get('dateto', type=int)

    query = """
        SELECT measure_year, maxyear,minyear,maxspring,minspring,maxsummer,minsummer,maxautumn,minautumn,maxwinter,minwinter FROM stationdata where station_id = %s and measure_year between %s and %s;
    """

    with DatabaseConnection() as cursor:
        cursor.execute(query,(stationid, datefrom, dateto))
        fetcheddata = cursor.fetchall()
        cursor.connection.commit()
        
    df = pd.DataFrame(fetcheddata, columns=["year","max","min","springmax","springmin","summermax","summermin","autumnmax","autumnmin","wintermax","wintermin"])
    # Struktur für Charts
    data = {
        "years": df["year"].tolist(),
        "seasons": {
            "Jahr": {"min": df["min"].tolist(), "max": df["max"].tolist()},
            "Frühling": {"min": df["springmin"].tolist(), "max": df["springmax"].tolist()},
            "Sommer": {"min": df["summermin"].tolist(), "max": df["summermax"].tolist()},
            "Herbst": {"min": df["autumnmin"].tolist(), "max": df["autumnmax"].tolist()},
            "Winter": {"min": df["wintermin"].tolist(), "max": df["wintermax"].tolist()},
        }
    }
    # Struktur für die Tabellen
    seasontabledata = json.loads(df.to_json(orient="records"))
    seasontemplate = render_template("seasontabledata.html",data=seasontabledata,stationid = stationid)
    yearlytemplate = render_template("yearlytabledata.html",data=seasontabledata, stationid = stationid)
    return jsonify(data=data, seasontemplate = seasontemplate,yearlytemplate = yearlytemplate)


def create_tables():
    with DatabaseConnection() as cursor:
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS "station" (
                "station_id" character(25) PRIMARY KEY,
                "latitude" NUMERIC(7,4) NOT NULL,
                "longitude" NUMERIC(7,4) NOT NULL,
                "station_name" character(100) NOT NULL,
                "station_point" geography(Point, 4326) NOT NULL
            );''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS stationdata (
                station_id character(25),
                measure_year smallint NOT NULL,
                maxyear numeric(7,3),
                minyear numeric(7,3),
                maxspring numeric(7,3),
                minspring numeric(7,3),
                maxsummer numeric(7,3),
                minsummer numeric(7,3),
                maxautumn numeric(7,3),
                minautumn numeric(7,3),
                maxwinter numeric(7,3),
                minwinter numeric(7,3),
                PRIMARY KEY (station_id, measure_year)
            );''')
            cursor.connection.commit()
        except Exception as ex:
            print(ex)

import csv

def get_ghcn_stations(file_path):
    with DatabaseConnection() as cursor:
        try:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM station)")
            exists = cursor.fetchone()[0]
            if not exists:
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file) 
                    next(reader)

                    for row in reader:
                        if len(row) < 4:
                            continue
                        
                        station_id = row[0].strip()
                        latitude = float(row[1].strip())
                        longitude = float(row[2].strip())
                        station_name = row[5].strip()

                        cursor.execute('''
                            INSERT INTO station (station_id, latitude, longitude, station_name, station_point)
                            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326))
                            ON CONFLICT (station_id) DO NOTHING;
                        ''', (station_id, latitude, longitude, station_name, longitude, latitude))
            cursor.connection.commit()
        except Exception as ex:
            print(f"Fehler beim Einfügen: {ex}")


def insert_ghcn_by_year(year):
    gzipped_file = download_file(year)
    if gzipped_file:
        with DatabaseConnection() as cursor:
            try:
                with gzip.open(gzipped_file, "rt", encoding="utf-8") as f:
                    df = pd.read_csv(f, delimiter=",", header=None, usecols=[0, 1, 2, 3],
                                     names=["station_id", "measure_date", "measure_type", "measure_value"])
                    df = df[df["measure_type"].isin(["TMAX", "TMIN"])]
                    df["measure_date"] = pd.to_datetime(df["measure_date"].astype(str), format='%Y%m%d')
                    df["measure_year"] = df["measure_date"].dt.year
                    # Erstellung der Jahreszeiten zur weiteren Berechnung der Mins und Maxs
                    df["season"] = df["measure_date"].dt.month.apply(lambda month: 'Winter' if month in [12, 1, 2]
                                                                     else ('Spring' if month in [3, 4, 5]
                                                                           else ('Summer' if month in [6, 7, 8] 
                                                                                 else 'Autumn')))
                    #Umrechnung in Dezimalzahl
                    df["measure_value"] = df["measure_value"] / 10 
                    yearly_data = df.groupby(["station_id", "measure_year"]).agg(
                        maxyear=('measure_value', 'max'),
                        minyear=('measure_value', 'min'),
                        maxspring=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Spring'].max() if 'Spring' in df.loc[x.index, 'season'].values else None),
                        minspring=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Spring'].min() if 'Spring' in df.loc[x.index, 'season'].values else None),
                        maxsummer=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Summer'].max() if 'Summer' in df.loc[x.index, 'season'].values else None),
                        minsummer=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Summer'].min() if 'Summer' in df.loc[x.index, 'season'].values else None),
                        maxautumn=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Autumn'].max() if 'Autumn' in df.loc[x.index, 'season'].values else None),
                        minautumn=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Autumn'].min() if 'Autumn' in df.loc[x.index, 'season'].values else None),
                        maxwinter=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Winter'].max() if 'Winter' in df.loc[x.index, 'season'].values else None),
                        minwinter=('measure_value', lambda x: x[df.loc[x.index, 'season'] == 'Winter'].min() if 'Winter' in df.loc[x.index, 'season'].values else None)
                    ).reset_index()

                    data_to_insert = list(yearly_data.itertuples(index=False, name=None))
                    insert_query = """
                        INSERT INTO stationdata (station_id, measure_year, maxyear, minyear,maxspring,minspring, 
                        maxsummer, minsummer, maxautumn, minautumn, maxwinter, minwinter)
                        VALUES %s
                        ON CONFLICT (station_id, measure_year) 
                        DO NOTHING;
                    """
                    execute_values(cursor, insert_query, data_to_insert)      
                    cursor.connection.commit()
                print("Daten erfolgreich in die Datenbank eingefügt.")
            except Exception as ex:
                print(f"Fehler beim Verarbeiten der Datei: {ex}")


def download_file(year):
    baseURLbyYear = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_year/PLACEHOLDER.csv.gz"
    print(f'Herunterladen der {year} Datei.')
    baseURLbyYear = baseURLbyYear.replace("PLACEHOLDER",year)
    print(baseURLbyYear)
    response = requests.get(baseURLbyYear)
    print(response)
    response.raise_for_status()
    print("Herunterladen abgeschlossen")
    return io.BytesIO(response.content)

def fill_database():
    for year in range(2000,2024):
        with DatabaseConnection() as cursor:
            try:
                cursor.execute("SELECT EXISTS(SELECT 1 FROM stationdata where measure_year = %s)",[year])
                exists = cursor.fetchone()[0]
                if not exists:
                    print('''Datenbank Upload Vorgang Jahr {year}''')
                    insert_ghcn_by_year(str(year))
            except Exception as ex:
                print(f"Fehler beim Verarbeiten der Datei: {ex}")

#create_tables()
#fill_database()
#insert_ghcn_by_year("2024")
#get_ghcn_stations("./data/ghcnd-stations.csv")

# Benötigt, damit PostGIS aktiviert ist (nur einmalig, danach kommt sonst ein Fehler)
with DatabaseConnection() as cursor:
    cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis');")
    postgis_installed = cursor.fetchone()[0]

if not postgis_installed:
    print("PostGIS is not enabled. Enabling now...")
    with DatabaseConnection() as cursor:
        cursor.execute("CREATE EXTENSION postgis;")
        cursor.connection.commit()
    print("PostGIS has been enabled.")
else:
    print("PostGIS is already enabled.")

def get_stations_within_radius(lat_ref, lon_ref, radius, number):
    """
    Retrieves stations and their distance to a reference point within a given radius.

    Args:
        lat_ref (float): Latitude of the reference point.
        lon_ref (float): Longitude of the reference point.
        radius (int): Search radius in kilometers.
        number (int): Maximum number of stations.

    Returns:
        list: A list of tuples, where each tuple contains:
              - station_id (str)
              - station_name (str)
              - distance (float) in kilometers (rounded to 2 decimal places).
    """
    query = """
    SELECT station_id, CASE 
        WHEN latitude = %s AND longitude = %s 
        THEN station_name || ' (Zentrum)' 
        ELSE station_name 
    END AS station_name, ROUND(CAST(ST_Distance(station_point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000 AS NUMERIC), 2) AS distance, latitude, longitude
    FROM station
    WHERE ST_DWithin(station_point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s * 1000)
    ORDER BY distance
    LIMIT %s;
    """
    with DatabaseConnection() as cursor:
        cursor.execute(query, (lat_ref, lon_ref, lon_ref, lat_ref, lon_ref, lat_ref, radius, number))
        stations = cursor.fetchall()
        cursor.connection.commit()
    stations = [(station_id, station_name, float(distance), latitude, longitude) for station_id, station_name, distance, latitude, longitude in stations] # Convert distance from Decimal (needed for ROUND) to float.

    return stations

if __name__ == "__main__":
    app.run(debug=True)

