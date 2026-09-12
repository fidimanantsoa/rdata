"""Connecteurs de collecte.

Chaque connecteur expose :
    - recuperer(config_source) -> str  : télécharge (HTTP GET)
    - parser(contenu, config_source) -> list[dict] : transforme en items bruts
La séparation téléchargement/parsing permet de tester et de démontrer le
pipeline entièrement hors-ligne (jeu d'échantillons demo/fixtures/).
"""

from __future__ import annotations

from .rss import CollecteurRSS
from .reliefweb import CollecteurReliefWeb
from .worldbank import CollecteurIndicateursWB
from .html import CollecteurHTML

REGISTRE = {
    "rss": CollecteurRSS,
    "api_reliefweb": CollecteurReliefWeb,
    "api_wb_indicateurs": CollecteurIndicateursWB,
    "html": CollecteurHTML,
}


def get_collecteur(type_source: str):
    """Retourne la classe de connecteur associée au type déclaré en config."""
    if type_source not in REGISTRE:
        raise ValueError(
            f"Type de source inconnu : {type_source!r}. "
            f"Types disponibles : {', '.join(REGISTRE)}"
        )
    return REGISTRE[type_source]
