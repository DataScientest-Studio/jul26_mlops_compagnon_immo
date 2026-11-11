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

# CSS des interfaces
st.markdown("""
<style>
/* Arrière-plan de l'application */
.stApp {
    background:
        radial-gradient(circle at 88% 8%, rgba(255, 201, 190, 0.45), transparent 33%),
        radial-gradient(circle at 8% 35%, rgba(198, 221, 250, 0.65), transparent 36%),
        linear-gradient(135deg, #F6F9FE 0%, #F5F7FD 55%, #FFF8F4 100%);
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1220px;
    padding-top: 0.7rem;
    padding-bottom: 1rem;
}

/* Espacement compact en haut de la page */
.block-container h1 { font-size: 2rem; margin: 0; padding: 0; }
.block-container h2, .block-container h3 { margin-top: 0.25rem; padding-top: 0; }
.block-container [data-testid="stCaptionContainer"] { margin-top: 15px; margin-bottom: 10px; }
.block-container [data-testid="stVerticalBlock"] { gap: 0.55rem; }
.block-container [data-testid="stAlert"] { padding: 0.35rem 0.65rem; min-height: 0; }
.block-container hr { margin: 0.35rem 0; }
.stTabs [data-baseweb="tab-list"] { margin-bottom: 0.25rem; }
/* Conteneurs de saisie et métriques */
[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #E4EAF3;
    border-radius: 18px;
    padding: 12px 16px;
    box-shadow: 0 12px 30px rgba(32, 56, 93, 0.07);
}
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #E4EAF3;
    border-left: 4px solid #F16B5C;
    border-radius: 14px;
    padding: 10px 14px;
    box-shadow: 0 8px 20px rgba(32, 56, 93, 0.05);
}

/* Fond blanc pour l'ensemble des filtres de l'onglet Estimation */
.st-key-bloc_filtres_estimation {
    background: #FFFFFF !important;
    border: 1px solid #E4EAF3 !important;
    border-radius: 18px !important;
    padding: 14px 16px !important;
    box-shadow: 0 12px 30px rgba(32, 56, 93, 0.07) !important;
}

/* Onglets et boutons */
.stTabs [data-baseweb="tab-list"] { gap: 12px; }
.stTabs [data-baseweb="tab"] {
    background: rgba(255, 255, 255, 0.70);
    border-radius: 10px 10px 0 0;
    padding: 5px 12px;
}
.stTabs [aria-selected="true"] { color: #E75949; font-weight: 700; }
.stButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: #F16B5C;
    border-color: #F16B5C;
    color: white;
    border-radius: 10px;
}
.stButton button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
    background: #DE5446;
    border-color: #DE5446;
    color: white;
}
.st-key-btn_deconnexion button {
    margin-top: 15px;
}
</style>
""", unsafe_allow_html=True)


def euros(valeur, decimales=0):
    nombre = f"{float(valeur):,.{decimales}f}"
    return nombre.replace(",", " ").replace(".", ",") + " €"

def deconnecter():
    for cle in ( "token", "utilisateur", "dernier_resultat", "dernier_logement", "duree_prediction", "code_reponse", "etat_apis", "commune_estimee", "infos_modele", ):
        st.session_state.pop(cle, None)
    st.rerun()


# En-tête
st.title("🏠 Compagnon Immobilier")
st.caption("Estimation immobilière • Département du Rhône")
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
                st.session_state.pop("infos_modele", None)
                st.rerun()
            elif reponse.status_code in (400, 401):
                st.error("Identifiants incorrects.")               
            else:
                st.error(f"Erreur de connexion (HTTP {reponse.status_code}).")
        except (requests.RequestException, ValueError, KeyError):
            st.error("Impossible de contacter l'API de prédiction.")

    st.stop()

# Espace connecté
col_user, col_logout = st.columns([4, 1])
with col_user:
    st.success(f"Connecté : {st.session_state.get('utilisateur', '')}")
with col_logout:
    if st.button("Déconnexion", key="btn_deconnexion", use_container_width=True):
        deconnecter()

onglet_estimation, onglet_modele = st.tabs([ "🏠 Estimation", "📊 Modèle champion et performance" ])

##################################################################################
# ONGLET 1 — prédire à partir de la Prediction API
##################################################################################
with onglet_estimation:
    st.subheader("Estimer la valeur d'un logement")
    st.write("Indiquez les caractéristiques du bien pour obtenir le prix estimé.")

    # Les sélections dynamiques restent hors du formulaire afin que
    # les quartiers et le champ terrain réagissent immédiatement.
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
                st.session_state.pop("token", None)
                st.session_state.pop("utilisateur", None)
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
with onglet_modele:
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
                st.session_state.pop("token", None)
                st.session_state.pop("utilisateur", None)
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
