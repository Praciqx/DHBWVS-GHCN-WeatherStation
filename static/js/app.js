import Utils from "./utils.js"

let stationChart;
let chartinstance;
stationChart = $("#stationChart");
chartinstance = new Chart(stationChart, {
    type: 'line',
    options: {
        plugins:{
            tooltip:{
                callbacks:{
                    label:function(element){
                        let value = parseFloat(element.raw);
                        if (!isNaN(value)) {
                            return value.toFixed(1).replace(".", ",") + "°C"; 
                        }
                        return element.raw
                    }
                }
            },
            legend:{
                labels:{
                    usePointStyle:true,
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

const map = L.map('stationmap').setView([48.0594, 8.4641], 13);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
var markersLayer = L.layerGroup().addTo(map)

$(".latlon").on("keyup",function(){
    this.value = Utils.sanitizeLatLonInput(this.value); 
})

window.fillMapData = function(stationjson) {
    markersLayer.clearLayers();
    var center = stationjson.center;
    let selectedStationIsCenter = false;

    let circle = L.circle([center.lat, center.lon], {
        color: 'red',
        fillColor: 'blue',
        fillOpacity: 0.4,
        radius: center.radius,
        weight: 0
    }).addTo(markersLayer);
    map.fitBounds(circle.getBounds());

    stationjson.stations.forEach(function(station) {
        var lat = station.lat;
        var lon = station.lon;
        var address = station.address;
        var id = station.id;
        var km = station.km;
        let isCenter = center.lat == lat && center.lon == lon;
        let marker = L.marker([lat, lon]).addTo(markersLayer);

        if (isCenter) {
            selectedStationIsCenter = true;
            marker._icon.style.filter = "hue-rotate(120deg)";
        }
        marker.bindPopup(`
            <span>
                <b>Station: </b>${id}</br>
                <b>Ort:</b> ${address}</br>
                <b>Entfernung:</b> ${km} km</br>
                <b>Längengrad:</b> ${lat}</br>
                <b>Breitengrad:</b> ${lon}
            </span>
            <div class="pt-2">
                <button id='${id}' 
                    style="--bs-btn-padding-y: .2rem; --bs-btn-padding-x: .4rem; --bs-btn-font-size: .7rem;" 
                    class='btn btn-sm btn-success' 
                    onclick='getStationData("${id}")'>Auswählen</button>
            </div>
        `);
    });

    if (!selectedStationIsCenter) {
        let marker = L.marker([center.lat, center.lon]).addTo(markersLayer);
        marker.bindPopup(`<b>Zentrum:</b> ${center.address}`);
        marker._icon.style.filter = "hue-rotate(120deg)";
    }
}


function fillChartData(data){
    const chartData = Utils.prepareChartData(data);
    chartinstance.data = chartData;
    chartinstance.options.plugins.legend.position = "right";
    chartinstance.update();
}

function clearTableData(){
$(".dataContainer").html("<div>Bitte wählen Sie eine Station aus!</div>");
}
window.getStationData = function(stationid){
    $("#stationContent").block();
    clearChartData();
    clearTableData();
    let datefrom = $("#datefrom").val();
    let dateto = $("#dateto").val();
    $.ajax({
            url: '/get_station_data',
            method: 'GET',
            data: {
                stationid:stationid,
                datefrom:datefrom,
                dateto:dateto
            },
            success: function(response) {
                fillChartData(response.data)
                $("#seasonData").html(response.seasontemplate);
                $("#yearlyData").html(response.yearlytemplate);
            },
            complete: function(){
                $("#stationContent").unblock();
            },
            error: function(xhr, status, error) {
                swal("Fehler", xhr.responseJSON.error, "error");
            }
    });
}

$("#weatherinputForm input").on("input change",function(){
    clearChartData();
    clearTableData();
    defaultMap();
})

window.validateYears = function(dateFrom, dateTo) {
    let isValid = Utils.isValidYearRange(dateFrom, dateTo);
    if (isValid) {
        $(".datefrom-error").hide();
    } else {
        $(".datefrom-error").show();
    }
    return isValid;
}

function defaultMap() {
    if (markersLayer) {
        markersLayer.clearLayers();
        map.setView([48.0594, 8.4641], 13)
    }
}
function clearChartData(){
    chartinstance.data.labels = []; 
    chartinstance.data.datasets.forEach(dataset => {
        dataset.data = []; 
    });
    chartinstance.update();
}
