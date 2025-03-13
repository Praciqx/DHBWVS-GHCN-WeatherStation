
export function isValidYearRange(dateFrom, dateTo) {
    if (typeof dateFrom !== "number" || typeof dateTo !== "number") {
        throw new Error("Ungültige Eingaben: Beide Werte müssen Zahlen sein.");
    }
    return dateFrom <= dateTo;
}

export function prepareChartData(data) {
    if (!data || !data.years || !data.seasons) {
        throw new Error("Ungültige Datenstruktur für das Chart");
    }
    return {
        labels: data.years,
        datasets: [
            { label: "Jahr Max Temp", data: data.seasons.Jahr.max, borderColor: "rgba(112, 48, 160, 1)", backgroundColor: "rgba(112, 48, 160, 1)" },
            { label: "Jahr Min Temp", data: data.seasons.Jahr.min, borderColor: "rgba(229, 158, 221, 1)", backgroundColor: "rgba(229, 158, 221, 1)" },
            { label: "Frühling Max Temp", data: data.seasons.Frühling.max, borderColor: "rgba(19, 80, 27, 1)", backgroundColor: "rgba(19, 80, 27, 1)", hidden: true },
            { label: "Frühling Min Temp", data: data.seasons.Frühling.min, borderColor: "rgba(180, 229, 162, 1)", backgroundColor: "rgba(180, 229, 162, 1)", hidden: true },
            { label: "Sommer Max Temp", data: data.seasons.Sommer.max, borderColor: "rgba(242, 5, 5, 1)", backgroundColor: "rgba(242, 5, 5, 1)", hidden: true },
            { label: "Sommer Min Temp", data: data.seasons.Sommer.min, borderColor: "rgba(242, 5, 5, 0.5)", backgroundColor: "rgba(242, 5, 5, 0.5)", hidden: true },
            { label: "Herbst Max Temp", data: data.seasons.Herbst.max, borderColor: "rgba(91, 58, 45, 1)", backgroundColor: "rgba(91, 58, 45, 1)", hidden: true },
            { label: "Herbst Min Temp", data: data.seasons.Herbst.min, borderColor: "rgba(182, 128, 95, 1)", backgroundColor: "rgba(182, 128, 95, 1)", hidden: true },
            { label: "Winter Max Temp", data: data.seasons.Winter.max, borderColor: "#1035EB", backgroundColor: "#1035EB", hidden: true },
            { label: "Winter Min Temp", data: data.seasons.Winter.min, borderColor: "rgba(150, 229, 248, 1)", backgroundColor: "rgba(150, 229, 248, 1)", hidden: true }
        ]
    };
}

export function generateMapData(stationjson) {
    if (!stationjson || !stationjson.center || !Array.isArray(stationjson.stations)) {
        throw new Error("Ungültige stationjson-Daten");
    }
    let selectedStationIsCenter = false;
    let center = {
        lat: stationjson.center.lat,
        lon: stationjson.center.lon,
        radius: stationjson.center.radius,
        address: stationjson.center.address
    };
    let markers = stationjson.stations.map(station => ({
        lat: station.lat,
        lon: station.lon,
        address: station.address,
        id: station.id,
        km: station.km,
        isCenter: station.lat == center.lat && station.lon == center.lon
    }));
    selectedStationIsCenter = markers.some(marker => marker.isCenter);

    return { center, markers, selectedStationIsCenter };
}


export function sanitizeLatLonInput(value) {
    if (typeof value !== "string") return "";

    value = value.replace(/[^0-9,.-]/g, "");  
    value = value.replace(/,/g, "."); 

    if (value.includes("-")) {
        value = "-" + value.replace(/-/g, "");
    }
    let parts = value.split(".");
    if (parts.length > 2) {
        value = parts[0] + "." + parts.slice(1).join("");
    }
    return value;
}

const Utils = {sanitizeLatLonInput,isValidYearRange, prepareChartData,generateMapData}
export default Utils;