"""Chargement de la configuration YAML (sources, domaines, paramètres)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# Racine du dépôt = parent du paquet `veille`
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_CONFIG = RACINE / "config"


def _charger(chemin: Path) -> dict:
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {chemin}")
    with chemin.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def charger_sources() -> list[dict]:
    """Retourne la liste des sources déclarées dans config/sources.yml."""
    donnees = _charger(DOSSIER_CONFIG / "sources.yml")
    return donnees.get("sources", [])


def charger_domaines() -> dict:
    """Retourne la configuration des domaines (mots-clés, seuils, pondérations)."""
    return _charger(DOSSIER_CONFIG / "domaines.yml")


def charger_parametres() -> dict:
    """Retourne les paramètres généraux (config/settings.yml)."""
    return _charger(DOSSIER_CONFIG / "settings.yml")


def chemin(relatif: str) -> Path:
    """Résout un chemin relatif au dépôt, en créant les dossiers parents si besoin."""
    p = Path(relatif)
    if not p.is_absolute():
        p = RACINE / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
