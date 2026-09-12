"""Moteur de traitement : normalisation, classification, scoring, dates limites.

Toutes les fonctions sont pures (aucun réseau, aucune base) : elles sont
testées unitairement (tests/test_traitement.py) et rejouables.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def sans_accents(texte: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def normaliser_texte(texte: str) -> str:
    """Minuscules, sans accents, espaces réduits — pour comparaisons et recherche."""
    if not texte:
        return ""
    texte = sans_accents(texte).lower()
    return re.sub(r"\s+", " ", texte).strip()


def normaliser_titre(titre: str) -> str:
    """Empreinte de titre : lettres/chiffres uniquement (dédoublonnage)."""
    t = normaliser_texte(titre)
    return re.sub(r"[^a-z0-9]", "", t)


def normaliser_url(url: str) -> str:
    """URL canonique : protocole et www ignorés, paramètres de suivi retirés."""
    if not url:
        return ""
    url = url.strip()
    morceaux = urlsplit(url)
    netloc = morceaux.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parametres_purs = [
        (k, v)
        for k, v in parse_qsl(morceaux.query)
        if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_", "ref"))
    ]
    requete = urlencode(parametres_purs)
    return f"{netloc}{morceaux.path.rstrip('/')}" + (f"?{requete}" if requete else "")


# ---------------------------------------------------------------------------
# Classification par domaine et scoring de pertinence
# ---------------------------------------------------------------------------

def _index_mots_cles(config_domaine: dict) -> list[tuple[str, int]]:
    """[(mot-clé normalisé, poids fort=3|moyen=1)], trié par longueur décroissante.

    Le tri garantit qu'un mot-clé long (« évaluation finale ») neutralise la
    portion de texte avant qu'un mot-clé court (« évaluation ») ne soit testé :
    aucun double comptage.
    """
    couples: list[tuple[str, int]] = []
    for mc in config_domaine.get("mots_cles", {}).get("fort", []):
        couples.append((normaliser_texte(mc), 3))
    for mc in config_domaine.get("mots_cles", {}).get("moyen", []):
        couples.append((normaliser_texte(mc), 1))
    return sorted(couples, key=lambda c: -len(c[0]))


def _points(texte: str, index: list[tuple[str, int]], mult: int) -> int:
    """Points marqués par un texte selon un index de mots-clés ; chaque
    mot-clé ne compte qu'une fois (portion remplacée après match)."""
    total = 0
    for mot, poids in index:
        if mot and mot in texte:
            total += poids * mult
            texte = texte.replace(mot, "§")
    return total


def classer(
    titre: str,
    resume: str,
    config: dict,
    domaines_defaut: list[str] | None = None,
    priorite_source: int = 3,
    date_publication: str | None = None,
) -> tuple[dict[str, int], int]:
    """Classe un item par domaine et calcule son score de pertinence global.

    Retourne ({domaine: score_local}, score_global 0-100).
    """
    pond = config.get("ponderations", {})
    seuil = config.get("seuils", {}).get("attribution", 3)
    titre_n, resume_n = normaliser_texte(titre), normaliser_texte(resume or "")

    scores: dict[str, int] = {}
    for code, config_domaine in config.get("domaines", {}).items():
        index = _index_mots_cles(config_domaine)
        s = _points(titre_n, index, pond.get("titre", 3))
        s += _points(resume_n, index, pond.get("resume", 1))
        if s > 0:
            scores[code] = s

    # Domaines rattachés d'office par la source
    for code in domaines_defaut or []:
        if code not in scores:
            scores[code] = seuil  # score plancher = rattaché

    # Score global = meilleur score local + bonus source + bonus fraîcheur
    score = max(scores.values(), default=0)
    score += pond.get("bonus_source", 2) * priorite_source
    try:
        if date_publication:
            dp = datetime.fromisoformat(date_publication.replace("Z", "+00:00"))
            age = (datetime.now(dp.tzinfo) - dp).days
            if 0 <= age <= 7:
                score += pond.get("bonus_recence", 8)
    except (ValueError, TypeError):
        pass

    return scores, min(score, config.get("seuils", {}).get("score_max", 100))


def rattacher_domaines(scores: dict[str, int], config: dict) -> dict[str, int]:
    """Ne conserve que les domaines dont le score local atteint le seuil."""
    seuil = config.get("seuils", {}).get("attribution", 3)
    return {c: s for c, s in scores.items() if s >= seuil}


# ---------------------------------------------------------------------------
# Extraction des dates limites (heuristique)
# ---------------------------------------------------------------------------

MOIS_FR = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}
MOIS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "decembre": 12,
}
MOIS_COURTS = {
    "jan": 1, "feb": 2, "fev": 2, "mar": 3, "avr": 4, "apr": 4, "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "juil": 7, "jul": 7, "aout": 8, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

MOTS_CONTEXTE = [
    "cloture", "deadline", "au plus tard", "date limite", "remise des offres",
    "remise des propositions", "closing date", "submission of", "soumission",
    "before", "due", "expiration", "closes",
]

# Motifs : ISO, 12/09/2026, 12-09-26, 12 septembre 2026, September 12, 2026,
#          12-Sep-26, 12 Sep 2026 (formats UNDP : "Application Deadline: 12-Jan-26")
MOTIF_ISO = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
MOTIF_SLASH = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
MOTIF_MOIS_FR = re.compile(
    r"\b(\d{1,2})(?:er)?\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|"
    r"septembre|octobre|novembre|decembre)\s+(20\d{2})\b", re.IGNORECASE)
MOTIF_MOIS_EN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b", re.IGNORECASE)
MOTIF_JOUR_MOIS_EN = re.compile(
    r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+(20\d{2})\b", re.IGNORECASE)
MOTIF_COURT = re.compile(
    r"\b(\d{1,2})[- ](jan|feb|fev|mar|avr|apr|mai|may|jun|juin|jul|juil|aout|aug|"
    r"sep|oct|nov|dec)[a-z]*[- ](\d{2,4})\b", re.IGNORECASE)


def _trouver_dates(texte: str) -> list[tuple[int, date, int]]:
    """Toutes les dates du texte : [(position, date, fiabilité)]."""
    texte_n = sans_accents(texte.lower())
    trouvees: list[tuple[int, date, int]] = []

    def _ajouter(pos, annee, mois, jour, fiab):
        try:
            d = date(annee, mois, jour)
            if date(2000, 1, 1) <= d <= date(2100, 1, 1):
                trouvees.append((pos, d, fiab))
        except ValueError:
            pass

    for m in MOTIF_ISO.finditer(texte_n):
        _ajouter(m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3)), 3)
    for m in MOTIF_MOIS_FR.finditer(texte_n):
        _ajouter(m.start(), int(m.group(3)), MOIS_FR[m.group(2)], int(m.group(1)), 3)
    for m in MOTIF_MOIS_EN.finditer(texte_n):
        _ajouter(m.start(), int(m.group(3)), MOIS_EN[m.group(1)], int(m.group(2)), 3)
    for m in MOTIF_JOUR_MOIS_EN.finditer(texte_n):
        _ajouter(m.start(), int(m.group(3)), MOIS_EN[m.group(2)], int(m.group(1)), 3)
    for m in MOTIF_COURT.finditer(texte_n):
        annee = int(m.group(3))
        annee += 2000 if annee < 100 else 0
        mois = MOIS_COURTS.get(m.group(2)[:3].lower())
        if mois:
            _ajouter(m.start(), annee, mois, int(m.group(1)), 2)
    for m in MOTIF_SLASH.finditer(texte_n):
        j, mois, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a += 2000 if a < 100 else 0
        if mois <= 12 and j <= 31:  # format jour/mois/année
            _ajouter(m.start(), a, mois, j, 2)
        elif j <= 12:  # format américain mois/jour/année
            _ajouter(m.start(), a, j, mois, 1)

    # retire les doublons de position (deux motifs captant la même date)
    vues, uniques = set(), []
    for pos, d, f in sorted(trouvees):
        cle = d.isoformat()
        if cle not in vues:
            vues.add(cle)
            uniques.append((pos, d, f))
    return uniques


def extraire_date_limite(
    texte: str, aujourdhui: date | None = None, date_publication: str | None = None
) -> str | None:
    """Estime la date limite de remise des offres à partir du titre et du résumé.

    Heuristique (documentée comme telle) :
      1. priorité aux dates proches d'un mot de contexte ("clôture", "deadline"…) ;
      2. sinon la première date postérieure à aujourd'hui (les avis annoncent
         des échéances futures) ;
      3. fenêtre de validité : [aujourd'hui - 30 j ; aujourd'hui + 1 an].
    """
    if not texte:
        return None
    ajd = aujourdhui or date.today()
    fenetre_min = ajd - timedelta(days=30)
    fenetre_max = ajd + timedelta(days=365)
    texte_n = sans_accents(texte.lower())
    candidats = _trouver_dates(texte)

    plausibles = [(p, d, f) for p, d, f in candidats if fenetre_min <= d <= fenetre_max]
    if not plausibles:
        return None

    # 1) date précédée d'un mot de contexte à moins de 60 caractères
    for pos, d, f in plausibles:
        contexte = texte_n[max(0, pos - 60):pos]
        if any(m in contexte for m in MOTS_CONTEXTE):
            return d.isoformat()

    # 2) première date future
    futures = sorted((d for _, d, _ in plausibles if d >= ajd))
    if futures:
        return futures[0].isoformat()

    # 3) dernière date passée plausible (avis repris tardivement)
    return max(d for _, d, _ in plausibles).isoformat()


def duree_avant(date_iso: str | None) -> str:
    """Formate le délai restant avant une date limite (pour rapports/dashboard)."""
    if not date_iso:
        return "—"
    try:
        d = date.fromisoformat(date_iso[:10])
    except ValueError:
        return "—"
    delta = (d - date.today()).days
    if delta < 0:
        return "clôturé"
    if delta == 0:
        return "aujourd'hui !"
    if delta <= 7:
        return f"J-{delta}"
    return f"J-{delta}"
