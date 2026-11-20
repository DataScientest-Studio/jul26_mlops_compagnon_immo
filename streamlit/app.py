#Streamlit : interface utilisant API prediction

import os
import time

import requests
import streamlit as st

PREDICTION_API_URL = os.getenv("PREDICTION_API_URL", "http://localhost:8000").rstrip("/")

# Les communes du Rhône et 9 arrondissements de Lyon.
COMMUNES_RHONE = { code: nom for code, nom in ( ligne.split("|", 1) for ligne in """69001|Affoux
69002|Aigueperse
69003|Albigny-sur-Saône
69004|Alix
69005|Ambérieux
69006|Amplepuis
69007|Ampuis
69008|Ancy
69009|Anse
69010|L'Arbresle
69012|Les Ardillats
69013|Arnas
69014|Aveize
69016|Azolette
69017|Bagnols
69018|Beaujeu
69179|Beauvallon
69019|Belleville-en-Beaujolais
69020|Belmont-d'Azergues
69021|Bessenay
69022|Bibost
69023|Blacé
69026|Le Breuil
69027|Brignais
69028|Brindas
69029|Bron
69030|Brullioles
69031|Brussieu
69032|Bully
69033|Cailloux-sur-Fontaines
69034|Caluire-et-Cuire
69035|Cenves
69036|Cercié
69228|Chabanière
69037|Chambost-Allières
69038|Chambost-Longessaigne
69039|Chamelet
69040|Champagne-au-Mont-d'Or
69042|La Chapelle-sur-Coise
69270|Chaponnay
69043|Chaponost
69044|Charbonnières-les-Bains
69045|Charentay
69046|Charly
69047|Charnay
69049|Chasselay
69271|Chassieu
69051|Chaussan
69052|Chazay-d'Azergues
69056|Chessy
69057|Chevinay
69058|Chiroubles
69050|Châtillon
69055|Les Chères
69053|Chénas
69054|Chénelette
69059|Civrieux-d'Azergues
69060|Claveisolles
69061|Cogny
69062|Coise
69063|Collonges-au-Mont-d'Or
69299|Colombier-Saugnieu
69272|Communay
69064|Condrieu
69273|Corbas
69065|Corcelles-en-Beaujolais
69066|Cours
69067|Courzieu
69068|Couzon-au-Mont-d'Or
69069|Craponne
69070|Cublize
69071|Curis-au-Mont-d'Or
69072|Dardilly
69074|Denicé
69135|Deux-Grosnes
69075|Dième
69076|Dommartin
69077|Dracé
69078|Duerne
69275|Décines-Charpieu
69276|Feyzin
69084|Fleurie
69085|Fleurieu-sur-Saône
69086|Fleurieux-sur-l'Arbresle
69087|Fontaines-Saint-Martin
69088|Fontaines-sur-Saône
69089|Francheville
69090|Frontenas
69277|Genas
69278|Genay
69091|Givors
69092|Gleizé
69093|Grandris
69096|Grigny-sur-Rhône
69094|Grézieu-la-Varenne
69095|Grézieu-le-Marché
69097|Les Haies
69098|Les Halles
69099|Haute-Rivoire
69100|Irigny
69279|Jonage
69280|Jons
69102|Joux
69103|Juliénas
69104|Jullié
69105|Lacenas
69106|Lachassagne
69107|Lamure-sur-Azergues
69108|Lancié
69109|Lantignié
69110|Larajasse
69112|Lentilly
69115|Limas
69116|Limonest
69117|Lissieu
69118|Loire-sur-Rhône
69119|Longes
69120|Longessaigne
69121|Lozanne
69122|Lucenay
69123|Lyon
69111|Légny
69113|Létra
69124|Marchampt
69125|Marcilly-d'Azergues
69126|Marcy
69127|Marcy-l'Étoile
69281|Marennes
69130|Meaux-la-Montagne
69131|Messimy
69132|Meys
69282|Meyzieu
69133|Millery
69283|Mions
69134|Moiré
69136|Montagny
69284|Montanay
69137|Montmelas-Saint-Sorlin
69138|Montromant
69139|Montrottier
69140|Morancé
69141|Mornant
69142|La Mulatière
69143|Neuville-sur-Saône
69145|Odenas
69148|Orliénas
69149|Oullins-Pierre-Bénite
69151|Le Perréon
69153|Poleymieux-au-Mont-d'Or
69154|Pollionnay
69155|Pomeys
69156|Pommiers
69114|Porte des Pierres Dorées
69160|Poule-les-Écharmeaux
69161|Propières
69285|Pusignan
69163|Quincieux
69162|Quincié-en-Beaujolais
69164|Ranchal
69286|Rillieux-la-Pape
69166|Riverie
69167|Rivolet
69168|Rochetaillée-sur-Saône
69169|Ronno
69170|Rontalon
69165|Régnié-Durette
69171|Sain-Bel
69180|Saint-André-la-Côte
69181|Saint-Appolinaire
69287|Saint-Bonnet-de-Mure
69182|Saint-Bonnet-des-Bruyères
69183|Saint-Bonnet-le-Troncy
69186|Saint-Clément-de-Vers
69187|Saint-Clément-les-Places
69188|Saint-Clément-sur-Valsonne
69191|Saint-Cyr-au-Mont-d'Or
69192|Saint-Cyr-le-Chatoux
69193|Saint-Cyr-sur-le-Rhône
69194|Saint-Didier-au-Mont-d'Or
69196|Saint-Didier-sur-Beaujeu
69199|Saint-Fons
69200|Saint-Forgeux
69204|Saint-Genis-Laval
69203|Saint-Genis-l'Argentière
69205|Saint-Genis-les-Ollières
69206|Saint-Georges-de-Reneins
69208|Saint-Germain-Nuelles
69207|Saint-Germain-au-Mont-d'Or
69209|Saint-Igny-de-Vers
69212|Saint-Jean-des-Vignes
69214|Saint-Jean-la-Bussière
69215|Saint-Julien
69216|Saint-Julien-sur-Bibost
69217|Saint-Just-d'Avray
69218|Saint-Lager
69219|Saint-Laurent-d'Agny
69220|Saint-Laurent-de-Chamousset
69288|Saint-Laurent-de-Mure
69225|Saint-Marcel-l'Éclairé
69227|Saint-Martin-en-Haut
69229|Saint-Nizier-d'Azergues
69289|Saint-Pierre-de-Chandieu
69231|Saint-Pierre-la-Palud
69290|Saint-Priest
69233|Saint-Romain-au-Mont-d'Or
69234|Saint-Romain-de-Popey
69235|Saint-Romain-en-Gal
69236|Saint-Romain-en-Gier
69291|Saint-Symphorien-d'Ozon
69238|Saint-Symphorien-sur-Coise
69240|Saint-Vincent-de-Reins
69239|Saint-Vérand
69197|Saint-Étienne-des-Oullières
69198|Saint-Étienne-la-Varenne
69184|Sainte-Catherine
69189|Sainte-Colombe
69190|Sainte-Consorce
69201|Sainte-Foy-l'Argentière
69202|Sainte-Foy-lès-Lyon
69230|Sainte-Paule
69172|Salles-Arbuissonnas-en-Beaujolais
69173|Sarcey
69292|Sathonay-Camp
69293|Sathonay-Village
69174|Les Sauvages
69175|Savigny
69295|Simandres
69296|Solaize
69176|Soucieu-en-Jarrest
69177|Sourcieux-les-Mines
69178|Souzy
69294|Sérézin-du-Rhône
69241|Taluyers
69242|Taponas
69243|Tarare
69244|Tassin-la-Demi-Lune
69245|Ternand
69297|Ternay
69246|Theizé
69248|Thizy-les-Bourgs
69249|Thurins
69250|La Tour-de-Salvagny
69298|Toussieu
69252|Trèves
69253|Tupin-et-Semons
69024|Val d'Oingt
69254|Valsonne
69255|Vaugneray
69256|Vaulx-en-Velin
69257|Vaux-en-Beaujolais
69258|Vauxrenard
69260|Vernaison
69261|Vernay
69265|Ville-sur-Jarnioux
69263|Villechenève
69264|Villefranche-sur-Saône
69266|Villeurbanne
69267|Villié-Morgon
69157|Vindry-sur-Turdine
69268|Vourles
69259|Vénissieux
69269|Yzeron
69080|Échalas
69081|Écully
69082|Émeringes
69083|Éveux
69381|Lyon 1er arrondissement
69382|Lyon 2e arrondissement
69383|Lyon 3e arrondissement
69384|Lyon 4e arrondissement
69385|Lyon 5e arrondissement
69386|Lyon 6e arrondissement
69387|Lyon 7e arrondissement
69388|Lyon 8e arrondissement
69389|Lyon 9e arrondissement""".splitlines() ) }

# Codes à exclure selon les données PostgreSQL
CODES_A_EXCLURE = {
    "69001", "69002", "69008", "69012", "69014",
    "69016", "69022", "69026", "69035", "69038",
    "69042", "69054", "69057", "69058", "69060",
    "69070", "69075", "69082", "69097", "69098",
    "69099", "69103", "69109", "69123", "69130",
    "69132", "69134", "69135", "69138", "69155",
    "69161", "69164", "69165", "69167", "69169",
    "69178", "69180", "69182", "69183", "69186",
    "69192", "69198", "69209", "69216", "69217",
    "69225", "69229", "69230", "69236", "69253",
    "69258", "69261"
}

# Conserver uniquement les communes avec Maison ET Appartement
COMMUNES_RHONE = {
    code: nom
    for code, nom in COMMUNES_RHONE.items()
    if code not in CODES_A_EXCLURE
}

OPTIONS_COMMUNES = [ f"{code} — {nom}" for code, nom in sorted( COMMUNES_RHONE.items(), key=lambda ligne: ligne[1].casefold() ) ]

st.set_page_config(page_title="Compagnon Immobilier", page_icon="🏠", layout="wide",)

# CSS des interfaces => Charger les styles depuis le fichier CSS externe.
from pathlib import Path

CSS_PATH = Path(__file__).resolve().parent / "style.css"
st.markdown(f"<style>\n{CSS_PATH.read_text(encoding='utf-8')}\n</style>", unsafe_allow_html=True)


def euros(valeur, decimales=0):
    nombre = f"{float(valeur):,.{decimales}f}"
    return nombre.replace(",", " ").replace(".", ",") + " €"

def deconnecter():
    for cle in ( "token", "utilisateur", "role", "page_active", "dernier_resultat", "dernier_logement", "duree_prediction", "code_reponse", "etat_apis", "commune_estimee", "infos_modele", ):
        st.session_state.pop(cle, None)
    st.rerun()


# En-tête
st.title("🏠 Compagnon Immobilier")
st.caption("Industrialisation d’un modèle de prédiction immobilière")
st.markdown("<hr style='margin: 5px 0; border: 0; border-top: 1px solid #D3D9E4;'>", unsafe_allow_html=True)

# Connexion via l'API FastAPI
if not st.session_state.get("token"):
    st.subheader("🔐 Connexion")
    if st.session_state.pop("session_expiree", False):
        st.warning("Session expirée. Veuillez vous reconnecter.")

    with st.form("form_connexion"):
        utilisateur = st.text_input("Utilisateur")
        mot_de_passe = st.text_input("Mot de passe", type="password")
        connecter = st.form_submit_button("Se connecter", type="primary")

    if connecter:
        try:
            reponse = requests.post( f"{PREDICTION_API_URL}/token", data={"username": utilisateur, "password": mot_de_passe}, timeout=10, )
            if reponse.status_code == 200:
                st.session_state["token"] = reponse.json()["access_token"]
                st.session_state["utilisateur"] = utilisateur
                st.session_state["role"] = utilisateur.strip().lower()
                st.session_state.pop("page_active", None)
                st.session_state.pop("infos_modele", None)
                st.rerun()
            elif reponse.status_code in (400, 401):
                st.error("Identifiants incorrects.")               
            else:
                st.error(f"Erreur de connexion (HTTP {reponse.status_code}).")
        except (requests.RequestException, ValueError, KeyError):
            st.error("Impossible de contacter l'API de prédiction.")

    st.stop()

# -----------------------------------------------------------------------------
# Présentation MLOps (admin) / Application métier (admin et user: sans Modèle Champion MLflow)
# -----------------------------------------------------------------------------
role = st.session_state.get("role")

# Onglet métier 
PAGE_ESTIMATION = "🏠 Estimation"
PAGE_TRANSACTION = "💰 Transaction réalisée"
PAGE_CHAMPION = "📊 Modèle champion et performance"

# 8 rubriques de la présentation
PAGES_SOUTENANCE = [
    "1. Contexte et objectifs",
    "2. Architecture et données",
    "3. Modèle et MLflow",
    "4. Déploiement et API",
    "5. CI/CD et tests",
    "6. Automatisation avec Airflow",
    "7. Monitoring et drift",
    "8. Bilan et perspectives",
]

# Icônes uniquement pour l'affichage du menu 
ICONES_SOUTENANCE = ["🎯", "🗂️", "🧠", "⚙️", "🔄", "🛠️", "📈", "✅"]

PAGES_METIER = [PAGE_ESTIMATION, PAGE_TRANSACTION]
if role == "admin":
    pages_autorisees = PAGES_SOUTENANCE + [PAGE_ESTIMATION, PAGE_CHAMPION, PAGE_TRANSACTION]
else:
    pages_autorisees = PAGES_METIER

# Évite une page inaccessible après un changement de profil.
if st.session_state.get("page_active") not in pages_autorisees:
    st.session_state["page_active"] = (
        PAGES_SOUTENANCE[0] if role == "admin" else PAGE_ESTIMATION
    )

def aller_vers(page):
    if page in pages_autorisees:
        st.session_state["page_active"] = page
        st.rerun()


# Deux sections séparées dans le même menu de gauche.
with st.sidebar:
    if role == "admin":
        st.markdown("**PRÉSENTATION DU PROJET MLOPS**")
        for index, rubrique in enumerate(PAGES_SOUTENANCE):
            if st.button(
                f"{ICONES_SOUTENANCE[index]}  {rubrique}",
                key=f"nav_soutenance_{index}",
                use_container_width=True,
                type=("primary" if st.session_state["page_active"] == rubrique
                      else "secondary"),
            ):
                aller_vers(rubrique)
        st.divider()

    st.markdown("**APPLICATION MÉTIER**" if role == "admin"
                else "**APPLICATION MÉTIER**")
    labels_metier = [(PAGE_ESTIMATION, "🏠 Estimation immobilière")]
    if role == "admin":
        labels_metier.append((PAGE_CHAMPION, "📊 Modèle Champion et performances"))
    labels_metier.append((PAGE_TRANSACTION, "💰 Transaction réalisée"))

    for index, (page, libelle) in enumerate(labels_metier):
        if st.button(
            libelle,
            key=f"nav_metier_{index}",
            use_container_width=True,
            type=("primary" if st.session_state["page_active"] == page
                  else "secondary"),
        ):
            aller_vers(page)

page_active = st.session_state["page_active"]

# Afficher la session et la déconnexion uniquement dans l'application métier.
# Sur les pages de soutenance, ces éléments sont masqués.
if page_active in (PAGE_ESTIMATION, PAGE_CHAMPION, PAGE_TRANSACTION):
    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.success(f"Connecté : {st.session_state.get('utilisateur', '')}")
    with col_logout:
        if st.button("Déconnexion", key="btn_deconnexion", use_container_width=True):
            deconnecter()

##################################################################################
# SOUTENANCE — ONGLET 1 : CONTEXTE ET OBJECTIFS
##################################################################################
if role == "admin" and page_active == PAGES_SOUTENANCE[0]:
    with st.container(key="soutenance_contexte"):
        st.markdown(
            '<h2 class="titre-soutenance">1. Contexte et objectifs</h2>',
            unsafe_allow_html=True
        )
        st.markdown("<hr style='border:0;border-top:1px solid #D3D9E4;margin:4px 0 12px;height: 18px;'>", unsafe_allow_html=True)
        
        st.markdown("### 📋 Cadre du projet")
        st.markdown("<div style='padding-left: 44px;'>"
            "<strong>Objectif : déployer une solution d'estimation immobilière "
            "dans un environnement MLOps.</strong>"
            "</div>",unsafe_allow_html=True
        )       
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        # Retrait commun pour les deux sous-parties du Cadre du projet.
        with st.container(key="soutenance_colonnes"):
            col_technique, col_metier = st.columns(2, gap="large")
            with col_technique:
                st.markdown("#### Cadre technique")
                st.markdown("""
                    - Construire une chaîne MLOps dédiée à la prédiction immobilière.
                    - Concevoir une architecture modulaire intégrant les données, le modèle et les composants applicatifs.
                    - Mettre en place un environnement reproductible et évolutif, facilitant l'exploitation et la maintenance.
                """)
            with col_metier:
                st.markdown("#### Contexte métier")
                st.markdown("""
                    - Estimer le prix au m² d'un logement à partir de ses caractéristiques.
                    - Exploiter les données DVF du Rhône, enrichies par des données INSEE.
                    - Proposer un outil d'aide à l'estimation destiné aux particuliers et aux professionnels de l'immobilier.
                """)

        # Un peu plus d’espace entre les deux colonnes et le dernier bloc.
        st.markdown("<div style='height: 55px;'></div>", unsafe_allow_html=True)
        st.markdown("### 🎯 Objectifs du projet MLOps")
        st.markdown("""
            - **Industrialisation :** rendre le modèle de prédiction immobilière exploitable au sein d'une application.
            - **Automatisation :** orchestrer les différentes étapes du pipeline, de la préparation des données à l'évaluation.
            - **Reproductibilité et traçabilité :** assurer le suivi des données, des expérimentations et des versions du modèle.
            - **Déploiement et supervision :** rendre la solution accessible et surveiller son fonctionnement ainsi que ses performances dans le temps.
        """)

##################################################################################
# SOUTENANCE — ONGLET 2 : ARCHITECTURE ET DONNÉES 
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[1]:
    with st.container(key="soutenance_architecture"):
        st.markdown(
            '<h2 class="titre-soutenance">2. Architecture et données</h2>',
            unsafe_allow_html=True
        )
        st.markdown("<hr style='border:0;border-top:1px solid #D3D9E4;margin:4px 0 12px;height:18px;'>", unsafe_allow_html=True) 
        st.markdown("### 🎯 Objectif")
        st.markdown(
            "<div style='padding-left: 44px;'>"
            "L’architecture repose sur une chaîne MLOps modulaire, automatisée et reproductible,"
            "intégrant les différentes étapes du cycle de vie du modèle, "
            "de la collecte et de la préparation des données jusqu’à l’entraînement, au déploiement et à la supervision."
            "<br>"
            "Cette organisation permet d'assurer la fiabilité, la traçabilité et la maintenabilité de la solution,"
            "tout en facilitant son exploitation et son évolution."
            "</div>", unsafe_allow_html=True
        )

        # Image architecture
        image_architecture = Path(__file__).resolve().parent / "images" / "Architecture_mlops.png"
        if image_architecture.is_file():
            st.image(str(image_architecture), width=1000)
        else:
            st.error("Image introuvable : images/Architecture_mlops.png")

##################################################################################
# SOUTENANCE — ONGLET 3 : MODÈLE ET MLFLOW
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[2]:
    with st.container(key="soutenance_mlflow"):
        st.markdown(
            '<h2 class="titre-soutenance">3. Modèle et MLflow</h2>',
            unsafe_allow_html=True
        )
        st.markdown("<hr style='border:0;border-top:1px solid #D3D9E4;margin:4px 0 12px;height:18px;'>", unsafe_allow_html=True)

        # OBJECTIF
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong> Objectif :</strong> "
            "Centraliser le suivi des entraînements du modèle XGBoost, "
            "comparer les performances, gérer les versions et conserver "
            "les artefacts avec MLflow et MinIO."
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True) 

        st.markdown("### 📊 Suivi et gestion des modèles")

        # Taille des libellés radio pour la soutenance (onglet 3 uniquement)
        st.markdown(
            "<style>"
            ".st-key-soutenance_mlflow_details [data-testid='stRadio'] p "
            "{ font-size:16px !important; }"
            "</style>",
            unsafe_allow_html=True
        )

        with st.container(key="soutenance_mlflow_details"):

            choix = st.radio(
                "Fonctionnalités MLflow",
                ["Tracking", "Model Registry", "Champion et MinIO"],
                horizontal=True,
                label_visibility="collapsed",
                key="capture_mlflow"
            )

            # Description et image selon le radio sélectionné
            contenus = {
                "Tracking": {
                    "titre": "MLflow Tracking — Suivi des expérimentations",
                    "description": (
                        "Suivre les runs d'entraînement, enregistrer les paramètres "
                        "et comparer les performances du modèle XGBoost "
                        "à travers les métriques MAE, RMSE et R²."
                    ),
                    "image": "mlflow_tracking.png"
                },
                "Model Registry": {
                    "titre": "Model Registry — Gestion des versions",
                    "description": (
                        "Centraliser les différentes versions du modèle XGBoost, "
                        "conserver leur historique et identifier la version "
                        "retenue pour les prédictions."
                    ),
                    "image": "mlflow_registry.png"
                },
                "Champion et MinIO": {
                    "titre": "Champion et MinIO ",
                    "description": (
                        "Utiliser l'alias Champion pour identifier le modèle "
                        "sélectionné et stocker ses artefacts dans MinIO, "
                        "afin de permettre son chargement par FastAPI."
                    ),
                    "image": "mlflow_minio_champion.png"
                }
            }
            contenu = contenus[choix]
            st.markdown(
                f"<div style='font-size:17px; line-height:1.5;'>"
                f"<strong>{contenu['titre']} :</strong> "
                f"{contenu['description']}"
                f"</div>",
                unsafe_allow_html=True
            )

            # Une seule image affichée à la fois via radio
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
            image_path = ( Path(__file__).resolve().parent / "images" / contenu["image"])

            if image_path.is_file():
                st.image(str(image_path), width=1000)
            else:
                st.warning(f"Capture introuvable : {contenu['image']}")
        
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

##################################################################################
# SOUTENANCE — ONGLET 4 : DÉPLOIEMENT AVEC DOCKER COMPOSE ET API FASTAPI
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[3]:
    with st.container(key="soutenance_deploiement_api"):

        st.markdown(
            """
            <h2 class="titre-onglet-4">4. Déploiement et API</h2>
            <hr style="border:0; border-top:1px solid #D3D9E4; margin:4px 0 12px;height:18px;">
            """,
            unsafe_allow_html=True
        )
        # OBJECTIF
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong> Objectif :</strong> "
            "Déployer les composants de la plateforme dans un environnement "
            "reproductible avec Docker Compose et rendre le modèle Champion "
            "accessible via une API FastAPI sécurisée."
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        # DÉPLOIEMENT AVEC DOCKER COMPOSE
        st.markdown("### 🐳 Déploiement avec Docker Compose")
        with st.container(key="soutenance_docker_blocs"):

            blocs_docker = [
                (
                    "Conteneurisation",
                    "Services exécutés dans des conteneurs distincts, "
                    "avec des environnements et dépendances adaptés.",
                ),
                (
                    "Coordination des services",
                    "Configuration centralisée, dépendances, "
                    "contrôles de santé et démarrage coordonné.",
                ),
                (
                    "Réseaux et persistance",
                    "Communication interne sur un réseau Docker commun "
                    "et conservation des données via des volumes persistants.",
                ),
            ]

            colonnes = st.columns(3, gap="small")
            for col, (titre, description) in zip(colonnes, blocs_docker):
                with col:
                    st.markdown(
                        "<div style='background:#E6F2FF;"
                        "border-radius:12px;"
                        "padding:10px 16px;"
                        "min-height:90px;"
                        "box-sizing:border-box;"
                        "font-size:16px;"
                        "line-height:1.4;"
                        "color:#345C7A;'>"
                        f"<strong style='color:#173C60;'>{titre}</strong>"
                        f"<div style='margin-top:4px;'>{description}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                    
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

        # FASTAPI ET SÉCURISATION DES ACCÈS
        st.markdown("### 🔐 FastAPI et sécurisation des accès")
        st.markdown(
            "<div style='padding-left:44px;"
            "font-size:17px;line-height:1.5;'>"
            "L'API expose le modèle Champion via une API dédiée aux prédictions immobilières et à la consultation des informations du modèle."
            "</div>",
            unsafe_allow_html=True
        )

        # Espace entre le texte et la capture Swagger
        st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)

        # Image API Prediction
        with st.container(key="soutenance_api_details"):

            image_swagger = ( Path(__file__).resolve().parent / "images" / "api_prediction.png" )
            if image_swagger.is_file():
                col_gauche, col_centre, col_droite = st.columns([1, 10, 1])
                with col_centre:
                    st.image(str(image_swagger), use_container_width=True)
                    st.caption("API de prédiction")
            else:
                st.warning(
                    "Capture Swagger introuvable : images/api_prediction.png"
                )
        
        # SÉCURITÉ OAUTH2 / JWT — BLOC DE SYNTHÈSE
        st.markdown(
            """
            <div class="securite-api">
                <div class="securite-api-titre">🔐 Sécurité mise en place — OAuth2 / JWT</div>
                <div class="securite-api-etapes">
                    <div class="securite-api-etape">
                        <strong>1. Authentification</strong>
                        <div class="securite-api-description">Identifiants via /token</div>
                    </div>
                    <div class="securite-api-etape">
                        <strong>2. Jeton JWT</strong>
                        <div class="securite-api-description">Token transmis à l'API</div>
                    </div>
                    <div class="securite-api-etape">
                        <strong>3. Contrôle des droits</strong>
                        <div class="securite-api-description">Vérification des rôles</div>
                    </div>
                    <div class="securite-api-etape">
                        <strong>4. Accès autorisé</strong>
                        <div class="securite-api-description">Exécution de la requête</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

##################################################################################
# SOUTENANCE — ONGLET 5 : CI/CD ET TESTS
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[4]:
    with st.container(key="soutenance_cicd"):

        st.markdown(
            """
            <h2 class="titre-soutenance">5. CI/CD et tests</h2>
            <hr style="border:0;border-top:1px solid #D3D9E4;margin:4px 0 12px;height:18px;">
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            "<div class='cicd-objectif'>"
            "<strong>Objectif :</strong> Automatiser les vérifications du code, "
            "les tests et la publication des images Docker afin de fiabiliser "
            "l'évolution de la plateforme MLOps."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("### ⚙️ Intégration et déploiement continus")
        col_ci, col_release = st.columns(2, gap="small")

        with col_ci:
            st.markdown(
                """
                <div class="cicd-bloc cicd-ci">
                    <div class="cicd-titre">✅ CI — Intégration continue</div>
                    <div class="cicd-declenchement">Déclenchement : push / pull request</div>
                    <div class="cicd-etapes">
                        <strong>1. Flake8 :</strong> analyse statique et détection des erreurs du code Python.
                    </div>
                    <div class="cicd-etape">
                        <strong>2. Pytest :</strong> exécution des tests automatisés.
                    </div>
                    <div class="cicd-etape">
                        <strong>3. Docker Build :</strong> construction des images.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_release:
            st.markdown(
                """
                <div class="cicd-bloc cicd-release">
                    <div class="cicd-titre">📦 CD — déploiement continu</div>
                    <div class="cicd-declenchement">Déclenchement : push sur master</div>
                    <div class="cicd-etapes">
                       <strong>1. Contrôles qualité :</strong> vérification du code avec Flake8 et tests automatisés avec Pytest.
                    </div>
                    <div class="cicd-etape">
                        <strong>2. DockerHub :</strong> authentification via GitHub Secrets.
                    </div>
                    <div class="cicd-etape">
                        <strong>3. docker build et Push:</strong> construction et publication des images sur DockerHub.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown(
            "<div class='cicd-publication'>"
            "<strong>Publication des images sur DockerHub."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        image_dockerhub = Path(__file__).resolve().parent / "images" / "dockerhub.png"
        if image_dockerhub.is_file():
            col_gauche, col_centre, col_droite = st.columns([1, 8, 1])
            with col_centre:
                st.image(str(image_dockerhub), use_container_width=True)
                # st.caption("Images Docker publiées sur DockerHub")
        else:
            st.warning("Capture DockerHub introuvable : images/dockerhub.png")

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        st.markdown("### 🔍 Tests automatisés avec Pytest")
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        tests = [
            (
                "Validation des données",
                "Rejet des surfaces nulles ou négatives et des logements sans pièce."
            ),
            (
                "API et sécurité",
                "Disponibilité de /health (HTTP 200) et refus d'une prédiction sans authentification (HTTP 401)."
            ),
            (
                "Gestion des modèles MLflow",
                "Vérification de l'attribution initiale de l'alias champion à la version V1."
            )
        ]

        colonnes_tests = st.columns(3, gap="small")
        for col, (titre, description) in zip(colonnes_tests, tests):
            with col:
                st.markdown(
                    "<div class='pytest-bloc'>"
                    f"<strong class='pytest-titre'>{titre}</strong>"
                    f"<div class='pytest-description'>{description}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

##################################################################################
# SOUTENANCE — ONGLET 6 : AUTOMATISATION AVEC AIRFLOW
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[5]:
    with st.container(key="soutenance_airflow"):

        st.markdown(""" <h2 class="titre-soutenance">6. Automatisation avec Airflow</h2>
            <hr style="border:0; border-top:1px solid #D3D9E4; margin:4px 0 12px; height:18px;">
            """, unsafe_allow_html=True )
        # OBJECTIF
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong>Objectif :</strong> "
            "Automatiser et orchestrer les étapes du pipeline MLOps "
            "avec Airflow."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        # PIPELINE MLOPS
        st.markdown("### ⚙️ Orchestration du pipeline MLOps")

        etapes_airflow = [
            (
                "Préparation des données",
                "Collecte et transformation des données immobilières."
            ),
            (
                "Entraînement",
                "Exécution du pipeline d'entraînement du modèle."
            ),
            (
                "Suivi MLflow",
                "Enregistrement des expérimentations et des modèles."
            ),
            (
                "Évaluation",
                "Contrôle des performances du modèle entraîné."
            )
        ]

        colonnes = st.columns(4, gap="small")

        for col, (titre, description) in zip(colonnes, etapes_airflow):
            with col:
                st.markdown(
                    "<div class='airflow-bloc'>"
                    f"<strong>{titre}</strong>"
                    f"<div class='airflow-description'>{description}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)

        # CAPTURE AIRFLOW
        st.markdown("### 🔄 DAG Airflow et suivi des exécutions")

        st.markdown(
            "<div style='padding-left:44px;font-size:17px;line-height:1.5;'>"
            "Airflow organise les traitements sous forme de DAGs, "
            "gère les dépendances entre les tâches et permet "
            "de suivre leur état d'exécution."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)

        image_airflow = (Path(__file__).resolve().parent / "images" / "airflow_dag.png")

        if image_airflow.is_file():
            col_gauche, col_centre, col_droite = st.columns([1, 10, 1])

            with col_centre:
                st.image(str(image_airflow), use_container_width=True)
                st.caption("Pipeline MLOps orchestré avec Airflow")
        else:
            st.warning("Capture introuvable : images/airflow_dag.png")
##################################################################################
# SOUTENANCE — ONGLET 7 : MONITORING ET DRIFT
##################################################################################
elif role == "admin" and page_active == PAGES_SOUTENANCE[6]:
    with st.container(key="soutenance_monitoring"):

        st.markdown(
            """
            <h2 class="titre-soutenance">7. Monitoring et drift</h2>
            <hr style="border:0;border-top:1px solid #D3D9E4;
                       margin:4px 0 12px;height:18px;">
            """,
            unsafe_allow_html=True
        )

        # OBJECTIF
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong>Objectif :</strong> "
            "Surveiller les dérives des données, les performances du modèle "
            "et le fonctionnement des services de la plateforme MLOps."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        ################## EVIDENTLY — DÉTECTION DES DÉRIVES
        st.markdown("### 📊 Evidently — Détection des dérives")

        st.markdown(
            "<div style='padding-left:44px;font-size:17px;line-height:1.5;'>"
            "Evidently permet d'analyser les écarts entre les données de référence "
            "et les nouvelles données afin de détecter les dérives susceptibles "
            "d'affecter la fiabilité des prédictions."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # IMAGE 1 — EVIDENTLY
        image_evidently = (
            Path(__file__).resolve().parent / "images" / "evidently.png"
        )

        if image_evidently.is_file():
            col_gauche, col_centre, col_droite = st.columns([1, 10, 1])

            with col_centre:
                st.image(str(image_evidently), use_container_width=True)
                st.caption("Rapport de monitoring Evidently")
        else:
            st.warning("Capture introuvable : images/evidently.png")

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # IMAGE 2 — EVIDENTLY DRIFT
        image_evidently_drift = (
            Path(__file__).resolve().parent / "images" / "evidently_drift.png"
        )

        if image_evidently_drift.is_file():
            col_gauche, col_centre, col_droite = st.columns([1, 10, 1])

            with col_centre:
                st.image(str(image_evidently_drift), use_container_width=True)
                st.caption("Analyse des dérives des données avec Evidently")
        else:
            st.warning("Capture introuvable : images/evidently_drift.png")

        st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)

        ################## PROMETHEUS / GRAFANA 
        st.markdown("### 📈 Prometheus et Grafana — Supervision")

        st.markdown(
            "<div style='padding-left:44px;font-size:17px;line-height:1.5;'>"
            "Prometheus collecte les métriques techniques des services, "
            "tandis que Grafana permet de les visualiser dans des tableaux "
            "de bord pour suivre le fonctionnement de la plateforme."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        # IMAGE 3 — GRAFANA
        image_grafana = (
            Path(__file__).resolve().parent / "images" / "grafana.png"
        )

        if image_grafana.is_file():
            col_gauche, col_centre, col_droite = st.columns([1, 10, 1])

            with col_centre:
                st.image(str(image_grafana), use_container_width=True)
                st.caption("Tableau de bord de supervision Grafana")
        else:
            st.warning("Capture introuvable : images/grafana.png")

##################################################################################
# SOUTENANCE — ONGLET 8 : BILAN ET PERSPECTIVES
##################################################################################

elif role == "admin" and page_active == PAGES_SOUTENANCE[7]:
    with st.container(key="soutenance_bilan"):

        st.markdown(
            """
            <h2 class="titre-soutenance">8. Bilan et perspectives</h2>
            <hr style="border:0;border-top:1px solid #D3D9E4;
                       margin:4px 0 12px;height:18px;">
            """,
            unsafe_allow_html=True
        )

        # BILAN GLOBAL
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong>Bilan :</strong> "
            "Une plateforme MLOps conteneurisée intégrant le versionnement du modèle, "
            "l'automatisation des traitements, la mise à disposition des prédictions "
            "et leur supervision."
            "</div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        # SÉCURITÉ, RGPD ET GOUVERNANCE
        st.markdown("### 🔎 Sécurité, RGPD et gouvernance")

        blocs_bilan = [
            (
                "🔐 Sécurité et RGPD",
                [
                    "Authentification OAuth2/JWT et gestion des rôles admin/user.",
                    "Limitation de l'exposition des ports Docker.",
                    "Exploitation des données publiques DVF/INSEE."
                ],
                [
                    "Délimitation des accès et isolation des réseaux Docker.",
                    "Sécurisation des accès administrateur par tunnel SSH.",
                    "Définition des durées de conservation des données."
                ]
            ),
            (
                "📋 Gouvernance et traçabilité",
                [
                    "Versionnement des données avec DVC.",
                    "Suivi des modèles et expérimentations avec MLflow.",
                    "Identification des prédictions par Request ID."
                ],
                [
                    "Mise en place d'une interface d'audit des prédictions.",
                    "Définition de seuils d'alerte sur les performances et les dérives.",
                ]
            )
        ]

        # BLOCS HORIZONTAUX AVEC LISTES À PUCES
        for titre, realisations, perspectives in blocs_bilan:

            liste_realisations = "".join(
                f"<li>{element}</li>" for element in realisations
            )

            liste_perspectives = "".join(
                f"<li>{element}</li>" for element in perspectives
            )

            st.markdown(
                f'<div class="bilan-bloc">'
                f'<div class="bilan-titre">{titre}</div>'
                f'<div class="bilan-contenu">'
                f'<div>'
                f'<strong>Déjà réalisé</strong>'
                f'<ul class="bilan-liste">{liste_realisations}</ul>'
                f'</div>'
                f'<div>'
                f'<strong>Perspectives</strong>'
                f'<ul class="bilan-liste">{liste_perspectives}</ul>'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        # PERSPECTIVES GLOBALES
        st.markdown(
            "<div style='font-size:17px;line-height:1.5;'>"
            "<strong>Perspectives globales :</strong>"
            "<div style='margin-top:8px;'>"
            "<strong>- Sécurité et gouvernance :</strong> "
            "Renforcer la sécurité, la traçabilité et la gouvernance des données "
            "pour préparer une exploitation fiable et maîtrisée en production."
            "</div>"
            "<div style='margin-top:8px;'>"
            "<strong>- Infrastructure et déploiement :</strong> "
            "Automatiser le déploiement sur un environnement cloud "
            "et envisager une orchestration avec Kubernetes pour améliorer "
            "la scalabilité, la disponibilité et la gestion des services."
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

##################################################################################
# APPLICATION MÉTIER — ONGLET 1 : ESTIMATION (Prediction API)
##################################################################################
if page_active == "🏠 Estimation":
    st.subheader("Estimer la valeur d'un logement")
    st.write("Indiquez les caractéristiques du bien pour obtenir le prix estimé.")

    # Les sélections dynamiques restent hors du formulaire afin que les quartiers et le champ terrain réagissent immédiatement.
    @st.cache_data(ttl=3600)
    def charger_quartiers(code_commune):
        reponse = requests.get(
            f"{PREDICTION_API_URL}/quartiers/{code_commune}", timeout=25
        )
        reponse.raise_for_status()
        return reponse.json()

    def reinitialiser_estimation():
        for cle in (
            "dernier_resultat", "dernier_logement", "duree_prediction",
            "code_reponse", "commune_estimee",
        ):
            st.session_state.pop(cle, None)

    def changer_commune():
        # Vider le quartier sélectionné
        st.session_state.pop("quartier_estimation", None)

        # Forcer la création d'un nouveau champ Quartier
        st.session_state["version_quartier"] = (
            st.session_state.get("version_quartier", 0) + 1
        )
        # Effacer l'ancienne estimation
        reinitialiser_estimation()

    # Un seul bloc blanc pour tous les filtres et le bouton.
    with st.container(border=True, key="bloc_filtres_estimation"):
        col_type, col_commune, col_quartier = st.columns(
            [1.8, 3, 3], gap="small"
        )

        with col_type:
            type_local = st.radio(
                "Type de logement",
                ["Appartement", "Maison"],
                horizontal=True,
                key="type_local_estimation",
                on_change=reinitialiser_estimation,
            )

        with col_commune:
            commune_selectionnee = st.selectbox(
                "Commune (code INSEE)",
                options=OPTIONS_COMMUNES,
                index=OPTIONS_COMMUNES.index("69383 — Lyon 3e arrondissement"),
                help="Sélectionnez une commune du Rhône ou un arrondissement de Lyon.",
                key="commune_estimation",
                on_change=changer_commune,
            )

        code_commune = commune_selectionnee.split(" — ", 1)[0]

        try:
            quartiers = charger_quartiers(code_commune)
            erreur_quartiers = None
        except (requests.RequestException, ValueError) as erreur:
            quartiers = []
            erreur_quartiers = str(erreur)

        noms_quartiers = {
            quartier["code_quartier"]: quartier["nom_quartier"]
            for quartier in quartiers
        }

        with col_quartier:
            code_quartier = st.selectbox(
                "Quartier ",  #(IRIS)
                options=list(noms_quartiers),
                format_func=lambda code: noms_quartiers[code],
                index=None,
                placeholder="Sélectionnez un quartier",
                key=f"quartier_estimation_{st.session_state.get('version_quartier', 0)}",
                disabled=not bool(quartiers),
                on_change=reinitialiser_estimation,
            )

        if erreur_quartiers:
            st.error("Impossible de charger les quartiers depuis l'API de prédiction.")
        elif not quartiers:
            st.warning("Aucun quartier disponible pour cette commune.")

        col_surface, col_pieces = st.columns(2, gap="small")
        with col_surface:
            surface = st.number_input(
                "Surface habitable (m²)", min_value=1.0, value=70.0, step=1.0
            )
        with col_pieces:
            pieces = st.number_input("Nombre de pièces", min_value=1, value=3)

        if type_local == "Maison":
            surface_terrain = st.number_input(
                "Surface du terrain (m²) — facultative",
                min_value=0.0,
                value=None,
                step=10.0,
                placeholder="Ex. 300",
                help="Laissez vide si la surface du terrain est inconnue.",
            )
        else:
            surface_terrain = 0.0

        estimer = st.button(
            "🔎 Estimer ce bien", type="primary", width="content",
            disabled=(code_quartier is None or not quartiers),
        )

    if estimer:
        reinitialiser_estimation()

        logement = {
            "code_commune": code_commune,
            "code_quartier": code_quartier,
            "type_local": type_local,
            "surface_reelle_bati": float(surface),
            "nombre_pieces_principales": int(pieces),
            "surface_terrain": (
                float(surface_terrain) if surface_terrain is not None else None
            ),
        }

        try:
            with st.spinner("Calcul de l'estimation..."):
                debut = time.perf_counter()
                reponse = requests.post(
                    f"{PREDICTION_API_URL}/predict/",
                    json=logement,
                    headers={"Authorization": f"Bearer {st.session_state['token']}"},
                    timeout=60,
                )
                duree = time.perf_counter() - debut

            st.session_state["code_reponse"] = reponse.status_code
            st.session_state["duree_prediction"] = duree

            if reponse.status_code == 200:
                st.session_state["dernier_resultat"] = reponse.json()
                st.session_state["dernier_logement"] = logement
                st.session_state["commune_estimee"] = commune_selectionnee
            elif reponse.status_code == 401:
                for cle in ("token", "utilisateur", "role", "page_active", "retour_soutenance"):
                    st.session_state.pop(cle, None)
                st.session_state["session_expiree"] = True
                st.rerun()
            elif reponse.status_code == 403:
                st.error("Vous n'êtes pas autorisé à effectuer une prédiction.")
            elif reponse.status_code == 422:
                st.error("Les informations du logement sont invalides.")
            elif reponse.status_code == 500:
                st.error(
                    "Impossible d'estimer ce logement. "
                    "Vérifiez les caractéristiques saisies."
                )
            else:
                st.error(f"Erreur de prédiction (HTTP {reponse.status_code}).")
        except (requests.RequestException, ValueError):
            st.error("Impossible d'obtenir une estimation auprès de l'API.")

    resultat = st.session_state.get("dernier_resultat")
    logement = st.session_state.get("dernier_logement")
    if resultat is not None and logement is not None:
        st.divider()
        st.subheader("📊 Résultat de l'estimation")
        prix_m2 = resultat.get("prix_m2_estime")
        prix_total = resultat.get("valeur_totale_estimee")
        if prix_m2 is not None and prix_total is not None:
            st.success("Estimation réalisée avec succès !")
            c1, c2 = st.columns(2)
            c1.metric("Prix estimé au m²", euros(prix_m2, 2))
            c2.metric("Valeur totale estimée", euros(prix_total))
            with st.container(key="details_estimation"):
                if resultat.get("request_id"):
                    st.caption("Request ID à conserver pour transmettre le prix réel :")
                    st.code(resultat["request_id"], language=None)
                    st.caption(
                        "La journalisation est effectuée en arrière-plan. "
                        "Cet identifiant ne garantit pas que l'enregistrement a réussi."
                    )
                st.caption(
                    f"{logement['type_local']} • {logement['surface_reelle_bati']:g} m² "
                    f"• {logement['nombre_pieces_principales']} pièces "
                    f"• Commune {st.session_state.get('commune_estimee', logement['code_commune'])} "
                    f"• Quartier {noms_quartiers.get(logement['code_quartier'], logement['code_quartier'])}"
                )
        else:
            st.warning("La réponse de l'API ne contient pas les prix attendus.")
            st.json(resultat)
##################################################################################
# ONGLET 2 — Données du modèle Champion enregistrées dans MLflow.
##################################################################################
if page_active == "📊 Modèle champion et performance" and role == "admin":
    st.subheader("📊 Modèle Champion MLflow")
    st.write( "Consultez la version actuellement associée à l'alias **champion** " "et les métriques enregistrées lors de  l'entraînement." )

    if st.button("🔄 Actualiser depuis MLflow", key="actualiser_champion", type="primary"):
        st.session_state.pop("infos_modele", None)
        try:
            with st.spinner("Lecture des informations du Champion..."):
                reponse = requests.get( f"{PREDICTION_API_URL}/model-info", headers={ "Authorization": f"Bearer {st.session_state['token']}" }, timeout=10, )

            if reponse.status_code == 200:
                st.session_state["infos_modele"] = reponse.json()
            elif reponse.status_code == 401:
                for cle in ("token", "utilisateur", "role", "page_active", "retour_soutenance"):
                    st.session_state.pop(cle, None)
                st.session_state["session_expiree"] = True
                st.rerun()
            elif reponse.status_code == 403:
                st.error("Accès refusé aux informations du modèle.")
            elif reponse.status_code == 503:
                st.error("MLflow est indisponible ou aucun Champion n'est défini.")
            else:
                st.error(f"Erreur de lecture du modèle (HTTP {reponse.status_code}).")

        except (requests.RequestException, ValueError):
            st.error("Impossible de récupérer les informations du modèle.")

    infos = st.session_state.get("infos_modele")
    if infos:
        st.markdown("#### Modèle enregistré")
        st.write(f"**Nom :** {infos['modele']}")
        col_version, col_alias = st.columns(2)
        col_version.metric("Version Champion", f"V{infos['version']}")
        col_alias.metric("Alias MLflow", infos["alias"])

        st.markdown("#### Performances enregistrées dans MLflow")
        metriques = { nom.lower(): valeur for nom, valeur in (infos.get("metrics") or {}).items() }

        col1, col2, col3 = st.columns(3)
        col1.metric( "MAE", f"{euros(metriques['mae'], 2)}/m²" if "mae" in metriques else "Non disponible", )
        col2.metric( "RMSE", f"{euros(metriques['rmse'], 2)}/m²" if "rmse" in metriques else "Non disponible", )
        col3.metric( "R²", f"{metriques['r2']:.3f}".replace(".", ",") if "r2" in metriques else "Non disponible", )
        st.caption("Métriques du run MLflow associé au Champion.")

        if infos.get("run_id"):
            st.caption(f"Run MLflow : {infos['run_id']}")
    else:
        st.info("Cliquez sur « Actualiser depuis MLflow » pour afficher le Champion.")

##################################################################################
# ONGLET 3 — Retour du prix réel après une vente ou un achat.
##################################################################################
if page_active == "💰 Transaction réalisée":
    st.subheader("Enregistrer le prix réel d'une transaction")
    st.write(
        "Renseignez le prix réel de la transaction afin de comparer les estimations "
        "aux valeurs observées et de suivre les performances du modèle avec Evidently."
    )

    with st.form("form_prix_reel"):
        # ligne 1 — Identifiant de la prédiction
        col_label, col_input = st.columns(
            [1, 2.6],
            gap="small",
            vertical_alignment="center"
        )

        with col_label:
            st.html(
                '<div style="font-family:inherit; font-size:14px; '
                'font-weight:400; line-height:1.5;">'
                'Identifiant de la prédiction (Request ID)'
                '</div>'
            )

        with col_input:
            request_id = st.text_input("Identifiant", placeholder="Ex. : 8f4a2c91-...", label_visibility="collapsed"            )

        # ligne 2 — Prix réel de la transaction
        col_label2, col_input2 = st.columns( [1, 2.6], gap="small", vertical_alignment="center")

        with col_label2:
            st.html(
                '<div style="font-family:inherit; font-size:14px; '
                'font-weight:400; line-height:1.5;">'
                'Prix réel de la transaction (€)'
                '</div>'
            )

        with col_input2:
            prix_reel = st.number_input("Prix réel", min_value=0.0, value=None, step=1000.0,
                format="%.2f", placeholder="Ex. : 250000", label_visibility="collapsed")

        transmettre = st.form_submit_button( "Transmettre le prix réel", type="primary")

    if transmettre:
        if not request_id.strip() or prix_reel is None or prix_reel <= 0:
            st.warning("Veuillez renseigner les deux champs.")
        else:
            try:
                reponse = requests.put(
                    f"{PREDICTION_API_URL}/predictions/{request_id.strip()}/prix-reel",
                    json={"prix_total_reel": prix_reel},
                    headers={"Authorization": f"Bearer {st.session_state['token']}"},
                    timeout=15,
                )
                if reponse.status_code == 200:
                    st.success("Prix réel enregistré pour cette prédiction.")
                elif reponse.status_code == 401:
                    for cle in ("token", "utilisateur", "role", "page_active", "retour_soutenance"):
                        st.session_state.pop(cle, None)
                    st.session_state["session_expiree"] = True
                    st.rerun()
                elif reponse.status_code == 403:
                    st.error("Vous n'êtes pas autorisé à transmettre un prix réel.")
                elif reponse.status_code in (404, 409):
                    st.error(reponse.json()["detail"])
                elif reponse.status_code == 422:
                    st.error("Request ID invalide ou prix réel non positif ou non fini.")
                else:
                    st.error("Impossible d'enregistrer le prix réel. Réessayez plus tard.")
            except (requests.RequestException, ValueError, KeyError):
                st.error("Impossible de transmettre le prix réel à l'API.")
