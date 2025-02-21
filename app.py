from flask import Flask, render_template, request,jsonify,render_template_string
import folium
import psycopg2
from folium.map import Marker
from jinja2 import Template

app = Flask(__name__)

connection = psycopg2.connect(database="dhbwvsghcn", user="admin",password="secretpassword", host="db",port=5432)

cursor = connection.cursor()

# cursor.execute('select * from testtabelle;')

# record = cursor.fetchall()

# print(record)

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

def is_within_radius(lat_origin, lon_origin, lat_asked, lon_asked, radius):
    """
    Checks whether a given point is within a specified radius from an origin point.

    Calculates the geodesic distance between the origin (lat_origin, lon_origin) and 
    the target point (lat_asked, lon_asked) in kilometers and compares it to the given radius. The Vincenty formula is used for that.

    Parameters:
    lat_origin (float): Latitude of the origin point.
    lon_origin (float): Longitude of the origin point.
    lat_asked (float): Latitude of the point to check.
    lon_asked (float): Longitude of the point to check.
    radius (float): The maximum allowed radius in kilometers.

    Returns:
    bool: True if the point is within the radius, otherwise False.
    """
    distance = geodesic((lat_origin, lon_origin), (lat_asked, lon_asked)).km
    return distance <= radius

if __name__ == "__main__":
    app.run(debug=True)