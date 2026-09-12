"""Connecteur API Indicateurs de la Banque mondiale (veille économique quantitative).

Interroge https://api.worldbank.org/v2/country/MGA/indicator/{code}?mrnev=1
(dernière valeur non vide) pour chaque indicateur déclaré dans sources.yml.
Chaque résultat devient un item du domaine veille_economique, avec la valeur
dans le résumé : le système garde l'historique des relevés.
"""

from __future__ import annotations

import json

import requests

from .base import ErreurCollecte, item_brut


class CollecteurIndicateursWB:

    @staticmethod
    def recuperer(source: dict, timeout: int = 20, user_agent: str = "") -> str:
        """Regroupe les derniers relevés de tous les indicateurs en un JSON."""
        indicateurs = source.get("parametres", {}).get("indicateurs", [])
        if not indicateurs:
            raise ErreurCollecte("Aucun indicateur déclaré pour cette source")

        gabarit = source.get("url", "https://api.worldbank.org/v2/country/MGA/indicator/{code}")
        entetes = {"User-Agent": user_agent or "Veille-Consultance-Madagascar/1.0"}
        releves: list[dict] = []
        for indicateur in indicateurs:
            code = indicateur["code"]
            try:
                reponse = requests.get(
                    gabarit.format(code=code),
                    params={"format": "json", "mrnev": 1},
                    headers=entetes, timeout=timeout,
                )
                reponse.raise_for_status()
            except requests.RequestException as e:
                releves.append({"code": code, "erreur": f"{type(e).__name__} : {e}"})
                continue
            releves.append(
                {"code": code, "libelle": indicateur.get("libelle", code),
                 "donnees": reponse.json()}
            )
        return json.dumps(releves, ensure_ascii=False)

    @staticmethod
    def parser(contenu: str, source: dict, limite: int = 40) -> list[dict]:
        try:
            releves = json.loads(contenu)
        except json.JSONDecodeError as e:
            raise ErreurCollecte(f"Relevés illisibles : {e}") from e

        items: list[dict] = []
        for releve in releves:
            if "erreur" in releve:
                continue
            corps = releve.get("donnees")
            # format WB : [méta, [lignes]] ; mrnev=1 -> une seule ligne
            if not isinstance(corps, list) or len(corps) < 2 or not corps[1]:
                continue
            ligne = corps[1][0]
            valeur = ligne.get("value")
            annee = ligne.get("date", "?")
            if valeur is None:
                continue
            code, libelle = releve["code"], releve.get("libelle", releve["code"])
            items.append(
                item_brut(
                    source,
                    titre=f"{libelle} — {valeur:g} ({annee})".replace(".", ","),
                    url=(ligne.get("indicator") or {}).get("id", "")
                         and f"https://data.worldbank.org/indicator/{code}?locations=MG"
                         or "",
                    resume=(
                        f"Dernière valeur disponible de l'indicateur Banque mondiale "
                        f"{code} pour Madagascar : {valeur:g} ({annee})."
                    ),
                    date_publication=f"{annee}-12-31T00:00:00Z",
                )
            )
        return items
