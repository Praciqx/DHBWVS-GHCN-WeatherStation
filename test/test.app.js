import { expect } from "chai";
import { 
    isValidYearRange, 
    prepareChartData, 
    generateMapData, 
    sanitizeLatLonInput 
} from "../static/js/utils.js";

describe("logic function tests", () => {

    describe("isValidYearRange()", () => {
        it("is true if from is higher than to", () => {
            expect(isValidYearRange(2000, 2020)).to.be.true;
            expect(isValidYearRange(2020, 2020)).to.be.true;
        });

        it("is false if from is higher than to", () => {
            expect(isValidYearRange(2025, 2020)).to.be.false;
        });

        it("should fail if something else than numbers are given", () => {
            expect(() => isValidYearRange("abc", 2020)).to.throw("Ungültige Eingaben: Beide Werte müssen Zahlen sein.");
            expect(() => isValidYearRange(null, 2020)).to.throw("Ungültige Eingaben: Beide Werte müssen Zahlen sein.");
        });
    });

    describe("Prepare Chart Data Check", () => {
        it("should generate the chart data correctly", () => {
            const input = {
                years: [2000, 2001, 2002],
                seasons: {
                    Jahr: { max: [10, 12, 15], min: [0, 2, 3] },
                    Frühling: { max: [5, 8, 10], min: [0, 1, 2] },
                    Sommer: { max: [20, 22, 25], min: [10, 12, 15] },
                    Herbst: { max: [10, 12, 15], min: [5, 6, 7] },
                    Winter: { max: [2, 3, 4], min: [-5, -3, -2] }
                }
            };

            const result = prepareChartData(input);

            expect(result.labels).to.deep.equal([2000, 2001, 2002]);
            expect(result.datasets).to.have.lengthOf(10);
            expect(result.datasets[0].label).to.equal("Jahr Max Temp");
            expect(result.datasets[0].data).to.deep.equal([10, 12, 15]);
        });

        it("should fail if chart data has incorrect format", () => {
            const wrongdata = {
                seasons: { Jahr: { max: [10, 12, 15], min: [0, 2, 3] } }
            };
            expect(() => prepareChartData(null)).to.throw("Ungültige Datenstruktur für das Chart");
            expect(() => prepareChartData({})).to.throw("Ungültige Datenstruktur für das Chart");
            expect(() => prepareChartData(wrongdata)).to.throw("Ungültige Datenstruktur für das Chart");
        });
    });

    describe("Prepare of the map data", () => {
        it("should generate the correct station data and add markers", () => {
            const input = {
                center: { lat: 48.0, lon: 8.0, radius: 1000, address: "Zentrum" },
                stations: [
                    { lat: 48.1, lon: 8.1, address: "Station 1", id: "S1", km: 5 },
                    { lat: 48.0, lon: 8.0, address: "Station 2", id: "S2", km: 0 }
                ]
            };

            const result = generateMapData(input);

            expect(result.center.lat).to.equal(48.0);
            expect(result.center.lon).to.equal(8.0);
            expect(result.markers).to.have.lengthOf(2);
            expect(result.markers[1].isCenter).to.be.true;
        });

        it("should fail if the json is stationjson is wrong", () => {
            const wrongdata = {
                center: { lat: 48.0, lon: 8.0, radius: 1000, address: "Zentrum" }
            };
            expect(() => generateMapData(wrongdata)).to.throw("Ungültige stationjson-Daten");
            expect(() => generateMapData(null)).to.throw("Ungültige stationjson-Daten");
            expect(() => generateMapData({})).to.throw("Ungültige stationjson-Daten");
        });
    });
    describe("Sanitize of the LAT and LON Inputs", () => {
        it("should eleminate wrong input values", () => {
            expect(sanitizeLatLonInput("48.1234 G")).to.equal("48.1234");
            expect(sanitizeLatLonInput("8,5678")).to.equal("8.5678");
            expect(sanitizeLatLonInput("-48.123,45")).to.equal("-48.12345");
        });

        it("should return a string if invalid input is given", () => {
            expect(sanitizeLatLonInput(null)).to.equal("");
            expect(sanitizeLatLonInput(12345)).to.equal("");
        });

        it("should only accept one point in the value", () => {
            expect(sanitizeLatLonInput("48.12.")).to.equal("48.12");
        });
    });

});
