"""
Script pour extraire les données de tremblements de terre depuis l'API USGS
et les stocker dans une base de données locale DuckDB en utilisant dlt.

Documentation API: https://earthquake.usgs.gov/fdsnws/event/1/
"""
import dlt
from datetime import datetime, timedelta
from typing import Iterator, Dict, Any
import requests


@dlt.source
def usgs_earthquake_source(
    start_date: str = None,
    end_date: str = None,
    min_magnitude: float = 4.5,
    max_magnitude: float = None,
    limit: int = 20000,
):
    """
    Source dlt pour récupérer les données de tremblements de terre depuis l'API USGS.
    
    Args:
        start_date: Date de début au format "YYYY-MM-DD" (défaut: il y a 30 jours)
        end_date: Date de fin au format "YYYY-MM-DD" (défaut: aujourd'hui)
        min_magnitude: Magnitude minimale (défaut: 4.5)
        max_magnitude: Magnitude maximale (optionnel)
        limit: Nombre maximum de résultats (défaut: 20000)
    
    Returns:
        Source dlt configurée
    """
    # Définir les dates par défaut si non fournies
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    @dlt.resource(name="earthquakes")
    def get_earthquakes() -> Iterator[Dict[str, Any]]:
        """
        Récupère les données de tremblements de terre depuis l'API USGS.
        """
        base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        
        params = {
            "format": "geojson",
            "starttime": start_date,
            "endtime": end_date,
            "minmagnitude": min_magnitude,
            "orderby": "time",
            "limit": limit,
        }
        
        if max_magnitude is not None:
            params["maxmagnitude"] = max_magnitude
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extraire les features et transformer en format tabulaire
            features = data.get("features", [])
            
            for feature in features:
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [])
                feature_id = feature.get("id", "")
                
                # Convertir les timestamps Unix en dates lisibles
                time_ms = props.get("time", 0)
                updated_ms = props.get("updated", 0)
                
                time_str = None
                updated_str = None
                
                if time_ms:
                    time_str = datetime.fromtimestamp(time_ms / 1000).isoformat()
                
                if updated_ms:
                    updated_str = datetime.fromtimestamp(updated_ms / 1000).isoformat()
                
                # Créer un dictionnaire avec toutes les données
                earthquake_data = {
                    # Identifiants
                    "id": feature_id,
                    "code": props.get("code"),
                    "ids": props.get("ids"),
                    "sources": props.get("sources"),
                    
                    # Dates et temps
                    "time": time_str,
                    "time_unix_ms": time_ms,
                    "updated": updated_str,
                    "updated_unix_ms": updated_ms,
                    "tz": props.get("tz"),
                    
                    # Magnitude et intensité
                    "magnitude": props.get("mag"),
                    "mag_type": props.get("magType"),
                    "mmi": props.get("mmi"),  # Intensité modifiée de Mercalli
                    "felt": props.get("felt"),  # Nombre de personnes ayant ressenti
                    "cdi": props.get("cdi"),  # Intensité maximale rapportée
                    "mcd": props.get("mcd"),  # Distance au plus proche point de données
                    
                    # Localisation
                    "place": props.get("place"),
                    "longitude": coords[0] if len(coords) > 0 else None,
                    "latitude": coords[1] if len(coords) > 1 else None,
                    "depth_km": coords[2] if len(coords) > 2 else None,  # Profondeur en km
                    
                    # Données techniques
                    "type": props.get("type"),
                    "status": props.get("status"),
                    "net": props.get("net"),  # Réseau sismique source
                    "nst": props.get("nst"),  # Nombre de stations
                    "dmin": props.get("dmin"),  # Distance minimale aux stations
                    "gap": props.get("gap"),  # Écart angulaire
                    "rms": props.get("rms"),  # Erreur quadratique moyenne
                    
                    # Alertes et significativité
                    "alert": props.get("alert"),  # Niveau d'alerte (green, yellow, orange, red)
                    "sig": props.get("sig"),  # Significativité de l'événement
                    "tsunami": props.get("tsunami", 0),
                    
                    # Types de produits
                    "types": props.get("types"),
                    
                    # URL
                    "url": props.get("url"),
                    "detail": props.get("detail"),
                }
                
                yield earthquake_data
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur lors de la récupération des données: {e}")
    
    return get_earthquakes


def main():
    """Fonction principale pour exécuter le pipeline dlt"""
    print("🌍 Extraction des données de tremblements de terre avec dlt...\n")
    
    # Configuration des paramètres de recherche
    start_date = "2026-01-01"
    end_date = "2026-02-08"
    min_magnitude = 4.5
    
    print(f"📅 Période: {start_date} → {end_date}")
    print(f"📏 Magnitude minimale: {min_magnitude}\n")
    
    # Créer la source dlt
    source = usgs_earthquake_source(
        start_date=start_date,
        end_date=end_date,
        min_magnitude=min_magnitude,
    )
    
    # Créer le pipeline dlt avec DuckDB comme destination locale
    pipeline = dlt.pipeline(
        pipeline_name="usgs_earthquakes",
        destination="duckdb",
        dataset_name="earthquake_data",
    )
    
    # Exécuter le pipeline (extraction, normalisation et chargement)
    print("🔄 Exécution du pipeline...")
    load_info = pipeline.run(source)
    
    # Afficher les informations de chargement
    print("\n✅ Chargement terminé!")
    print(load_info)
    
    # Afficher un aperçu des données chargées
    print("\n📊 Aperçu des données chargées:")
    print("=" * 100)
    
    # Récupérer les données depuis DuckDB en utilisant pandas
    try:
        import pandas as pd
        
        # Charger les données dans un DataFrame pandas directement depuis la table
        df = pipeline.dataset().earthquakes.df()
        
        # Afficher les statistiques
        print(f"Nombre total de tremblements de terre: {len(df)}")
        
        if len(df) > 0:
            # Afficher les colonnes principales
            print("\n📋 Aperçu des 10 premiers tremblements de terre (triés par date):")
            print("-" * 120)
            
            # Sélectionner et trier les colonnes d'intérêt
            display_cols = ["time", "magnitude", "place", "depth_km", "alert", "tsunami"]
            available_cols = [col for col in display_cols if col in df.columns]
            
            # Trier par date décroissante et prendre les 10 premiers
            df_sorted = df.sort_values("time", ascending=False, na_position="last")
            df_display = df_sorted[available_cols].head(10)
            
            # Afficher le DataFrame formaté
            pd.set_option("display.max_columns", None)
            pd.set_option("display.width", None)
            pd.set_option("display.max_colwidth", 40)
            print(df_display.to_string(index=False))
            
            # Afficher quelques statistiques
            print("\n📈 Statistiques:")
            if "magnitude" in df.columns:
                print(f"   Magnitude minimale: {df['magnitude'].min():.2f}")
                print(f"   Magnitude maximale: {df['magnitude'].max():.2f}")
                print(f"   Magnitude moyenne: {df['magnitude'].mean():.2f}")
            
            if "tsunami" in df.columns:
                tsunami_count = df["tsunami"].sum() if df["tsunami"].dtype in ["int64", "float64"] else 0
                print(f"   Tremblements avec alerte tsunami: {tsunami_count}")
        
    except ImportError:
        print("⚠️  pandas n'est pas disponible, affichage limité")
        print("   Installez pandas pour voir les statistiques détaillées")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'affichage des données: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n💾 Les données sont stockées dans DuckDB localement.")
    print(f"   Base de données: {pipeline.pipeline_name}.duckdb")
    print(f"   Table: earthquakes")


if __name__ == "__main__":
    main()