"""Digest Markdown — synthèse hebdomadaire par domaine, prête à diffuser."""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .traitement import duree_avant

DEFAUT_COULEURS = {
    "evaluation_projet": "🔎",
    "collecte_donnees": "📋",
    "etudes_recherches": "📚",
    "veille_economique": "📊",
    "promotion_investissements": "🚀",
}


def _lignes_items(rows: list[sqlite3.Row]) -> list[str]:
    lignes = []
    for r in rows:
        dl = f"⏰ **{r['date_limite']}** ({duree_avant(r['date_limite'])})" if r["date_limite"] else "—"
        lignes.append(
            f"1. **{r['titre']}** — *{r['source_nom'] or r['source_id']}*\n"
            f"   Score {r['score']}/100 · Date limite : {dl} · "
            f"[ouvrir]({r['url']})"
        )
    return lignes


def generer_digest(
    conn: sqlite3.Connection,
    config_domaines: dict,
    jours: int = 7,
    max_par_domaine: int = 15,
    chemin_sortie: str | Path | None = None,
) -> str:
    """Génère le digest Markdown de la période et le sauvegarde si chemin fourni."""
    depuis = (datetime.utcnow() - timedelta(days=jours)).strftime("%Y-%m-%d")
    aujourdhui = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # items de la période (par date de collecte, plus fiable que la date de publication)
    periode = [
        r for r in conn.execute(
            """
            SELECT * FROM items
            WHERE substr(cree_le, 1, 10) >= ?
            ORDER BY score DESC, cree_le DESC
            """,
            (depuis,),
        )
    ]
    statuts = dict(
        conn.execute(
            """
            SELECT statut, COUNT(*) FROM items
            WHERE substr(cree_le, 1, 10) >= ? GROUP BY statut
            """,
            (depuis,),
        ).fetchall()
    )

    rapport: list[str] = []
    rapport.append(f"# Digest de veille — consultances à Madagascar")
    rapport.append(f"*Période : {jours} derniers jours · Généré le {aujourdhui}*")
    rapport.append("")
    rapport.append(
        f"**{len(periode)} opportunités et signaux collectés** — "
        + " · ".join(f"{s} : {n}" for s, n in sorted(statuts.items()))
    )
    rapport.append("")

    libelles = {
        code: cfg.get("libelle", code) for code, cfg in config_domaines.get("domaines", {}).items()
    }
    for code, libelle in libelles.items():
        items_domaine = [
            r for r in periode
            if f'"{code}"' in (r["domaines"] or "")
        ]
        if not items_domaine:
            continue
        icone = DEFAUT_COULEURS.get(code, "•")
        rapport.append(f"## {icone} {libelle} — {len(items_domaine)} item(s)")
        rapport.append("")
        rapport.extend(_lignes_items(items_domaine[:max_par_domaine]))
        rapport.append("")

    # échéances imminentes toutes catégories
    imminentes = [
        r for r in periode
        if r["date_limite"]
        and r["date_limite"] >= datetime.utcnow().strftime("%Y-%m-%d")
        and r["date_limite"] <= (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d")
    ]
    if imminentes:
        rapport.append(f"## ⚠️ Échéances dans les 10 jours — {len(imminentes)}")
        rapport.append("")
        rapport.extend(_lignes_items(sorted(imminentes, key=lambda r: r["date_limite"])[:15]))
        rapport.append("")

    rapport.append("---")
    rapport.append(
        "*Prochaine étape du workflow : statuer sur chaque item retenu "
        "(`python -m veille statut <id> go|a_suivre|no_go`) — voir docs/00_methodologie.md.*"
    )

    texte = "\n".join(rapport)
    if chemin_sortie:
        chemin = Path(chemin_sortie)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(texte, encoding="utf-8")
    return texte


def exporter_csv(conn: sqlite3.Connection, chemin_sortie: str | Path, jours: int = 0) -> int:
    """Exporte les items (tous ou de la période) en CSV pour tableur/CRM."""
    requete = """
        SELECT id, source_nom, categorie, titre, url, date_publication, date_limite,
               domaines, score, statut, doublon, cree_le
        FROM items
    """
    params: tuple = ()
    if jours:
        depuis = (datetime.utcnow() - timedelta(days=jours)).strftime("%Y-%m-%d")
        requete += " WHERE substr(cree_le, 1, 10) >= ?"
        params = (depuis,)
    requete += " ORDER BY cree_le DESC"

    lignes = conn.execute(requete, params).fetchall()
    chemin = Path(chemin_sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8-sig") as f:
        ecrivain = csv.writer(f, delimiter=";")
        ecrivain.writerow(
            ["id", "source", "categorie", "titre", "url", "date_publication",
             "date_limite", "domaines", "score", "statut", "doublon", "collecte_le"]
        )
        for r in lignes:
            ecrivain.writerow(
                [r["id"], r["source_nom"], r["categorie"], r["titre"], r["url"],
                 r["date_publication"], r["date_limite"], r["domaines"], r["score"],
                 r["statut"], r["doublon"], r["cree_le"]]
            )
    return len(lignes)
