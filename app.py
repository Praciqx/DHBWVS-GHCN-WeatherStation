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
import csv

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
    datefrom = request.args.get('datefrom', type=int)
    dateto = request.args.get('dateto', type=int)

    
    selectedstations = get_stations_within_radius(lat, lon, radius, station_count,datefrom,dateto)
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
        SELECT measure_year, maxyear, minyear, 
            CASE WHEN latitude >= 0 THEN maxspring ELSE maxautumn END AS max_spring,
            CASE WHEN latitude >= 0 THEN minspring ELSE minautumn END AS min_spring,
            CASE WHEN latitude >= 0 THEN maxsummer ELSE maxwinter END AS max_summer,
            CASE WHEN latitude >= 0 THEN minsummer ELSE minwinter END AS min_summer,
            CASE WHEN latitude >= 0 THEN maxautumn ELSE maxspring END AS max_autumn,
            CASE WHEN latitude >= 0 THEN minautumn ELSE minspring END AS min_autumn,
            CASE WHEN latitude >= 0 THEN maxwinter ELSE maxsummer END AS max_winter,
            CASE WHEN latitude >= 0 THEN minwinter ELSE minsummer END AS min_winter
        FROM stationdata 
        JOIN station ON stationdata.station_id = station.station_id
        WHERE stationdata.station_id = %s AND measure_year BETWEEN %s AND %s and measure_year between measure_from and measure_to;
    """

    with DatabaseConnection() as cursor:
        cursor.execute(query,(stationid, datefrom, dateto))
        fetcheddata = cursor.fetchall()
        cursor.connection.commit()
        
    if not fetcheddata:
        return jsonify({"error":f"Von der Station {stationid} wurden im Jahresbereich von {datefrom} bis {dateto} keine Daten gefunden."}),404

    df = pd.DataFrame(fetcheddata, columns=["year","max","min","springmax","springmin","summermax","summermin","autumnmax","autumnmin","wintermax","wintermin"])
    df = df.where(pd.notna(df), 0)
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

### Anfang Kopie in data.py

def create_tables():
    with DatabaseConnection() as cursor:
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS "station" (
                "station_id" character(25) PRIMARY KEY,
                "latitude" NUMERIC(7,4) NOT NULL,
                "longitude" NUMERIC(7,4) NOT NULL,
                "station_name" character(100) NOT NULL,
                "measure_from" smallint NOT NULL,
                "measure_to" smallint NOT NULL,
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



#müsste das nicht insert heißen?
def get_ghcn_stations(csv_file_path, txt_file_path):
    with DatabaseConnection() as cursor:
        try:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM station)")
            exists = cursor.fetchone()[0]
            if exists:
                print("Datenbank ist bereits befüllt.")
                return  

            #only valid years stations from inventory
            df_inventory = pd.read_csv(txt_file_path, sep=r'\s+', header=None, 
                names=["station_id", "latitude","longitude","measure_type","measure_from_year","measure_to_year"])
            df_inventory = df_inventory[df_inventory["measure_type"].isin(["TMIN", "TMAX"])].copy()  

            df_pivot = df_inventory.pivot(index=["station_id", "latitude", "longitude"], 
                                          columns="measure_type", 
                                          values=["measure_from_year", "measure_to_year"])
            df_pivot.columns = ["measure_from_TMAX", "measure_from_TMIN", "measure_to_TMAX", "measure_to_TMIN"]
            df_pivot = df_pivot.reset_index()

            df_pivot = df_pivot.dropna()
            df_pivot["measure_from"] = df_pivot[["measure_from_TMAX", "measure_from_TMIN"]].max(axis=1)
            df_pivot["measure_to"] = df_pivot[["measure_to_TMAX", "measure_to_TMIN"]].min(axis=1)
            df_inventory = df_pivot[["station_id", "latitude", "longitude", "measure_from", "measure_to"]]
            df_inventory.loc[:, "measure_from"] = df_inventory["measure_from"].astype(int)
            df_inventory.loc[:, "measure_to"] = df_inventory["measure_to"].astype(int)

            #read csv to get the names of the stations
            df_stations = pd.read_csv(csv_file_path, header=None, usecols=[0, 4, 5], names=["station_id", "station_state","station_name"])
            #only get the station names that are in the inventory
            df_stations["station_with_state"] = df_stations["station_state"].fillna("") + " " + df_stations["station_name"]
            station_name_dict = df_stations.set_index("station_id")["station_with_state"].to_dict()

            df_inventory.loc[:, "station_name"] = df_inventory["station_id"].map(station_name_dict)
            df_inventory.loc[:, "station_name"] = df_inventory["station_name"].str.strip()

            insert_query = """
                INSERT INTO station (station_id, latitude, longitude, station_name, measure_from, measure_to, station_point)
                VALUES (%s, %s, %s, %s,%s,%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ON CONFLICT (station_id) DO NOTHING;
            """
            for _, row in df_inventory.iterrows():
                cursor.execute(insert_query, (row["station_id"], row["latitude"], row["longitude"], row["station_name"], row["measure_from"], row["measure_to"], row["longitude"], row["latitude"]))

            cursor.connection.commit()
        except Exception as ex:
            print(f"Fehler beim Einfügen: {ex}")


def insert_ghcn_by_year(year):
    gzipped_file_this_yr = download_file(year)
    gzipped_file_last_yr = download_file(str(int(year)-1))
    list_winter = [1, 2]
    if gzipped_file_this_yr:
        with DatabaseConnection() as cursor:
            try:
                with gzip.open(gzipped_file_this_yr, "rt", encoding="utf-8") as f1:
                    df_this_yr = prepare_dataframe(f1)
                    #Prüfen ob Vorjahr vorhanden
                    if gzipped_file_last_yr:
                        list_winter.append(12)
                        with gzip.open(gzipped_file_last_yr, "rt", encoding="utf-8") as f2:
                            df_last_yr = prepare_dataframe(f2)
                            december_last_yr = df_last_yr[df_last_yr["measure_date"].dt.month == 12]
                            # Delete values of december of the dataframe of this year
                            df_this_yr = df_this_yr[~(df_this_yr["measure_date"].dt.month == 12)]
                            # Insert values of december last year to the dataframe of this year
                            df_this_yr = pd.concat([df_this_yr, december_last_yr]).sort_values(by=['station_id', 'measure_type', 'measure_date'])
                            df_this_yr.reset_index(drop=True, inplace=True)
                    # Erstellung der Jahreszeiten zur weiteren Berechnung der Mins und Maxs
                    df_this_yr["season"] = df_this_yr["measure_date"].dt.month.apply(lambda month: 'Winter' if month in list_winter
                                                                     else ('Spring' if month in [3, 4, 5]
                                                                           else ('Summer' if month in [6, 7, 8] 
                                                                                 else ('Autumn' if month in [9, 10, 11] else 'Unknown'))))
                    #Umrechnung in Dezimalzahl
                    df_this_yr["measure_value"] = df_this_yr["measure_value"] / 10 
                    df_this_yr["measure_year"] = year
                    yearly_data = df_this_yr.groupby(["station_id", "measure_year"]).agg(
                        # Annual average for TMAX and TMIN
                        max_year=('measure_value', lambda x: round(x[df_this_yr.loc[x.index, 'measure_type'] == 'TMAX'].mean(), 1)),
                        min_year=('measure_value', lambda x: round(x[df_this_yr.loc[x.index, 'measure_type'] == 'TMIN'].mean(), 1)),
                        # Seasonal averages for TMAX and TMIN
                        maxspring=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Spring') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Spring' in df_this_yr.loc[x.index, 'season'].values else None),
                        minspring=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Spring') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1)  if 'Spring' in df_this_yr.loc[x.index, 'season'].values else None),
                        maxsummer=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Summer') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Summer' in df_this_yr.loc[x.index, 'season'].values else None),
                        minsummer=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Summer') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Summer' in df_this_yr.loc[x.index, 'season'].values else None),
                        maxautumn=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Autumn') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Autumn' in df_this_yr.loc[x.index, 'season'].values else None),
                        minautumn=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Autumn') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Autumn' in df_this_yr.loc[x.index, 'season'].values else None),
                        maxwinter=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Winter') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Winter' in df_this_yr.loc[x.index, 'season'].values else None),
                        minwinter=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Winter') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Winter' in df_this_yr.loc[x.index, 'season'].values else None)
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

def prepare_dataframe(file):
    df = pd.read_csv(file, delimiter=",", header=None, usecols=[0, 1, 2, 3],
                        names=["station_id", "measure_date", "measure_type", "measure_value"])
    df = df[df["measure_type"].isin(["TMAX", "TMIN"])]
    df["measure_date"] = pd.to_datetime(df["measure_date"].astype(str), format='%Y%m%d')
    df["measure_year"] = df["measure_date"].dt.year    
    return df


def fill_database(start, end):
    #TODO: prüfen warum Range nicht funktioniert hat
    for year in range(start, end):
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
#insert_ghcn_by_year("2024")
#get_ghcn_stations("./data/ghcnd-stations.csv","./data/ghcnd-inventory.txt")
#fill_database(1750, 2024)

#### Ende Kopie in data.py


# Benötigt, damit PostGIS aktiviert ist (nur einmalig, danach kommt sonst ein Fehler)
# Kann das in die Funktion?
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

def get_stations_within_radius(lat_ref, lon_ref, radius, number,year_from,year_to):
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
    WHERE ST_DWithin(station_point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s * 1000) AND measure_from between %s and %s
    ORDER BY distance
    LIMIT %s;
    """
    with DatabaseConnection() as cursor:
        cursor.execute(query, (lat_ref, lon_ref, lon_ref, lat_ref, lon_ref, lat_ref, radius, number,year_from,year_to))
        stations = cursor.fetchall()
        cursor.connection.commit()
    stations = [(station_id, station_name, float(distance), latitude, longitude) for station_id, station_name, distance, latitude, longitude in stations] # Convert distance from Decimal (needed for ROUND) to float.

    return stations

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

