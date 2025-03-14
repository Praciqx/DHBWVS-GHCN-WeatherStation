#This file is only used to design the data filling
import pandas as pd
import gzip
from psycopg2.extras import execute_values
import io
import requests

def create_tables():
    cursor = get_db_connection()
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
        print(ex, flush=True)

def insert_ghcn_stations(csv_file_path, txt_file_path):
    cursor = get_db_connection()
    try:
        cursor.execute("SELECT EXISTS(SELECT 1 FROM station)")
        exists = cursor.fetchone()[0]
        if exists:
            print("Datenbank ist bereits befüllt.", flush=True)
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
        print(f"Fehler beim Einfügen: {ex}", flush=True)

def insert_ghcn_by_year(year):
    gzipped_file_this_yr = download_file(year)
    gzipped_file_last_yr = download_file(str(int(year)-1))
    list_winter = [1, 2]
    if gzipped_file_this_yr:
        cursor = get_db_connection()
        try:
            with gzip.open(gzipped_file_this_yr, "rt", encoding="utf-8") as f1:
                df_this_yr = prepare_dataframe(f1)
                df_only_this_yr = df_this_yr
                # Check if previous year is available
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
                # Creation of the seasons for further calculation of the Mins and Maxs
                df_this_yr["season"] = df_this_yr["measure_date"].dt.month.apply(lambda month: 'Winter' if month in list_winter
                                                                    else ('Spring' if month in [3, 4, 5]
                                                                        else ('Summer' if month in [6, 7, 8] 
                                                                                else ('Autumn' if month in [9, 10, 11] else 'Unknown'))))
                # Conversion to decimal
                df_this_yr["measure_value"] = df_this_yr["measure_value"] / 10 
                df_only_this_yr["measure_value"] = df_only_this_yr["measure_value"] / 10
                df_this_yr["measure_year"] = int(year)
                yearly_data = df_only_this_yr.groupby(["station_id", "measure_year"]).agg(
                    # Annual average for TMAX and TMIN
                    max_year=('measure_value', lambda x: round(x[df_only_this_yr.loc[x.index, 'measure_type'] == 'TMAX'].mean(), 1) if not x.empty else None),
                    min_year=('measure_value', lambda x: round(x[df_only_this_yr.loc[x.index, 'measure_type'] == 'TMIN'].mean(), 1) if not x.empty else None),
                )

                seasonal_data = df_this_yr.groupby(["station_id", "measure_year"]).agg(
                    # Seasonal averages for TMAX and TMIN
                    maxspring=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Spring') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Spring' in df_this_yr.loc[x.index, 'season'].values else None),
                    minspring=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Spring') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1)  if 'Spring' in df_this_yr.loc[x.index, 'season'].values else None),
                    maxsummer=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Summer') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Summer' in df_this_yr.loc[x.index, 'season'].values else None),
                    minsummer=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Summer') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Summer' in df_this_yr.loc[x.index, 'season'].values else None),
                    maxautumn=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Autumn') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Autumn' in df_this_yr.loc[x.index, 'season'].values else None),
                    minautumn=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Autumn') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Autumn' in df_this_yr.loc[x.index, 'season'].values else None),
                    maxwinter=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Winter') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMAX')].mean(), 1) if 'Winter' in df_this_yr.loc[x.index, 'season'].values else None),
                    minwinter=('measure_value', lambda x: round(x[(df_this_yr.loc[x.index, 'season'] == 'Winter') & (df_this_yr.loc[x.index, 'measure_type'] == 'TMIN')].mean(), 1) if 'Winter' in df_this_yr.loc[x.index, 'season'].values else None)
                )
                # Merging the results
                merged_yearly_data = pd.merge(yearly_data, seasonal_data, on=["station_id", "measure_year"], how="outer").reset_index()
                data_to_insert = list(merged_yearly_data.itertuples(index=False, name=None))
                insert_query = """
                    INSERT INTO stationdata (station_id, measure_year, maxyear, minyear,maxspring,minspring, 
                    maxsummer, minsummer, maxautumn, minautumn, maxwinter, minwinter)
                    VALUES %s
                    ON CONFLICT (station_id, measure_year) 
                    DO NOTHING;
                """
                execute_values(cursor, insert_query, data_to_insert)      
                cursor.connection.commit()
            print("Daten erfolgreich in die Datenbank eingefügt.", flush=True)
        except Exception as ex:
            print(f"Fehler beim Verarbeiten der Datei: {ex}", flush=True)

def download_file(year):
    baseURLbyYear = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_year/PLACEHOLDER.csv.gz"
    print(f'Herunterladen der {year} Datei.', flush=True)
    baseURLbyYear = baseURLbyYear.replace("PLACEHOLDER", year)
    try:
        response = requests.get(baseURLbyYear)
        response.raise_for_status() 
        print("Herunterladen abgeschlossen", flush=True)
        return io.BytesIO(response.content)  
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Herunterladen von {year}: {e}", flush=True)
        return None 

def prepare_dataframe(file):
    df = pd.read_csv(file, delimiter=",", header=None, usecols=[0, 1, 2, 3],
                        names=["station_id", "measure_date", "measure_type", "measure_value"])
    df = df[df["measure_type"].isin(["TMAX", "TMIN"])]
    df["measure_date"] = pd.to_datetime(df["measure_date"].astype(str), format='%Y%m%d')
    df["measure_year"] = df["measure_date"].dt.year    
    return df

def fill_database(start, end):
    for year in range(start, end):
        cursor = get_db_connection()
        try:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM stationdata where measure_year = %s)",[year])
            exists = cursor.fetchone()[0]
            if not exists:
                print('''Datenbank Upload Vorgang Jahr {year}''', flush=True)
                insert_ghcn_by_year(str(year))
        except Exception as ex:
            print(f"Fehler beim Verarbeiten der Datei: {ex}", flush=True)

def set_pg_extension():
    cursor = get_db_connection()
    cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis');")
    postgis_installed = cursor.fetchone()[0]

    if not postgis_installed:
        print("PostGIS is not enabled. Enabling now...", flush=True)
        cursor.execute("CREATE EXTENSION postgis;")
        cursor.connection.commit()
        print("PostGIS has been enabled.", flush=True)
    else:
        print("PostGIS is already enabled.", flush=True)

#set_pg_extension()

#create_tables()
#fill_database(1930, 1932)