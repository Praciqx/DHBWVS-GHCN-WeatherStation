import pytest
import json
import app
import pandas as pd
from app import create_app


@pytest.fixture()
def test_app():
    app = create_app()
    app.config.update({
        "TESTING":True
    })
    yield app

@pytest.fixture()
def client(test_app):
    return test_app.test_client()

def test_get_stations_within_radius(client,monkeypatch):
    def mock_get_stations_within_radius(params):
        return[
             ("ABC13333337", "Testort", 0.0, 11, 6) 
        ]
    
    monkeypatch.setattr("app.get_stations_within_radius",mock_get_stations_within_radius)

    response = client.get("/get_stations?lat=10.0&lon=5.0&radius=10&stations=5&datefrom=2000&dateto=2020")

    assert response.status_code == 200
    data = response.get_json()
    print(data)
    assert "center" in data
    assert "stations" in data
    assert len(data["stations"]) > 0
    assert data["stations"][0]["id"] == "ABC13333337"

def test_get_station_data_valid(client, monkeypatch):
    def mock_fetch_station_data(params):
        data = {
            "year": [2000, 2020],
            "max": [20, 27],
            "min": [0, 5],
            "springmax": [None, 17],
            "springmin": [3, 7],
            "summermax": [20, 27],
            "summermin": [19, 23],
            "autumnmax": [13, 15],
            "autumnmin": [8, 9],
            "wintermax": [3, 4],
            "wintermin": [0, 5],
        }
        return pd.DataFrame(data) 

    monkeypatch.setattr(app,"fetch_station_data", mock_fetch_station_data)

    response = client.get("/get_station_data?stationid=123&datefrom=2000&dateto=2005")
    assert response.status_code == 200
    data = json.loads(response.data)

    assert "data" in data
    assert "seasons" in data["data"]
    assert data["data"]["years"][1] == 2020
    assert data["data"]["years"][0] == 2000
    assert max(data["data"]["seasons"]["Jahr"]["max"]) == max(data["data"]["seasons"]["Sommer"]["max"])


def test_get_station_data_invalid(client, monkeypatch):
    def mock_fetch_station_data(params):
        return None

    monkeypatch.setattr(app,"fetch_station_data", mock_fetch_station_data)
    response = client.get("/get_station_data?stationid=ABC1333337&datefrom=2000&dateto=2024")
    assert response.status_code == 404
    data = json.loads(response.data)

    assert "error" in data
    assert data["error"] == "Von der Station ABC1333337 wurden im Jahresbereich von 2000 bis 2024 keine Daten gefunden."
