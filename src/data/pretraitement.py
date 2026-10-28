
import numpy as np
import pandas as pd
from src.features.build_features import creer_features, detecter_prix_extremes

MESURES_2023 = ["MED_SL", "POP", "SUP", "DWELLINGS", "DWELLINGS_OCS_DW_MAIN",
                "DWELLINGS_OCS_DW_MAIN_TSH_100", "DWELLINGS_OCS_DW_SEC_DW_OCC",
                "DWELLINGS_OCS_DW_VAC"]
RENOMMAGE = {"GEO": "code_commune", "MED_SL": "niveau_vie_median",
             "POP": "population", "SUP": "superficie_km2", "DWELLINGS": "nb_logements",
             "DWELLINGS_OCS_DW_MAIN": "nb_residences_principales",
             "DWELLINGS_OCS_DW_MAIN_TSH_100": "nb_proprietaires",
             "DWELLINGS_OCS_DW_SEC_DW_OCC": "nb_residences_secondaires",
             "DWELLINGS_OCS_DW_VAC": "nb_logements_vacants",
             "UNIT_LOC": "nb_etablissements"}
COLONNES_SUPPRIMEES = [
    "numero_disposition", "nature_mutation", "adresse_suffixe", "code_departement",
    "ancien_code_commune", "ancien_nom_commune", "ancien_id_parcelle", "numero_volume",
    "lot2_numero", "lot2_surface_carrez", "lot3_numero", "lot3_surface_carrez",
    "lot4_numero", "lot4_surface_carrez", "lot5_numero", "lot5_surface_carrez",
    "code_type_local", "code_nature_culture", "code_nature_culture_speciale",
    "nature_culture_speciale",
    # Suppression lors de la finalisation dans le notebook d'origine
    "nature_culture", "nom_commune", "code_postal", "id_mutation", "id_parcelle",
    "adresse_nom_voie", "adresse_code_voie", "date_mutation", "adresse_numero",
    "lot1_numero",
]


def preparer_dvf(dvf: pd.DataFrame) -> pd.DataFrame:
    df = dvf.copy()
    df = df.loc[df["nature_mutation"].eq("Vente") &
                df["type_local"].isin(["Maison", "Appartement"])].drop_duplicates().copy()
    # Une mutation avec plusieurs profils de logements est écartée.
    profils = df[["id_mutation", "type_local", "surface_reelle_bati",
                  "nombre_pieces_principales"]].drop_duplicates()
    profils_par_mutation = profils.groupby("id_mutation").size()
    ids_multi = profils_par_mutation.index[profils_par_mutation > 1]
    df = df.loc[~df["id_mutation"].isin(ids_multi)].copy()
    # On somme chaque composante foncière une fois par mutation.
    terrains = df[["id_mutation", "id_parcelle", "nature_culture",
                  "nature_culture_speciale", "surface_terrain"]].drop_duplicates()
    surface = terrains.groupby("id_mutation")["surface_terrain"].sum(min_count=1)
    df = df.drop_duplicates(subset=["id_mutation"], keep="first").copy()
    df["surface_terrain"] = df["id_mutation"].map(surface)
    df["code_commune"] = df["code_commune"].astype("string").str.zfill(5)
    df["type_local"] = df["type_local"].astype("string")
    df.loc[df["nombre_pieces_principales"].eq(0), "nombre_pieces_principales"] = np.nan
    df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
    df = df.loc[df["surface_reelle_bati"] > 0].copy()
    df = creer_features(df)
    df, _, _ = detecter_prix_extremes(df)
    # Reproduit les colonnes de dvf_nettoye.csv, sans appeler finaliser_datasets,
    # car cette fonction écrit des CSV sur disque.
    df = df.drop(columns=COLONNES_SUPPRIMEES, errors="ignore")
    if df.empty:
        raise ValueError("Le prétraitement DVF a produit un DataFrame vide.")
    print(f"DVF préparé : {len(df):,} ventes")
    return df.reset_index(drop=True)


def preparer_insee(insee: pd.DataFrame) -> pd.DataFrame:
    df = insee.copy()
    df["TIME_PERIOD"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce")
    choix = ((df["TAB_MEASURE"].isin(MESURES_2023) & df["TIME_PERIOD"].eq(2023))
             | (df["TAB_MEASURE"].eq("UNIT_LOC") & df["TIME_PERIOD"].eq(2024)))
    selection = df.loc[choix, ["GEO", "TAB_MEASURE", "OBS_VALUE"]].copy()
    selection["OBS_VALUE"] = pd.to_numeric(selection["OBS_VALUE"], errors="coerce")
    if selection.empty:
        raise ValueError("Indicateurs INSEE 2023/2024 introuvables : vérifier les millésimes de la source.")
    if selection.duplicated(["GEO", "TAB_MEASURE"]).any():
        raise ValueError("Plusieurs valeurs INSEE pour une même commune et mesure : pivot ambigu.")
    resultat = selection.pivot(index="GEO", columns="TAB_MEASURE", values="OBS_VALUE").reset_index()
    resultat.columns.name = None
    resultat = resultat.rename(columns=RENOMMAGE)
    manquantes = set(RENOMMAGE.values()) - set(resultat.columns)
    if manquantes:
        raise ValueError(f"Mesures INSEE absentes : {sorted(manquantes)}")
    resultat["code_commune"] = resultat["code_commune"].astype("string").str.zfill(5)
    resultat["densite_population"] = resultat["population"] / resultat["superficie_km2"]
    resultat["part_proprietaires"] = 100 * resultat["nb_proprietaires"] / resultat["nb_residences_principales"]
    resultat["part_logements_vacants"] = 100 * resultat["nb_logements_vacants"] / resultat["nb_logements"]
    resultat = resultat.replace([np.inf, -np.inf], np.nan)
    print(f"INSEE préparé : {len(resultat)} territoires")
    return resultat


def fusionner(dvf: pd.DataFrame, insee: pd.DataFrame) -> pd.DataFrame:
    base = dvf.copy()
    base["code_jointure_insee"] = base["code_commune"].replace({"69152": "69149", "69159": "69114"})
    socio = insee.rename(columns={"code_commune": "code_jointure_insee"})
    if socio["code_jointure_insee"].duplicated().any():
        raise ValueError("Codes communes INSEE dupliqués : risque de multiplication des ventes.")
    resultat = base.merge(socio, on="code_jointure_insee", how="left", validate="many_to_one", indicator=True)
    print("Jointure DVF / INSEE :", resultat["_merge"].value_counts().to_dict())
    resultat = resultat.drop(columns=["code_jointure_insee", "_merge"])
    assert len(resultat) == len(dvf), "La jointure a changé le nombre de ventes."
    return resultat


def pretraiter(dvf_brut: pd.DataFrame, insee_brut: pd.DataFrame) -> pd.DataFrame:
    return fusionner(preparer_dvf(dvf_brut), preparer_insee(insee_brut))
