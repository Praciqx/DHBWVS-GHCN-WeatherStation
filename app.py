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
    stations = request.args.get('stations', type=int)
    stations_data = {
        "center":{
                "lat":lat,
                "lon":lon,
                "adress":"Zentrum",
                "radius":radius*1000
            }
        ,
        "stations": [
            {
                "id": "A884884",
                "lat": lat + 0.01,
                "lon": lon + 0.01,
                "address": "Freudenstadt",
                "km": "5km"
            },
            {
                "id": "DADM84848",
                "lat": lat - 0.01,
                "lon": lon - 0.01,
                "address": "Villingendorf",
                "km": "8km"
            },
            {
                "id": "SDJHGFHf38",
                "lat": lat + 0.02,
                "lon": lon + 0.02,
                "address": "Schwenningen",
                "km": "10km"
            }
        ]
    }
    return jsonify(stations_data)

@app.route('/get_station_data')
def get_station_data():
    stationid = request.args.get('stationid', type=str)
    data = {
        "years": [2020, 2021, 2022, 2023],
        "seasons": {
            "Sommer": {"min": [20, 22, 23, 24], "max": [30, 32, 33, 34]},
            "Frühling": {"min": [10, 12, 13, 14], "max": [20, 22, 23, 24]},
            "Herbst": {"min": [5, 6, 7, 8], "max": [15, 16, 17, 18]},
            "Winter": {"min": [-5, -4, -3, -2], "max": [5, 6, 7, 8]}
        }
    }
    seasontabledata = [
        {"year":2024,"summermax":10,"summermin":5,"wintermax":2,"wintermin":-2,"springmax":4,"springmin":7,"autumnmin":3,"autumnmax":20,"min":4,"max":30}
    ]
    seasontemplate = render_template("seasontabledata.html",data=seasontabledata)
    yearlytemplate = render_template("yearlytabledata.html",data=seasontabledata)
    return jsonify(data=data, seasontemplate = seasontemplate,yearlytemplate =yearlytemplate)

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
                            INSERT INTO station (station_id, latitude, longitude, station_name, station_point)
                            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s)::geography, 4326))
                            ON CONFLICT (station_id) DO NOTHING;
                        ''', (station_id, latitude, longitude, station_name, latitude,longitude))
            cursor.connection.commit()
        except Exception as ex:
            print(ex)

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
    for year in range(1750,2024):
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
    SELECT station_id, station_name, ROUND(CAST(ST_Distance(point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000 AS NUMERIC), 2) AS distance
    FROM stations
    WHERE ST_DWithin(point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s * 1000)
    ORDER BY distance
    LIMIT %s;
    """
    with DatabaseConnection() as cursor:
        cursor.execute(query, (lon_ref, lat_ref, lon_ref, lat_ref, radius, number))
        stations = cursor.fetchall()

    stations = [(station_id, station_name, float(distance)) for station_id, station_name, distance in stations] # Convert distance from Decimal (needed for ROUND) to float.

    return stations

if __name__ == "__main__":
    app.run(debug=True)

