import pandas as pd
from geopy.geocoders import Nominatim
import time

geolocator = Nominatim(user_agent="geo_test")

df = pd.read_csv("entreprises_source.csv", encoding="utf-8")

print(f"Chargement du fichier source : entreprises_source.csv")
print("Début du processus de géocodage...")

for idx in range(len(df)):
    adresse = df.iloc[idx]["Adresse_Complete"]  # <- utilisation de .iloc pour accès par position
    try:
        location = geolocator.geocode(adresse)
        if location:
            print("SUCCÈS ({} / {}): {} -> ({}, {})".format(idx+1, len(df), adresse, location.latitude, location.longitude))
            df.at[idx, "Latitude"] = location.latitude
            df.at[idx, "Longitude"] = location.longitude
        else:
            print("ERREUR ({} / {}): {} - Adresse non trouvée".format(idx+1, len(df), adresse))
            df.at[idx, "Latitude"] = None
            df.at[idx, "Longitude"] = None
    except Exception as e:
        print("ERREUR ({} / {}): {} - {}".format(idx+1, len(df), adresse, e))
        df.at[idx, "Latitude"] = None
        df.at[idx, "Longitude"] = None

    time.sleep(1)

df.to_csv("entreprises_geocode.csv", index=False, encoding="utf-8")
print("Fichier géocodé créé : entreprises_geocode.csv")

