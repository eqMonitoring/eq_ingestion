"""
Script pour récupérer et afficher les données de tremblements de terre
depuis l'API USGS Earthquake Hazards Program.

Documentation: https://earthquake.usgs.gov/fdsnws/event/1/
"""
import csv
import json
from datetime import datetime
import pandas as pd
import requests

# URL de l'API USGS pour les tremblements de terre
USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def get_earthquakes(start_date, end_date, min_magnitude=4.5):
    """
    Récupère les données de tremblements de terre depuis l'API USGS.
    
    Args:
        start_date: Date de début au format "YYYY-MM-DD"
        end_date: Date de fin au format "YYYY-MM-DD"
        min_magnitude: Magnitude minimale (défaut: 4.5)
    
    Returns:
        dict: Données GeoJSON des tremblements de terre
    """
    params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": min_magnitude,
        "orderby": "time"  # Trier par date
    }
    
    try:
        response = requests.get(USGS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération des données: {e}")
        return None


def format_earthquake_data(feature):
    """
    Formate les données d'un tremblement de terre pour l'affichage.
    
    Args:
        feature: Feature GeoJSON d'un tremblement de terre
    
    Returns:
        dict: Données formatées
    """
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [])
    
    # Convertir le timestamp Unix en date lisible
    timestamp = props.get("time", 0) / 1000  # USGS utilise des millisecondes
    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "magnitude": props.get("mag"),
        "lieu": props.get("place", "Lieu inconnu"),
        "date": date_str,
        "longitude": coords[0] if len(coords) > 0 else None,
        "latitude": coords[1] if len(coords) > 1 else None,
        "profondeur": coords[2] if len(coords) > 2 else None,
        "type": props.get("type", "N/A"),
        "tsunami": props.get("tsunami", 0),
        "url": props.get("url", "")
    }


def extract_all_earthquake_data(feature):
    """
    Extrait toutes les données disponibles d'un tremblement de terre.
    
    Args:
        feature: Feature GeoJSON d'un tremblement de terre
    
    Returns:
        dict: Toutes les données disponibles formatées pour CSV
    """
    props = feature.get("properties", {})
    coords = feature.get("geometry", {}).get("coordinates", [])
    feature_id = feature.get("id", "")
    
    # Convertir les timestamps Unix en dates lisibles
    time_ms = props.get("time", 0)
    updated_ms = props.get("updated", 0)
    
    time_str = ""
    updated_str = ""
    
    if time_ms:
        time_str = datetime.fromtimestamp(time_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    
    if updated_ms:
        updated_str = datetime.fromtimestamp(updated_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    
    # Extraire toutes les propriétés disponibles
    data = {
        # Identifiants
        "id": feature_id,
        "code": props.get("code", ""),
        "ids": props.get("ids", ""),
        "sources": props.get("sources", ""),
        
        # Dates et temps
        "time": time_str,
        "time_unix": time_ms,
        "updated": updated_str,
        "updated_unix": updated_ms,
        "tz": props.get("tz", ""),
        
        # Magnitude et intensité
        "magnitude": props.get("mag", ""),
        "mag_type": props.get("magType", ""),
        "mmi": props.get("mmi", ""),  # Intensité modifiée de Mercalli
        "felt": props.get("felt", ""),  # Nombre de personnes ayant ressenti
        "cdi": props.get("cdi", ""),  # Intensité maximale rapportée
        "mcd": props.get("mcd", ""),  # Distance au plus proche point de données
        
        # Localisation
        "place": props.get("place", ""),
        "longitude": coords[0] if len(coords) > 0 else "",
        "latitude": coords[1] if len(coords) > 1 else "",
        "depth": coords[2] if len(coords) > 2 else "",  # Profondeur en km
        
        # Données techniques
        "type": props.get("type", ""),
        "status": props.get("status", ""),
        "net": props.get("net", ""),  # Réseau sismique source
        "nst": props.get("nst", ""),  # Nombre de stations
        "dmin": props.get("dmin", ""),  # Distance minimale aux stations
        "gap": props.get("gap", ""),  # Écart angulaire
        "rms": props.get("rms", ""),  # Erreur quadratique moyenne
        
        # Alertes et significativité
        "alert": props.get("alert", ""),  # Niveau d'alerte (green, yellow, orange, red)
        "sig": props.get("sig", ""),  # Significativité de l'événement
        "tsunami": props.get("tsunami", 0),
        
        # Types de produits
        "types": props.get("types", ""),
        
        # URL
        "url": props.get("url", ""),
        "detail": props.get("detail", ""),
    }
    
    return data


def save_to_csv(data, filename):
    """
    Sauvegarde toutes les données de tremblements de terre dans un fichier CSV.
    
    Args:
        data: Données GeoJSON des tremblements de terre
        filename: Nom du fichier CSV à créer
    """
    features = data.get("features", [])
    
    # Extraire toutes les données
    all_data = [extract_all_earthquake_data(feature) for feature in features]
    
    # Définir les colonnes dans l'ordre souhaité
    fieldnames = [
        "id", "code", "time", "time_unix", "updated", "updated_unix", "tz",
        "magnitude", "mag_type", "mmi", "felt", "cdi", "mcd",
        "place", "latitude", "longitude", "depth",
        "type", "status", "net", "nst", "dmin", "gap", "rms",
        "alert", "sig", "tsunami", "types",
        "url", "detail", "ids", "sources"
    ]
    
    # Écrire le CSV
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for eq_data in all_data:
            # Convertir les valeurs None en chaînes vides pour le CSV
            row = {key: (eq_data.get(key, "") or "") for key in fieldnames}
            writer.writerow(row)
    
    print(f"✅ CSV créé avec {len(all_data)} tremblements de terre")
    print(f"   Colonnes: {len(fieldnames)}")


def display_earthquakes(data):
    """
    Affiche les données de tremblements de terre de manière formatée.
    
    Args:
        data: Données GeoJSON des tremblements de terre
    """
    if not data or "features" not in data:
        print("⚠️  Aucune donnée disponible")
        return
    
    features = data.get("features", [])
    metadata = data.get("metadata", {})
    
    print("=" * 100)
    print("🌍 DONNÉES DE TREMBLEMENTS DE TERRE - USGS")
    print("=" * 100)
    
    # Informations générales
    print(f"\n📊 Statistiques:")
    print(f"   Total de séismes trouvés: {metadata.get('count', len(features))}")
    print(f"   Période: {metadata.get('start', 'N/A')} → {metadata.get('end', 'N/A')}")
    
    if not features:
        print("\n⚠️  Aucun tremblement de terre trouvé pour cette période.")
        return
    
    # Statistiques sur les magnitudes
    magnitudes = [f.get("properties", {}).get("mag") for f in features if f.get("properties", {}).get("mag")]
    if magnitudes:
        print(f"   Magnitude minimale: {min(magnitudes):.1f}")
        print(f"   Magnitude maximale: {max(magnitudes):.1f}")
        print(f"   Magnitude moyenne: {sum(magnitudes) / len(magnitudes):.1f}")
    
    # Afficher les tremblements de terre
    print(f"\n📋 Liste des tremblements de terre ({len(features)} séismes):")
    print("-" * 100)
    print(f"{'Date':<20} | {'Magnitude':<10} | {'Lieu':<50} | {'Profondeur (km)':<15}")
    print("-" * 100)
    
    for idx, feature in enumerate(features, 1):
        eq_data = format_earthquake_data(feature)
        
        magnitude = eq_data.get("magnitude")
        magnitude_str = f"{magnitude:.1f}" if magnitude else "N/A"
        
        lieu = eq_data.get("lieu", "N/A")
        # Tronquer le lieu si trop long
        if len(lieu) > 48:
            lieu = lieu[:45] + "..."
        
        profondeur = eq_data.get("profondeur")
        profondeur_str = f"{profondeur:.1f}" if profondeur else "N/A"
        
        date_str = eq_data.get("date", "N/A")
        
        # Code couleur pour la magnitude (optionnel, juste pour l'affichage)
        magnitude_emoji = "🔴" if magnitude and magnitude >= 7.0 else "🟠" if magnitude and magnitude >= 6.0 else "🟡" if magnitude and magnitude >= 5.0 else "🟢"
        
        print(f"{date_str:<20} | {magnitude_emoji} {magnitude_str:<8} | {lieu:<50} | {profondeur_str:<15}")
    
    print("-" * 100)
    
    # Afficher les 5 plus forts séismes
    if len(features) > 0:
        sorted_features = sorted(
            features,
            key=lambda x: x.get("properties", {}).get("mag", 0),
            reverse=True
        )
        
        print(f"\n🔥 Top 5 des séismes les plus puissants:")
        print("-" * 100)
        for idx, feature in enumerate(sorted_features[:5], 1):
            eq_data = format_earthquake_data(feature)
            magnitude = eq_data.get("magnitude")
            print(f"   {idx}. Magnitude {magnitude:.1f} - {eq_data.get('lieu')}")
            print(f"      Date: {eq_data.get('date')}")
            print(f"      Coordonnées: {eq_data.get('latitude'):.2f}°N, {eq_data.get('longitude'):.2f}°E")
            if eq_data.get("tsunami"):
                print(f"      ⚠️  Alerte tsunami!")
            print()


def main():
    """Fonction principale"""
    print("🌍 Récupération des données de tremblements de terre...\n")
    
    # Paramètres de recherche
    start_date = "2026-01-01"
    end_date = "2026-02-04"
    min_magnitude = 4.5
    
    print(f"📅 Période: {start_date} → {end_date}")
    print(f"📏 Magnitude minimale: {min_magnitude}\n")
    
    # Récupérer les données
    data = get_earthquakes(start_date, end_date, min_magnitude)
    
    if data:
        # Afficher les données
        display_earthquakes(data)
        
        # Sauvegarder dans un fichier CSV avec toutes les informations
        csv_filename = f"earthquakes_{start_date}_{end_date}.csv"
        print(f"\n💾 Création du fichier CSV...")
        save_to_csv(data, csv_filename)
        print(f"   Fichier CSV: {csv_filename}")
        
        # Afficher les premières lignes du CSV sous forme de dataframe pandas
        print(f"\n📊 Aperçu du DataFrame pandas (premières lignes):")
        print("=" * 100)
        try:
            df = pd.read_csv(csv_filename)
            print(df.head(10))
            # print(f"\nShape du DataFrame: {df.shape[0]} lignes × {df.shape[1]} colonnes\n")
            # print(df.head(10).to_string())
            # print(f"\n... (affichage des 10 premières lignes sur {len(df)} total)")
        except Exception as e:
            print(f"⚠️  Erreur lors de la lecture du CSV: {e}")
        
        # Optionnel: sauvegarder aussi dans un fichier JSON
        json_filename = f"earthquakes_{start_date}_{end_date}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Fichier JSON: {json_filename}")
    else:
        print("❌ Impossible de récupérer les données.")


if __name__ == "__main__":
    main()
