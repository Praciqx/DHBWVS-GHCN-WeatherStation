from flask import Flask, render_template, request,jsonify
import folium
import psycopg2
from geopy.distance import geodesic

app = Flask(__name__)

connection = psycopg2.connect(database="dhbwvsghcn", user="admin",password="secretpassword", host="db",port=5432)

cursor = connection.cursor()

# cursor.execute('select * from testtabelle;')

# record = cursor.fetchall()

# print(record)

@app.route('/')

def index():
    default_lat, default_lon = 48.0594, 8.4641
    default_radius = 5000
    karte_html = create_map(default_lat, default_lon, default_radius,0)
    return render_template("index.html", karte_html=karte_html)

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

@app.route('/get_stations')
def get_stations():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', type=float)
    stations = request.args.get('stations', type=int)

    return jsonify(map_html=create_map(lat,lon,radius,stations))

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