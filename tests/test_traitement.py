"""Tests du moteur de traitement — exécution : python -m pytest tests/ -v"""

import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from veille import config, modele, traitement  # noqa: E402
from veille.collecteurs.rss import CollecteurRSS  # noqa: E402
from veille.collecteurs.reliefweb import CollecteurReliefWeb  # noqa: E402
from veille.collecteurs.html import CollecteurHTML  # noqa: E402

CFG = config.charger_domaines()
FIXTURES = RACINE / "demo" / "fixtures"


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def test_normaliser_texte():
    assert traitement.normaliser_texte("Évaluation À Mi-Parcours") == "evaluation a mi-parcours"
    assert traitement.normaliser_texte("  Collecte   de  données ") == "collecte de donnees"


def test_normaliser_url():
    a = traitement.normaliser_url("https://www.exemple.mg/avis/?utm_source=x&id=7")
    b = traitement.normaliser_url("http://exemple.mg/avis/?id=7")
    assert a == b == "exemple.mg/avis?id=7"


def test_normaliser_titre():
    assert traitement.normaliser_titre("Étude de marché — 2026 !") == traitement.normaliser_titre(
        "etude de marche 2026")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def test_classification_evaluation():
    scores, _ = traitement.classer(
        "Évaluation à mi-parcours du projet PFSR",
        "Le consultant conduira l'évaluation à mi-parcours conformément aux normes du Groupe Banque mondiale.",
        CFG, date_publication="2026-09-10T00:00:00Z")
    assert "evaluation_projet" in scores


def test_classification_collecte_donnees():
    scores, _ = traitement.classer(
        "Recrutement d'une société d'enquête pour la collecte de données",
        "Enquête auprès des ménages sur tablette, 2000 ménages, gestion des données CAPI.",
        CFG, date_publication="2026-09-10T00:00:00Z")
    assert "collecte_donnees" in scores


def test_classification_anglaise():
    scores, _ = traitement.classer(
        "Individual Consultant – Baseline study and impact evaluation",
        "The consultant will design the baseline survey and data collection protocols.",
        CFG)
    assert "evaluation_projet" in scores and "collecte_donnees" in scores


def test_classification_veille_economique():
    scores, _ = traitement.classer(
        "Madagascar : note de conjoncture économique",
        "La croissance du PIB ralentit, l'inflation se maintient au-dessus de 5 %.",
        CFG)
    assert "veille_economique" in scores


def test_classification_investissements():
    scores, _ = traitement.classer(
        "Baromètre EDBM : climat des affaires et guichet unique",
        "La réforme facilite la création d'entreprise et attire l'investissement privé.",
        CFG)
    assert "promotion_investissements" in scores


def test_classification_sans_domaine():
    scores, _ = traitement.classer(
        "Supply of office furniture",
        "RFQ for office furniture supply, delivery to Nairobi.", CFG)
    rattaches = traitement.rattacher_domaines(scores, CFG)
    assert "evaluation_projet" not in rattaches and "collecte_donnees" not in rattaches


def test_pas_de_double_comptage():
    """« évaluation finale » (fort) ne doit pas compter aussi « évaluation » (moyen)."""
    scores_un = traitement.classer("Évaluation finale du projet", "", CFG)[0]
    scores_deux = traitement.classer("Évaluation du projet", "", CFG)[0]
    assert scores_un["evaluation_projet"] > scores_deux["evaluation_projet"]


def test_domaines_defaut_source():
    scores, _ = traitement.classer(
        "Avis général de consultation", "Objet non précisé", CFG,
        domaines_defaut=["collecte_donnees"])
    rattaches = traitement.rattacher_domaines(scores, CFG)
    assert "collecte_donnees" in rattaches


def test_score_ordonne():
    fort = traitement.classer("Évaluation finale indépendante", "", CFG,
                              priorite_source=5, date_publication=None)[1]
    faible = traitement.classer("Fourniture de riz", "", CFG, priorite_source=1)[1]
    assert fort > faible


# ---------------------------------------------------------------------------
# Extraction des dates limites
# ---------------------------------------------------------------------------

AJD = date(2026, 9, 12)

def test_date_limite_iso():
    assert traitement.extraire_date_limite(
        "Deadline: 2026-10-03 pour le dépôt", aujourdhui=AJD) == "2026-10-03"

def test_date_limite_francaise():
    assert traitement.extraire_date_limite(
        "Les offres devront être remises au plus tard le 29 septembre 2026 à 10h00",
        aujourdhui=AJD) == "2026-09-29"

def test_date_limite_anglaise():
    assert traitement.extraire_date_limite(
        "Application Deadline: 3 October 2026", aujourdhui=AJD) == "2026-10-03"

def test_date_limite_format_undp():
    assert traitement.extraire_date_limite(
        "Application Deadline: 28-Sep-26", aujourdhui=AJD) == "2026-09-28"

def test_date_limite_slash():
    assert traitement.extraire_date_limite(
        "Date limite de soumission : 05/10/2026", aujourdhui=AJD) == "2026-10-05"

def test_date_limite_priorite_contexte():
    """Une date proche d'un mot de contexte prime sur une date antérieure."""
    assert traitement.extraire_date_limite(
        "Publication le 02/09/2026. Clôture : 21/10/2026", aujourdhui=AJD) == "2026-10-21"

def test_date_limite_hors_fenetre():
    assert traitement.extraire_date_limite(
        "Réunion tenue le 15 janvier 2020", aujourdhui=AJD) is None


# ---------------------------------------------------------------------------
# Dédoublonnage (modèle, base en mémoire)
# ---------------------------------------------------------------------------

def test_doublonnage():
    conn = modele.ouvrir(":memory:")
    item = {"source_id": "x", "source_nom": "X", "categorie": "c", "titre": "Évaluation finale du projet",
            "url": "https://exemple.mg/avis?utm_source=rss", "url_norm": "exemple.mg/avis",
            "titre_norm": "evaluationfinaleduprojet", "resume": "", "date_publication": None,
            "domaines": {}, "score": 10}
    assert modele.inserer_item(conn, item, "t1") == "nouveau"
    assert modele.inserer_item(conn, item, "t1") == "doublon_url"
    item2 = dict(item, url="https://autre.mg/avis", url_norm="autre.mg/avis")
    assert modele.inserer_item(conn, item2, "t1") == "doublon_titre"
    conn.close()


# ---------------------------------------------------------------------------
# Connecteurs (parsing des formats réels, sur échantillons)
# ---------------------------------------------------------------------------

def _source(source_id):
    return next(s for s in config.charger_sources() if s["id"] == source_id)


def test_parse_rss_undp_avec_filtre():
    contenu = (FIXTURES / "undp_pn.xml").read_text(encoding="utf-8")
    items = CollecteurRSS.parser(contenu, _source("undp_pn"))
    assert len(items) == 3  # 5 items, le filtre MADAGASCAR en garde 3
    assert all("MADAGASCAR" in (i["titre"] + i["resume"]).upper() for i in items)


def test_parse_reliefweb():
    contenu = (FIXTURES / "reliefweb_jobs.json").read_text(encoding="utf-8")
    items = CollecteurReliefWeb.parser(contenu, _source("reliefweb_jobs"))
    assert len(items) == 6
    assert items[0]["url"].startswith("https://reliefweb.int/")


def test_parse_html_fid():
    contenu = (FIXTURES / "fid_ao.html").read_text(encoding="utf-8")
    items = CollecteurHTML.parser(contenu, _source("fid_ao"))
    titres = " ".join(i["titre"] for i in items)
    assert len(items) == 4
    assert "évaluation à mi-parcours" in titres.lower()
