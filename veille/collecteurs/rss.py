"""Connecteur RSS / Atom (feedparser).

S'applique à toute source dont le type est `rss` (PNUD, BAD, presse…).
Le champ optionnel `filtre_inclut` ne conserve que les items mentionnant
la sous-chaîne demandée (ex. "MADAGASCAR" pour le flux mondial du PNUD).
"""

from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..traitement import normaliser_texte
from .base import ErreurCollecte, item_brut, telecharger


class CollecteurRSS:

    @staticmethod
    def recuperer(source: dict, timeout: int = 20, user_agent: str = "") -> str:
        url = source.get("url_flux") or source.get("url")
        if not url:
            raise ErreurCollecte("Source RSS sans URL")
        return telecharger(url, timeout=timeout, user_agent=user_agent)

    @staticmethod
    def parser(contenu: str, source: dict, limite: int = 40) -> list[dict]:
        flux = feedparser.parse(contenu)
        if flux.bozo and not flux.entries:
            raise ErreurCollecte(f"Flux illisible : {flux.bozo_exception}")

        filtre = normaliser_texte(source.get("filtre_inclut", "") or "")
        items: list[dict] = []
        for entree in flux.entries[:limite]:
            titre = entree.get("title", "").strip()
            resume = entree.get("summary", "") or entree.get("description", "")
            # nettoyage basique du HTML résiduel des résumés
            resume = resume.replace("<br />", " ").replace("<br>", " ")
            resume = " ".join(resume.split())
            if filtre and filtre not in f"{normaliser_texte(titre)} {normaliser_texte(resume)}":
                continue
            url = entree.get("link", "")
            items.append(
                item_brut(
                    source,
                    titre=titre,
                    url=url,
                    resume=resume,
                    date_publication=_date_iso(entree),
                )
            )
        return items


def _date_iso(entree) -> str | None:
    """Convertit la date de l'entrée en ISO 8601, si exploitable."""
    for champ in ("published", "updated"):
        brut = entree.get(champ)
        if not brut:
            continue
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                d = datetime.strptime(brut.replace(" +0000", " +0000"), fmt)
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                return d.isoformat()
            except ValueError:
                continue
        # feedparser expose parfois déjà un objet temps structuré
        st = entree.get("published_parsed") or entree.get("updated_parsed")
        if st:
            return datetime(*st[:6], tzinfo=timezone.utc).isoformat()
    return None
