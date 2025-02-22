#Diese Datei dient nur zur Gestaltung der Datenbefüllung

def get_ghcn_data_by_year(year):
    gzipped_file = download_file(year)
    if gzipped_file:
        with DatabaseConnection() as cursor:
            try:
                with gzip.open(gzipped_file, "rt", encoding="utf-8") as f:
                    df = pd.read_csv(f, delimiter=",", header=None, usecols=[0,1,2,3], names=["station_id", "measure_date", "measure_type", "measure_value"])
                    df = df[df["measure_type"].isin(["TMAX", "TMIN"])]

                    df = df

                    data_to_insert = list(df.itertuples(index=False, name=None))

                    insert_query = """
                        INSERT INTO stationdata (station_id, measure_date, measure_type, measure_value)
                        VALUES %s
                        ON CONFLICT (station_id, measure_date, measure_type) 
                        DO NOTHING
                    """

                    execute_values(cursor, insert_query, data_to_insert)

                cursor.connection.commit()
                print("Daten erfolgreich in die Datenbank eingefügt.")
            except Exception as ex:
                print(f"Fehler beim Verarbeiten der Datei: {ex}")