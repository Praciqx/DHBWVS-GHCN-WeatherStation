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


def create_app(test_mode = None):
    app = Flask(__name__)
    @app.route('/')
    def index():
        """Renders the index page with the available year range."""
        return render_template("index.html",year_range = get_min_max_year())
    @app.route('/get_stations')
    def get_stations():
        """Returns the requested station data within a radius."""

        params = extract_request_params(
            ["lat", "lon", "radius", "stations", "datefrom", "dateto"], 
            {"lat": float, "lon": float, "radius": float,
                "stations": int, "datefrom": int, "dateto": int})

        selectedstations = get_stations_within_radius(params)
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
                "lat": params["lat"],
                "lon": params["lon"],
                "adress": "Zentrum",
                "radius": params["radius"] * 1000 
            },
            "stations": stations
        }
        return jsonify(stations_data)
    @app.route('/get_station_data')
    def get_station_data():
        """Gets the weather data for specific stationdid"""

        params = extract_request_params(["stationid", "datefrom", "dateto"], {
            "stationid": str, "datefrom": int, "dateto": int
            })

        df = fetch_station_data(params)
        if df is None or df.empty:
            return jsonify({
                "error": "Von der Station {} wurden im Jahresbereich von {} bis {} keine Daten gefunden.".format(
                    params["stationid"], params["datefrom"], params["dateto"]
                )
            }), 404
        data = format_chart_data(df)
        # structure for tables
        seasontabledata = json.loads(df.to_json(orient="records"))
        seasontemplate = render_template("seasontabledata.html",data=seasontabledata,stationid = params["stationid"])
        yearlytemplate = render_template("yearlytabledata.html",data=seasontabledata, stationid = params["stationid"])
        return jsonify(data=data, seasontemplate = seasontemplate,yearlytemplate = yearlytemplate)

    return app

def get_db_connection():
    conn = psycopg2.connect(
        dbname="dhbwvsghcn", user="admin", password="secretpassword", host="db", port=5432
    )
    cursor = conn.cursor()
    return cursor

def format_chart_data(df):
    """Formats the weather data from the DataFrame into a JSON structure for charts."""
    return {
        "years": df["year"].tolist(),
        "seasons": {
            "Jahr": {"min": df["min"].tolist(), "max": df["max"].tolist()},
            "Frühling": {"min": df["springmin"].tolist(), "max": df["springmax"].tolist()},
            "Sommer": {"min": df["summermin"].tolist(), "max": df["summermax"].tolist()},
            "Herbst": {"min": df["autumnmin"].tolist(), "max": df["autumnmax"].tolist()},
            "Winter": {"min": df["wintermin"].tolist(), "max": df["wintermax"].tolist()},
        }
    }

def get_min_max_year():
    """Returns the minimum and maximum available years for station data."""
    return {"maxYear":2024,"minYear":1750}


def extract_request_params(keys, types):
    """Extracts and converts request parameters based on provided keys and their expected types.
    
    Args:
        keys (list): List of parameter names to extract from the request.
        types (dict): Dictionary mapping keys to their expected data types.
    
    Returns:
        dict: Extracted parameters with converted data types.
    """
    return {key: request.args.get(key, type=types[key]) for key in keys}



def fetch_station_data(params):
    """Retrieves weather data from the database for specific params.
    
    Args:
        params (dict): Dictionary containing search parameters:
            - stationid (int): ID of the station.
            - datefrom (int): Start year for data filtering.
            - dateto (int): End year for data filtering.
    
    Returns:
        df: Dataframe of the filtered data.
    """
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
    cursor = get_db_connection()
    cursor.execute(query,(params["stationid"], params["datefrom"], params["dateto"]))
    fetcheddata = cursor.fetchall()

    df = pd.DataFrame(fetcheddata, columns=["year","max","min","springmax","springmin","summermax","summermin","autumnmax","autumnmin","wintermax","wintermin"])
    df = df.where(pd.notna(df), None)

    
    return df

def get_stations_within_radius(params):
    """
    Retrieves stations and their distance to a reference point within a given radius.

    Args:
        params (dict): Dictionary containing search parameters:
            - lat (float): Latitude of the reference point.
            - lon (float): Longitude of the reference point.
            - radius (float): Search radius in kilometers.
            - stations (int): Maximum number of stations to return.
            - datefrom (int): Start year for data filtering.
            - dateto (int): End year for data filtering.

    Returns:
        list: A list of tuples, where each tuple contains:
              - station_id (str)
              - station_name (str)
              - distance (float) in kilometers (rounded to 1 decimal place).
    """
    query = """
    SELECT station_id, CASE 
        WHEN latitude = %s AND longitude = %s 
        THEN station_name || ' (Zentrum)' 
        ELSE station_name 
    END AS station_name, ROUND(CAST(ST_Distance(station_point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000 AS NUMERIC), 1) AS distance, latitude, longitude
    FROM station
    WHERE ST_DWithin(station_point, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s * 1000) AND (measure_from <= %s and measure_to >= %s)
    ORDER BY distance
    LIMIT %s;
    """

    cursor = get_db_connection()
    cursor.execute(query, (params["lat"], params["lon"], params["lon"], params["lat"], params["lon"], params["lat"], params["radius"], params["datefrom"],params["dateto"],params["stations"]))
    stations = cursor.fetchall()

    stations = [(station_id, station_name, float(distance), latitude, longitude) for station_id, station_name, distance, latitude, longitude in stations] # Convert distance from Decimal (needed for ROUND) to float.

    return stations

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)

