"""Socle commun des connecteurs : requêtes HTTP polies et normalisation d'items."""

from __future__ import annotations

import requests

from ..traitement import normaliser_url

FORMAT_ITEM = {
    "source_id": str,
    "source_nom": str,
    "categorie": str,
    "titre": str,
    "url": str,
    "resume": str,
    "date_publication": str,  # ISO 8601 si disponible
}


class ErreurCollecte(Exception):
    """Erreur de collecte d'une source (réseau, parsing, quota…)."""


def telecharger(url: str, timeout: int = 20, user_agent: str = "", params: dict | None = None) -> str:
    """GET avec User-Agent identifiable et délai d'attente explicite."""
    entetes = {"User-Agent": user_agent or "Veille-Consultance-Madagascar/1.0"}
    try:
        reponse = requests.get(url, params=params, headers=entetes, timeout=timeout)
        reponse.raise_for_status()
        return reponse.text
    except requests.RequestException as e:
        raise ErreurCollecte(f"{type(e).__name__} : {e}") from e


def item_brut(
    source: dict, titre: str, url: str, resume: str = "", date_publication: str | None = None
) -> dict:
    """Construit un item brut normalisé à partir d'une source déclarée."""
    titre = (titre or "").strip()
    url = (url or "").strip()
    if not titre or not url:
        raise ErreurCollecte("Item sans titre ou sans URL — ignoré")
    return {
        "source_id": source["id"],
        "source_nom": source.get("nom", source["id"]),
        "categorie": source.get("categorie", ""),
        "titre": titre,
        "url": url,
        "url_norm": normaliser_url(url),
        "resume": (resume or "").strip(),
        "date_publication": date_publication,
    }
