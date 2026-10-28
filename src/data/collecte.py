
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile
import requests
import pandas as pd 

DVF_URL = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260717-142041/dvf.csv.gz"
INSEE_URL = "https://www.insee.fr/fr/statistiques/fichier/2521169/comparateur_csv.zip"
LYON_ARRONDISSEMENTS = {f"6938{i}" for i in range(1, 10)}


def collecter_dvf() -> pd.DataFrame:
    """Lit le DVF national par lots et ne garde que le département 69."""
    morceaux = []
    for lot in pd.read_csv(
        DVF_URL, compression="gzip", chunksize=20_000, low_memory=False,
        dtype={"code_departement": "string", "code_commune": "string",
               "id_mutation": "string", "id_parcelle": "string",
               "numero_volume": "string", "lot1_numero": "string"},
    ):
        rhone = lot.loc[lot["code_departement"] == "69"]
        if not rhone.empty:
            morceaux.append(rhone)
    if not morceaux:
        raise ValueError("Aucune transaction DVF trouvée dans le département 69.")
    dvf = pd.concat(morceaux, ignore_index=True)
    print(f"DVF Rhône : {len(dvf):,} lignes")
    return dvf


def collecter_insee() -> pd.DataFrame:
    """Télécharge le ZIP officiel INSEE, lit le CSV en mémoire et filtre le Rhône."""
    reponse = requests.get(INSEE_URL, timeout=180)
    reponse.raise_for_status()
    with ZipFile(BytesIO(reponse.content)) as archive:
        candidats = [n for n in archive.namelist()
                     if n.lower().endswith(".csv")
                     and "metadata" not in n.lower()
                     and not n.startswith("__MACOSX/")]
        if not candidats:
            raise ValueError(f"CSV de données INSEE introuvable dans le ZIP : {archive.namelist()}")
        # Si plusieurs CSV, privilégier le principal (le plus gros fichier).
        nom = max(candidats, key=lambda n: archive.getinfo(n).file_size)
        with archive.open(nom) as fichier:
            insee = pd.read_csv(fichier, sep=None, engine="python", dtype={"GEO": "string"})
    colonnes = {"GEO", "GEO_OBJECT", "TIME_PERIOD", "TAB_MEASURE", "OBS_VALUE"}
    if not colonnes.issubset(insee.columns):
        raise ValueError(f"Format INSEE inattendu ({nom}). Colonnes : {list(insee.columns)}")
    insee["GEO"] = insee["GEO"].str.zfill(5)
    filtre = ((insee["GEO_OBJECT"].eq("COM") & insee["GEO"].str.startswith("69", na=False))
              | (insee["GEO_OBJECT"].eq("ARM") & insee["GEO"].isin(LYON_ARRONDISSEMENTS)))
    resultat = insee.loc[filtre].copy()
    if resultat.empty:
        raise ValueError("Aucune observation INSEE pour le Rhône.")
    print(f"INSEE Rhône : {len(resultat):,} observations, {resultat['GEO'].nunique()} territoires")
    return resultat


def collecter():
    """Retourne les deux DataFrames bruts en mémoire."""
    return collecter_dvf(), collecter_insee()
