from flask import Flask, render_template, request,jsonify
import folium
import psycopg2

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

# Benötigt, damit PostGIS aktiviert ist (nur einmalig, danach kommt sonst ein Fehler)
cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis');")
postgis_installed = cursor.fetchone()[0]

if not postgis_installed:
    print("PostGIS is not enabled. Enabling now...")
    cursor.execute("CREATE EXTENSION postgis;")
    connection.commit()
    print("PostGIS has been enabled.")
else:
    print("PostGIS is already enabled.")

def get_stations_within_radius(lat_ref, lon_ref, radius):
    """
    Retrieves stations and their distance to a reference point within a given radius.

    Args:
        lat_ref (float): Latitude of the reference point.
        lon_ref (float): Longitude of the reference point.
        radius (int): Search radius in kilometers.

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
    ORDER BY distance;
    """

    cursor.execute(query, (lon_ref, lat_ref, lon_ref, lat_ref, radius))
    stations = cursor.fetchall()

    stations = [(station_id, station_name, float(distance)) for station_id, station_name, distance in stations] # Convert distance from Decimal (needed for ROUND) to float.

    return stations

if __name__ == "__main__":
    app.run(debug=True)