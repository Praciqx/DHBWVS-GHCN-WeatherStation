
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

$(function() {
    $('#weatherinputForm').on('submit', function(e){
        e.preventDefault();
        if (!this.checkValidity() || !validateYears()) {
            e.stopPropagation();
            e.preventDefault();
        }else{
            var lat = $("#latitude").val();
            var lon = $("#longitude").val();
            var radius = $("#rangeradiusinput").val();
            var station_count = $("#rangestationinput").val();
            let datefrom = $("#datefrom").val();
            let dateto = $("#dateto").val();
            $.ajax({
                    url: '/get_stations',
                    method: 'GET',
                    data: {
                        lat: lat,
                        lon: lon,
                        radius: radius,
                        stations: station_count,
                        datefrom:datefrom,
                        dateto:dateto
                    },
                    success: function(response) {
                        fillMapData(response)
                    },
                    error: function(xhr, status, error) {
                        console.error('Fehler beim Abrufen der Stationen:', status, error);
                    }
            });
        }
        $(this).addClass('was-validated');
    });

});
    
function getStationData(stationid){
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

function validateYears() {
    let dateFrom = parseInt($("#datefrom").val(), 10);
    let dateTo = parseInt($("#dateto").val(), 10);

    if (dateFrom > dateTo) {
        $(".datefrom-error").show();
        return false;
    } else {
        $(".datefrom-error").hide();
        return true;
    }
    
}
function clearMap() {
    if (markersLayer) {
        markersLayer.clearLayers();
        map.setView([48.0594, 8.4641], 13)
    }
}
$("#weatherinputForm input").on("input change",function(){
    clearChartData();
    clearTableData();
    clearMap();
})

function clearChartData(){
    chartinstance.data.labels = []; 
    chartinstance.data.datasets.forEach(dataset => {
        dataset.data = []; 
    });
    chartinstance.update();
}

function clearTableData(){
    $(".dataContainer").html("<div>Bitte wählen Sie eine Station aus!</div>");
}

function fillChartData(data){
    chartinstance.data = {
        labels: data.years,
        datasets: [
            { 
                label: 'Jahr Max Temp', 
                data: data.seasons.Jahr.max, 
                borderColor: 'rgba(112, 48, 160, 1)', 
                backgroundColor: 'rgba(112, 48, 160, 1)'
            },
            { 
                label: 'Jahr Min Temp', 
                data: data.seasons.Jahr.min, 
                borderColor: 'rgba(229, 158, 221, 1)', 
                backgroundColor: 'rgba(229, 158, 221, 1)', 
            },
            { 
                label: 'Frühling Max Temp', 
                data: data.seasons.Frühling.max, 
                borderColor: 'rgba(19, 80, 27, 1)', 
                backgroundColor: 'rgba(19, 80, 27, 1)', 
                hidden: true
            },
            { 
                label: 'Frühling Min Temp', 
                data: data.seasons.Frühling.min, 
                borderColor: 'rgba(180, 229, 162, 1)', 
                backgroundColor: 'rgba(180, 229, 162, 1)', 
                hidden:true
            },
            { 
                label: 'Sommer Max Temp', 
                data: data.seasons.Sommer.max, 
                borderColor: 'rgba(242, 5, 5, 1)', 
                backgroundColor: 'rgba(242, 5, 5, 1)', 
                hidden:true
            },
            { 
                label: 'Sommer Min Temp', 
                data: data.seasons.Sommer.min, 
                borderColor: 'rgba(242, 5, 5, 0.5)', 
                backgroundColor: 'rgba(242, 5, 5, 0.5)',  
                hidden:true
            },
            { 
                label: 'Herbst Max Temp', 
                data: data.seasons.Herbst.max, 
                borderColor: 'rgba(91, 58, 45, 1)', 
                backgroundColor: 'rgba(91, 58, 45, 1)', 
                hidden:true
            },
            { 
                label: 'Herbst Min Temp', 
                data: data.seasons.Herbst.min, 
                borderColor: 'rgba(182, 128, 95, 1)', 
                backgroundColor: 'rgba(182, 128, 95, 1)',
                hidden:true
            },
            { 
                label: 'Winter Max Temp', 
                data: data.seasons.Winter.max, 
                borderColor: '#1035EB', 
                backgroundColor: '#1035EB', 
                hidden:true
            },
            { 
                label: 'Winter Min Temp', 
                data: data.seasons.Winter.min, 
                borderColor: 'rgba(150, 229, 248, 1)', 
                backgroundColor: 'rgba(150, 229, 248, 1)',
                hidden:true
    
            }
        ]
    };
    chartinstance.options.plugins.legend.position = 'right';
    chartinstance.update();
}

function fillMapData(stationjson){
    markersLayer.clearLayers();
    var center = stationjson.center;
    let selectedStationIsCenter = false;
    let circle = L.circle([center.lat, center.lon], {
        color: 'red',
        fillColor: 'blue',
        fillOpacity: 0.4,
        radius: center.radius,
        weight:0
    }).addTo(markersLayer);
    map.fitBounds(circle.getBounds());
    stationjson.stations.forEach(function(station) {
        var lat = station.lat;
        var lon = station.lon;
        var address = station.address;
        var id = station.id;
        var km = station.km;
        let marker = L.marker([lat, lon]).addTo(markersLayer);
        if(center.lat == lat && center.lon == lon){
            selectedStationIsCenter = true;
            marker._icon.style.filter = "hue-rotate(120deg)";
        }
        marker.bindPopup(`<span><b>Station: </b>${id}</br><b>Ort:</b> ${address}</br><b>Entfernung:</b> ${km}</br><b>Längengrad:</b> ${lat}</br><b>Breitengrad:</b> ${lon}</span><div class="pt-2"><button id='${id}' style="--bs-btn-padding-y: .2rem; --bs-btn-padding-x: .4rem; --bs-btn-font-size: .7rem;" class='btn btn-sm btn-success' onclick='getStationData("${id}")'>Auswählen</button></div>`);
    });
    if(!selectedStationIsCenter){
        let marker = L.marker([center.lat,center.lon]).addTo(markersLayer);
        marker.bindPopup(center.adress);
        marker._icon.style.filter = "hue-rotate(120deg)"
    }
}

$(".latlon").on("keyup",function(){
    let value = this.value;
    value = value.replace(/[^0-9,.-]/g, "");
    value = value.replace(/,/g, ".");
    if (value.includes("-")) {
        value = "-" + value.replace(/-/g, "");
    }
    // keine weitere Punkte erlauben
    let parts = value.split(".");
    if (parts.length > 2) {
        value = parts[0] + "." + parts.slice(1).join("");
    }
    this.value = value;
})
