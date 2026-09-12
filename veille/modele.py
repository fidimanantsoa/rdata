"""Modèle de données — base SQLite (items, sources, cycles).

Schéma volontairement minimal et lisible : la base est l'état du système,
elle peut être inspectée avec n'importe quel outil SQLite.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        TEXT NOT NULL,
    source_nom       TEXT,
    categorie        TEXT,
    titre            TEXT NOT NULL,
    url              TEXT NOT NULL,
    url_norm         TEXT NOT NULL,
    titre_norm       TEXT,
    resume           TEXT,
    date_publication TEXT,
    date_limite      TEXT,
    domaines         TEXT,          -- JSON : {"domaine": score_local}
    score            INTEGER DEFAULT 0,
    statut           TEXT DEFAULT 'nouveau',  -- nouveau|lu|a_suivre|go|no_go
    doublon          INTEGER DEFAULT 0,       -- 1 = titre déjà vu sous une autre URL
    cycle            TEXT,                    -- identifiant du cycle de collecte
    cree_le          TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_url ON items(url_norm);
CREATE INDEX IF NOT EXISTS idx_items_statut ON items(statut);
CREATE INDEX IF NOT EXISTS idx_items_date ON items(date_publication);

CREATE TABLE IF NOT EXISTS cycles (
    id            TEXT PRIMARY KEY,
    date          TEXT,
    duree_s       REAL,
    nb_collectes  INTEGER,
    nb_nouveaux   INTEGER,
    nb_doublons   INTEGER,
    sources_erreur TEXT            -- JSON : {source_id: message}
);

CREATE TABLE IF NOT EXISTS sources (
    id           TEXT PRIMARY KEY,
    nom          TEXT,
    type         TEXT,
    statut       TEXT,
    dernier_test TEXT,             -- date du dernier `verifier`
    dernier_etat TEXT              -- ok | erreur | manuel
);
"""


def maintenant_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ouvrir(chemin_bd: str | Path) -> sqlite3.Connection:
    """Ouvre (et initialise si besoin) la base de données."""
    chemin_bd = Path(chemin_bd)
    chemin_bd.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(chemin_bd)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def enregistrer_sources(conn: sqlite3.Connection, sources: list[dict]) -> None:
    """Met à jour la table miroir des sources (registre de config)."""
    for s in sources:
        conn.execute(
            """
            INSERT INTO sources (id, nom, type, statut)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nom=excluded.nom, type=excluded.type, statut=excluded.statut
            """,
            (s["id"], s.get("nom"), s.get("type"), s.get("statut")),
        )
    conn.commit()


def enregistrer_cycle(
    conn: sqlite3.Connection,
    cycle_id: str,
    duree: float,
    nb_collectes: int,
    nb_nouveaux: int,
    nb_doublons: int,
    erreurs: dict,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO cycles VALUES (?,?,?,?,?,?,?)",
        (
            cycle_id,
            maintenant_iso(),
            round(duree, 1),
            nb_collectes,
            nb_nouveaux,
            nb_doublons,
            json.dumps(erreurs, ensure_ascii=False),
        ),
    )
    conn.commit()


def inserer_item(conn: sqlite3.Connection, item: dict, cycle_id: str) -> str:
    """Insère un item normalisé. Retourne : 'nouveau', 'doublon_url' ou 'doublon_titre'.

    Politique de dédoublonnage :
      - URL normalisée identique  -> ignoré (même document, repris par un agrégateur) ;
      - titre normalisé identique -> inséré mais marqué doublon=1 (piste à vérifier :
        le même avis publié sur deux canaux distincts reste utile à suivre).
    """
    cur = conn.execute(
        """
        INSERT INTO items (source_id, source_nom, categorie, titre, url, url_norm,
                           titre_norm, resume, date_publication, date_limite,
                           domaines, score, statut, cycle, cree_le)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(url_norm) DO NOTHING
        """,
        (
            item["source_id"],
            item.get("source_nom"),
            item.get("categorie"),
            item["titre"],
            item["url"],
            item["url_norm"],
            item.get("titre_norm"),
            item.get("resume"),
            item.get("date_publication"),
            item.get("date_limite"),
            json.dumps(item.get("domaines", {}), ensure_ascii=False),
            item.get("score", 0),
            "nouveau",
            cycle_id,
            maintenant_iso(),
        ),
    )
    if cur.rowcount == 0:
        return "doublon_url"

    # Dédoublonnage par titre (après insertion, on marque sans supprimer)
    if item.get("titre_norm"):
        n = conn.execute(
            "SELECT COUNT(*) c FROM items WHERE titre_norm=? AND id != last_insert_rowid()",
            (item["titre_norm"],),
        ).fetchone()["c"]
        if n > 0:
            conn.execute(
                "UPDATE items SET doublon=1 WHERE id = last_insert_rowid()"
            )
            conn.commit()
            return "doublon_titre"
    conn.commit()
    return "nouveau"


def maj_statut(conn: sqlite3.Connection, item_id: int, statut: str) -> bool:
    cur = conn.execute(
        "UPDATE items SET statut=? WHERE id=?", (statut, item_id)
    )
    conn.commit()
    return cur.rowcount > 0


def purger_anciennes(conn: sqlite3.Connection, jours: int) -> int:
    """Supprime les items collectés depuis plus de `jours` (hors statuts actifs).

    La purge s'appuie sur la date de collecte (cree_le), pas sur la date de
    publication : certains items (indicateurs économiques, rapports) portent
    des dates de référence anciennes mais restent utiles à l'archive.
    """
    cur = conn.execute(
        """
        DELETE FROM items
        WHERE statut IN ('nouveau','lu','no_go')
          AND cree_le IS NOT NULL
          AND cree_le < datetime('now', ?)
        """,
        (f"-{jours} days",),
    )
    conn.commit()
    return cur.rowcount
