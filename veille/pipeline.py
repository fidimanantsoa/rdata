"""Orchestration du cycle de veille : collecte -> traitement -> stockage.

`cycle_complet` est le point d'entrée unique appelé par la CLI, par GitHub
Actions et par le mode démonstration hors-ligne.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config, modele, traitement
from .collecteurs import get_collecteur
from .collecteurs.base import ErreurCollecte


def _fichier_fixture(source: dict, dossier_fixtures: Path) -> Path | None:
    """Localise l'échantillon hors-ligne d'une source (mode démonstration)."""
    nom = f"{source['id']}.{ {'rss': 'xml', 'api_reliefweb': 'json', 'api_wb_indicateurs': 'json', 'html': 'html'} .get(source['type'], 'txt') }"
    chemin = dossier_fixtures / nom
    return chemin if chemin.exists() else None


def collecter_source(source: dict, params: dict, hors_ligne: bool = False) -> tuple[list[dict], str | None]:
    """Collecte une source : retourne (items_bruts, erreur_éventuelle)."""
    try:
        classe = get_collecteur(source["type"])
    except ValueError as e:
        return [], str(e)

    timeout = params.get("collecte", {}).get("timeout", 20)
    ua = params.get("collecte", {}).get("user_agent", "")
    limite = params.get("collecte", {}).get("limite_par_source", 40)

    try:
        if hors_ligne:
            fixture = _fichier_fixture(source, config.chemin(params["chemins"]["fixtures"]))
            if fixture is None:
                return [], None  # pas d'échantillon : source simplement ignorée en démo
            contenu = fixture.read_text(encoding="utf-8")
        else:
            contenu = classe.recuperer(source, timeout=timeout, user_agent=ua)
        items = classe.parser(contenu, source, limite=limite)
        return items, None
    except ErreurCollecte as e:
        return [], str(e)


def cycle_complet(
    hors_ligne: bool = False,
    sources_ciblees: list[str] | None = None,
    verbose: bool = True,
) -> dict:
    """Exécute un cycle complet de collecte et retourne le bilan."""
    debut = time.time()
    sources = config.charger_sources()
    cfg_domaines = config.charger_domaines()
    params = config.charger_parametres()

    if sources_ciblees:
        sources = [s for s in sources if s["id"] in sources_ciblees]

    conn = modele.ouvrir(config.chemin(params["chemins"]["base_donnees"]))
    modele.enregistrer_sources(conn, sources)

    cycle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    bilan = {"cycle": cycle_id, "collectees": 0, "nouvelles": 0,
             "doublons_url": 0, "doublons_titre": 0, "erreurs": {}}

    for source in sources:
        if source.get("statut") == "manuel":
            continue  # canal manuel : pas de connecteur, suivi documenté
        if not hors_ligne and source.get("statut") == "a_valider":
            pass  # on tente quand même : le diagnostic `verifier` calibrera

        items, erreur = collecter_source(source, params, hors_ligne=hors_ligne)
        if erreur:
            bilan["erreurs"][source["id"]] = erreur
            if verbose:
                print(f"  ✗ {source['id']} : {erreur}")
            continue
        if hors_ligne and not items:
            if verbose:
                print(f"  ○ {source['id']} : ignorée (pas d'échantillon hors-ligne)")
            continue

        for item in items:
            scores, score_global = traitement.classer(
                titre=item["titre"],
                resume=item["resume"],
                config=cfg_domaines,
                domaines_defaut=source.get("domaines_defaut"),
                priorite_source=source.get("priorite", 3),
                date_publication=item.get("date_publication"),
            )
            domaines = traitement.rattacher_domaines(scores, cfg_domaines)
            if not domaines and source.get("categorie") == "presse":
                domaines = {}  # la presse non classée reste stockée sans rattachement
            item["domaines"] = domaines
            item["score"] = score_global
            item["date_limite"] = traitement.extraire_date_limite(
                f"{item['titre']} {item['resume']}",
                date_publication=item.get("date_publication"),
            )
            resultat = modele.inserer_item(conn, item, cycle_id)
            if resultat == "nouveau":
                bilan["nouvelles"] += 1
            elif resultat == "doublon_url":
                bilan["doublons_url"] += 1
            else:
                bilan["doublons_titre"] += 1
        bilan["collectees"] += len(items)
        if verbose:
            print(f"  ✓ {source['id']} : {len(items)} item(s)")

    conn.commit()

    jours_purge = params.get("retention", {}).get("jours_purge", 548)
    purges = modele.purger_anciennes(conn, jours_purge)
    bilan["purges"] = purges

    modele.enregistrer_cycle(
        conn, cycle_id, time.time() - debut, bilan["collectees"],
        bilan["nouvelles"], bilan["doublons_url"] + bilan["doublons_titre"],
        bilan["erreurs"],
    )
    conn.close()
    bilan["duree_s"] = round(time.time() - debut, 1)
    return bilan
