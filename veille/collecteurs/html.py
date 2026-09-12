"""Connecteur HTML générique (scraping piloté par la configuration).

Aucun code n'est spécifique à un site : les sélecteurs CSS sont déclarés dans
config/sources.yml, ce qui permet d'ajuster une source (ou d'en ajouter une)
sans toucher au code. Stratégie par défaut si aucun sélecteur n'est déclaré :
repérer les liens internes porteurs d'une date, heuristique suffisante pour
les listes d'articles (WordPress, portails ministériels…).

Rappel méthodologique : vérifier les CGU/robots.txt de chaque site, garder
une fréquence de requête raisonnable (1 à 2 passages/semaine par source).
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..traitement import normaliser_texte
from .base import ErreurCollecte, item_brut, telecharger
from urllib.parse import urljoin

MOTIF_DATE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b|"
    r"\b(\d{1,2}(?:er)?\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|"
    r"septembre|octobre|novembre|décembre)\s+20\d{2})\b", re.IGNORECASE
)


class CollecteurHTML:

    @staticmethod
    def recuperer(source: dict, timeout: int = 20, user_agent: str = "") -> str:
        if not source.get("url"):
            raise ErreurCollecte("Source HTML sans URL")
        return telecharger(source["url"], timeout=timeout, user_agent=user_agent)

    @staticmethod
    def parser(contenu: str, source: dict, limite: int = 40) -> list[dict]:
        racine_url = source.get("url", "")
        selecteurs = source.get("selecteurs", {}) or {}
        soup = BeautifulSoup(contenu, "html.parser")

        for balise in soup(["script", "style", "nav", "footer", "header"]):
            balise.decompose()

        # 1) sélection des liens : sélecteur configuré, sinon heuristique
        selecteur = selecteurs.get("liens")
        if selecteur:
            liens = soup.select(selecteur)
        else:
            liens = CollecteurHTML._liens_heuristiques(soup, racine_url)

        filtre = normaliser_texte(source.get("filtre_inclut", "") or "")
        vus: set[str] = set()
        items: list[dict] = []
        for lien in liens:
            href = lien.get("href") or ""
            if not href:
                continue
            url = urljoin(racine_url, href)
            if not url.startswith("http") or url.rstrip("/") == racine_url.rstrip("/"):
                continue
            # les liens de menu/navigation sont écartés par longueur du texte
            texte = " ".join(lien.get_text(" ", strip=True).split())
            if len(texte) < 25 and not MOTIF_DATE.search(texte):
                continue
            if filtre and filtre not in normaliser_texte(texte):
                continue
            if url in vus:
                continue
            vus.add(url)

            bloc = lien if len(texte) > 60 else (lien.find_parent(["article", "li", "div"]) or lien)
            texte_bloc = " ".join(bloc.get_text(" ", strip=True).split())
            date_pub = CollecteurHTML._date_du_texte(texte_bloc)

            items.append(
                item_brut(
                    source,
                    titre=texte[:300] or texte_bloc[:300],
                    url=url,
                    resume=texte_bloc[:600],
                    date_publication=date_pub,
                )
            )
            if len(items) >= limite:
                break
        return items

    # ------------------------------------------------------------------

    @staticmethod
    def _liens_heuristiques(soup: BeautifulSoup, racine_url: str):
        """Liens internes situés dans une zone datée ou un <article>."""
        candidats = soup.select("article a[href]") or soup.select("main a[href]") \
            or soup.select(".post a[href]") or soup.select("a[href]")
        domaine = re.sub(r"^https?://(?:www\.)?", "", racine_url).split("/")[0]
        return [a for a in candidats if domaine in (a.get("href") or "")]

    @staticmethod
    def _date_du_texte(texte: str) -> str | None:
        m = MOTIF_DATE.search(texte)
        if not m:
            return None
        brut = m.group(1) or m.group(2)
        from ..traitement import extraire_date_limite
        iso = extraire_date_limite(brut)
        return f"{iso}T00:00:00Z" if iso else None
