"""Connecteur API ReliefWeb (ONU-OCHA) — emplois/consultances et rapports.

API publique documentée : https://reliefweb.int/api
Points d'entrée utilisés : /1/jobs (opportunités) et /1/reports (études).
Requêtes filtrées sur le pays Madagascar.
"""

from __future__ import annotations

import requests

from .base import ErreurCollecte, item_brut

APPNAME = "veille-consultance-madagascar"
BASE = "https://api.reliefweb.int/1"


class CollecteurReliefWeb:

    @staticmethod
    def recuperer(source: dict, timeout: int = 20, user_agent: str = "") -> str:
        endpoint = source.get("endpoint", "jobs")
        limite = source.get("parametres", {}).get("limite", 40)
        parametres = {
            "appname": APPNAME,
            "limit": limite,
            "query[value]": "Madagascar",
            "sort[]": ["date:desc"],
            "fields[include][]": [
                "title", "url_alias", "date.created", "source.shortname", "source.name",
                "body-html",
            ],
        }
        try:
            reponse = requests.get(
                f"{BASE}/{endpoint}", params=parametres, timeout=timeout,
                headers={"User-Agent": user_agent or APPNAME},
            )
            reponse.raise_for_status()
            return reponse.text
        except requests.RequestException as e:
            raise ErreurCollecte(f"{type(e).__name__} : {e}") from e

    @staticmethod
    def parser(contenu: str, source: dict, limite: int = 40) -> list[dict]:
        import json

        try:
            donnees = json.loads(contenu)
        except json.JSONDecodeError as e:
            raise ErreurCollecte(f"Réponse JSON invalide : {e}") from e

        items: list[dict] = []
        for enregistrement in donnees.get("data", [])[:limite]:
            champs = enregistrement.get("fields", {})
            titre = champs.get("title", "")
            alias = champs.get("url_alias", "")
            if not alias:
                continue
            url = f"https://reliefweb.int{alias}" if alias.startswith("/") else alias
            source_avis = (champs.get("source", {}) or {}).get("shortname") \
                or (champs.get("source", {}) or {}).get("name", "")
            resume = (champs.get("body-html") or champs.get("body") or "").strip()
            resume = " ".join(resume.split())[:600]
            if source_avis:
                resume = f"[{source_avis}] {resume}" if resume else f"[{source_avis}]"
            items.append(
                item_brut(
                    source,
                    titre=titre,
                    url=url,
                    resume=resume,
                    date_publication=((champs.get("date") or {}).get("created")),
                )
            )
        return items
