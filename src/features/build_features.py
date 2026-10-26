import numpy as np
import pandas as pd
from geopy.distance import geodesic

def creer_features(dvf):

    dvf = dvf.copy()

    # 1. Variables temporelles
    dvf["date_mutation"] = pd.to_datetime(dvf["date_mutation"])
    dvf["annee_mutation"] = dvf["date_mutation"].dt.year
    dvf["mois_mutation"] = dvf["date_mutation"].dt.month

    # 2. Prix au m²
    dvf["prix_m2"] = dvf["valeur_fonciere"] / dvf["surface_reelle_bati"]

    # 3. Surface par pièce
    # dvf.loc[dvf["nombre_pieces_principales"] <= 0, "nombre_pieces_principales"] = np.nan
    dvf["surface_par_piece"] = dvf["surface_reelle_bati"] / dvf["nombre_pieces_principales"]
    dvf["log_surface"] = np.log1p(dvf["surface_reelle_bati"])

    # 4. Distance par rapport au centre de Lyon
    # https://www.countrycoordinate.com/city-lyon-france/
    lyon = (45.7640, 4.8357)
    dvf["distance_lyon_km"] = dvf.apply(lambda ligne: geodesic((ligne["latitude"], ligne["longitude"]), lyon).km if pd.notna(ligne["latitude"]) and pd.notna(ligne["longitude"]) else np.nan, axis=1)

    # 5. Remplacer les valeurs infinies par des valeurs manquantes
    dvf = dvf.replace([np.inf, -np.inf], np.nan)

    return dvf


def detecter_prix_extremes(dvf):
   
    # Détecte les prix au m² extrêmes avec la règle de Tukey
    # appliquée au logarithme du prix
    # (La règle de Tukey => méthode statistique utilisée pour détecter les valeurs extrêmes à partir des quartiles.)

    # Le calcul est réalisé séparément pour les maisons
    # et les appartements.

    # Retourne :
    # - le DataFrame filtré ;
    # - les observations extrêmes ;
    # - le tableau des seuils.
     
    dvf = dvf.copy()

    # 1. Vérifier que prix_m2 existe
    if "prix_m2" not in dvf.columns:
        raise ValueError("La colonne prix_m2 n'existe pas. Exécutez d'abord creer_features().")

    # 2. Conserver uniquement les prix valides
    prix_valides = dvf["prix_m2"].notna() & np.isfinite(dvf["prix_m2"]) & (dvf["prix_m2"] > 0)
    dvf = dvf.loc[prix_valides].copy()

    # 3. Transformer le prix au m² en logarithme
    dvf["log_prix_m2"] = np.log1p(dvf["prix_m2"])

    # 4. Initialiser les résultats
    masque_valide = pd.Series(False, index=dvf.index)
    seuils = []

    # 5. Calculer les seuils séparément pour chaque type de logement
    for type_bien, groupe in dvf.groupby("type_local"):

        q1 = groupe["log_prix_m2"].quantile(0.25)
        q3 = groupe["log_prix_m2"].quantile(0.75)
        iqr = q3 - q1

        borne_basse_log = q1 - 1.5 * iqr
        borne_haute_log = q3 + 1.5 * iqr

        borne_basse = np.expm1(borne_basse_log)
        borne_haute = np.expm1(borne_haute_log)

        masque_type = (dvf["type_local"] == type_bien) & dvf["prix_m2"].between(borne_basse, borne_haute)
        masque_valide |= masque_type

        nombre_extremes = (~masque_type.loc[groupe.index]).sum()

        seuils.append({
            "Type": type_bien,
            "Borne basse (€/m²)": borne_basse,
            "Borne haute (€/m²)": borne_haute,
            "Nombre total": len(groupe),
            "Valeurs extrêmes": nombre_extremes
        })

    # 6. Séparer les données conservées et les valeurs extremes
    dvf_filtre = dvf.loc[masque_valide].copy()
    valeurs_extremes = dvf.loc[~masque_valide].copy()

    # 7. Supprimer la variable temporaire
    dvf_filtre = dvf_filtre.drop(columns="log_prix_m2")
    valeurs_extremes = valeurs_extremes.drop(columns="log_prix_m2")

    # 8. Créer le tableau récapitulatif des seuils
    tableau_seuils = pd.DataFrame(seuils)

    return dvf_filtre, valeurs_extremes, tableau_seuils


def finaliser_datasets(dvf_initial, dvf_nettoye):
    # Finalise et exporte les deux versions du dataset DVF :
    # - dvf_initial : avec les prix extrêmes ;
    # - dvf_nettoye : sans les prix extrêmes.
    
    colonnes_a_supprimer = ["nature_culture", "nom_commune", "code_postal", "id_mutation", "id_parcelle", "adresse_nom_voie", "adresse_code_voie", "date_mutation", "code_departement", "adresse_numero", "lot1_numero"]
    datasets = {"dvf_initial": dvf_initial.copy(), "dvf_nettoye": dvf_nettoye.copy()}
    resultats = {}

    for nom, df in datasets.items():

        # Suppression des colonnes inutiles
        df = df.drop(columns=colonnes_a_supprimer, errors="ignore")

        # Vérification des lignes identiques
        # nb_lignes_identiques = df.duplicated().sum()

        # Contrôles finaux
        assert df["prix_m2"].notna().all(), f"{nom} : il reste des NA dans prix_m2."
        assert df["valeur_fonciere"].notna().all(), f"{nom} : il reste des NA dans valeur_fonciere."
        assert df["surface_reelle_bati"].notna().all(), f"{nom} : il reste des NA dans surface_reelle_bati."
        assert (df["surface_reelle_bati"] > 0).all(), f"{nom} : il reste des surfaces bâties <= 0."
        assert set(df["type_local"].dropna().unique()).issubset({"Maison", "Appartement"}), f"{nom} : type_local contient une valeur inattendue."

        # Export
        chemin = f"../data/processed/{nom}.csv"
        df.to_csv(chemin, index=False)

        # Bilan
        print(f"\n--- {nom} ---")
        print("Dimensions :", df.shape)
        # print("Lignes identiques :", nb_lignes_identiques)
        print("Fichier enregistré :", chemin)

        resultats[nom] = df

    return resultats["dvf_initial"], resultats["dvf_nettoye"]

def creer_features_prediction(df): 
    df = df.copy()

    df["surface_par_piece"] = (df["surface_reelle_bati"] / df["nombre_pieces_principales"])
    df["log_surface"] = np.log1p(df["surface_reelle_bati"])
    lyon = (45.7640, 4.8357)

    df["distance_lyon_km"] = df.apply(
        lambda ligne: geodesic(
            (ligne["latitude"], ligne["longitude"]),
            lyon
        ).km
        if pd.notna(ligne["latitude"])
        and pd.notna(ligne["longitude"])
        else np.nan,
        axis=1
    )

    df = df.replace([np.inf, -np.inf], np.nan)

    return df