"""Interface en ligne de commande : `python -m veille <commande>`."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from . import __version__, config, dashboard, modele, notifier, pipeline, rapports

# ---------------------------------------------------------------------------

BANNIERE = f"""
╔══════════════════════════════════════════════════════════════════╗
║   Système de veille — Activités de consultance à Madagascar       ║
║   Évaluations · Données · Études · Économie · Investissements    ║
╚══════════════════════════════════════════════════════════════════╝
   v{__version__} — docs/00_methodologie.md
"""


def _connexion() -> tuple[sqlite3.Connection, dict, dict, dict]:
    params = config.charger_parametres()
    cfg_domaines = config.charger_domaines()
    conn = modele.ouvrir(config.chemin(params["chemins"]["base_donnees"]))
    return conn, params, cfg_domaines


# ---------------------------------------------------------------------------

def cmd_collecter(args):
    if getattr(args, "_banniere_deja_affichee", False):
        print()
    else:
        print(BANNIERE)
    cibles = args.sources.split(",") if getattr(args, "sources", None) else None
    print(f"▶ Cycle de collecte {'hors-ligne (échantillons)' if args.offline else 'en ligne'}"
          + (f" — sources : {', '.join(cibles)}" if cibles else ""))
    bilan = pipeline.cycle_complet(hors_ligne=args.offline, sources_ciblees=cibles)
    print(
        f"\n■ Bilan du cycle {bilan['cycle']} ({bilan['duree_s']} s)\n"
        f"  items collectés : {bilan['collectees']}\n"
        f"  nouveaux        : {bilan['nouvelles']}\n"
        f"  doublons URL    : {bilan['doublons_url']}\n"
        f"  doublons titre  : {bilan['doublons_titre']}\n"
        f"  purges          : {bilan.get('purges', 0)}\n"
        f"  erreurs         : {len(bilan['erreurs'])}"
        + (f"\n    " + "\n    ".join(f"{k} → {v}" for k, v in bilan['erreurs'].items())
           if bilan["erreurs"] else "")
    )


def cmd_demo(args):
    args.offline = True
    args.sources = getattr(args, "sources", None)
    args.jours = getattr(args, "jours", None)
    print(BANNIERE)
    print("▶ DÉMONSTRATION hors-ligne : le pipeline complet s'exécute sur les")
    print("  échantillons réalistes de demo/fixtures/ (aucun accès réseau).")
    args_silencieux = argparse.Namespace(**vars(args))
    args_silencieux._banniere_deja_affichee = True
    cmd_collecter(args_silencieux)
    cmd_rapport(args)
    cmd_dashboard(args)


def cmd_verifier(args):
    print(BANNIERE)
    print("▶ Diagnostic des sources (réseau + parsing)\n")
    params = config.charger_parametres()
    sources = config.charger_sources()
    cibles = args.sources.split(",") if args.sources else None
    connexion, _, _ = _connexion()
    ok, ko, manuelles = 0, 0, 0
    for s in sources:
        if cibles and s["id"] not in cibles:
            continue
        if s.get("type") == "manuel":
            manuelles += 1
            print(f"  ○ {s['id']:<22} canal manuel (inscription/alertes) — cf. registre")
            continue
        items, erreur = pipeline.collecter_source(s, params)
        if erreur:
            ko += 1
            print(f"  ✗ {s['id']:<22} {erreur[:90]}")
            etat = "erreur"
        else:
            ok += 1
            exemples = "; ".join(i["titre"][:40] for i in items[:2])
            print(f"  ✓ {s['id']:<22} {len(items)} item(s) — {exemples}")
            etat = "ok"
        connexion.execute(
            "UPDATE sources SET dernier_test=?, dernier_etat=? WHERE id=?",
            (modele.maintenant_iso(), etat, s["id"]),
        )
    connexion.commit()
    connexion.close()
    print(f"\n■ Sources : {ok} opérationnelles · {ko} en erreur (à calibrer ou retirer) "
          f"· {manuelles} manuelles")
    print("  Après calibrage (sélecteurs CSS, URL de flux), mettre à jour le champ")
    print("  `statut` dans config/sources.yml : a_valider -> operationnel.")


def cmd_rapport(args):
    conn, params, cfg_domaines = _connexion()
    jours = args.jours or params["rapport"]["jours_couverture"]
    max_items = params["rapport"]["max_par_domaine"]
    horodate = datetime.utcnow().strftime("%Y-%m-%d")
    chemin = config.chemin(params["chemins"]["rapports"]) / f"{horodate}_digest.md"
    texte = rapports.generer_digest(conn, cfg_domaines, jours=jours,
                                    max_par_domaine=max_items, chemin_sortie=chemin)
    nb_items = texte.count("\n1. ")
    conn.close()
    print(f"▶ Digest généré : {chemin.relative_to(config.RACINE)} "
          f"({jours} jours, {nb_items} items référencés)")
    if params.get("notification", {}).get("actif", False):
        succes, msg = notifier.envoyer_digest(
            texte, sujet=f"{params['notification'].get('objet_prefixe', '[Veille]')} "
                         f"digest du {horodate}")
        print(("  ✓ " if succes else "  ✗ ") + msg)


def cmd_dashboard(args):
    conn, params, cfg_domaines = _connexion()
    chemin = config.chemin(params["chemins"]["dashboard"])
    n = dashboard.generer_dashboard(conn, cfg_domaines, chemin,
                                    limite=params["dashboard"]["items_affiches"])
    conn.close()
    print(f"▶ Tableau de bord généré : {chemin.relative_to(config.RACINE)} ({n} items)")


def cmd_exporter(args):
    conn, params, _ = _connexion()
    horodate = datetime.utcnow().strftime("%Y-%m-%d")
    chemin = config.chemin(params["chemins"]["exports"]) / f"items_{horodate}.csv"
    n = rapports.exporter_csv(conn, chemin, jours=args.jours)
    conn.close()
    print(f"▶ Export CSV : {chemin.relative_to(config.RACINE)} ({n} items)")


def cmd_ajouter(args):
    """Consigne manuellement une opportunité (LinkedIn, WhatsApp, bouche-à-oreille)."""
    conn, _, cfg_domaines = _connexion()
    sources = {s["id"]: s for s in config.charger_sources()}
    source = sources.get(args.source)
    if not source:
        print(f"✗ Source inconnue : {args.source}. IDs valides : {', '.join(sources)}")
        sys.exit(1)
    from . import traitement
    item = {
        "source_id": source["id"], "source_nom": source.get("nom"),
        "categorie": source.get("categorie"), "titre": args.titre,
        "url": args.url, "url_norm": traitement.normaliser_url(args.url),
        "titre_norm": traitement.normaliser_titre(args.titre),
        "resume": args.resume or "", "date_publication": modele.maintenant_iso(),
    }
    scores, score = traitement.classer(
        args.titre, args.resume or "", cfg_domaines,
        source.get("domaines_defaut"), source.get("priorite", 3))
    item["domaines"] = traitement.rattacher_domaines(scores, cfg_domaines)
    item["score"] = score
    item["date_limite"] = traitement.extraire_date_limite(f"{args.titre} {args.resume or ''}")
    resultat = modele.inserer_item(conn, item, "saisie-manuelle")
    conn.close()
    print(f"{'✓ consigné' if resultat == 'nouveau' else '○ ' + resultat} "
          f"— domaines : {', '.join(item['domaines']) or 'aucun'} · score {score}/100")


def cmd_statut(args):
    conn, _, _ = _connexion()
    if args.statut not in ("lu", "a_suivre", "go", "no_go", "nouveau"):
        print("✗ Statut invalide. Valeurs : nouveau, lu, a_suivre, go, no_go")
        sys.exit(1)
    if modele.maj_statut(conn, args.id, args.statut):
        print(f"✓ Item {args.id} → {args.statut}")
    else:
        print(f"✗ Aucun item avec l'id {args.id}")
    conn.close()


def cmd_registre(args):
    """Génère docs/registre_sources.md depuis config/sources.yml (doc toujours à jour)."""
    sources = config.charger_sources()
    lignes = [
        "# Registre des sources — veille des activités de consultance à Madagascar",
        "",
        "*Document généré automatiquement depuis `config/sources.yml` — ne pas éditer à la main.*",
        "*Régénérer : `python -m veille registre`*",
        "",
        f"**{len(sources)} sources** enregistrées.",
        "",
        "| # | Source | Catégorie | Accès | Statut | Priorité | Fréquence | Domaines par défaut |",
        "|---|--------|-----------|-------|--------|----------|-----------|---------------------|",
    ]
    pictos = {"operationnel": "🟢 opérationnel", "a_valider": "🟠 à calibrer", "manuel": "🔵 manuel"}
    for i, s in enumerate(sources, 1):
        domaines = ", ".join(s.get("domaines_defaut", [])) or "—"
        lignes.append(
            f"| {i} | [{s['nom']}]({s.get('url') or ''}) | {s.get('categorie', '')} "
            f"| `{s['type']}` | {pictos.get(s.get('statut'), s.get('statut'))} "
            f"| {s.get('priorite', '—')} | {s.get('frequence', '—')} | {domaines} |"
        )
    lignes += [
        "",
        "## Légende",
        "",
        "- 🟢 **opérationnel** : connecteur prêt (API/flux vérifié).",
        "- 🟠 **à calibrer** : source identifiée, sélecteurs ou URL de flux à ajuster "
        "lors du déploiement (`python -m veille verifier`).",
        "- 🔵 **manuel** : canal sans connecteur (inscription, alertes e-mail, plateforme "
        "payante, réseaux sociaux) — procédure décrite dans la méthodologie.",
        "",
        "## Détail des sources",
        "",
    ]
    for s in sources:
        lignes.append(f"### {s['nom']}")
        lignes.append(f"- **id** : `{s['id']}` · **type** : `{s['type']}` · "
                      f"**statut** : {s.get('statut')} · **priorité** : {s.get('priorite', '—')}")
        if s.get("url"):
            lignes.append(f"- **accès** : {s['url']}")
        if s.get("commentaire"):
            lignes.append(f"- *{s['commentaire'].strip()}*")
        lignes.append("")

    chemin = config.RACINE / "docs" / "registre_sources.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print(f"▶ Registre généré : docs/registre_sources.md ({len(sources)} sources)")


def cmd_stats(args):
    """Indicateurs du système : volumes, statuts, cycles récents."""
    conn, _, _ = _connexion()
    total = conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
    par_statut = dict(conn.execute("SELECT statut, COUNT(*) FROM items GROUP BY statut").fetchall())
    par_source = conn.execute(
        "SELECT source_nom, COUNT(*) c FROM items GROUP BY source_id ORDER BY c DESC LIMIT 10"
    ).fetchall()
    cycles = conn.execute(
        "SELECT * FROM cycles ORDER BY date DESC LIMIT 5"
    ).fetchall()
    print(BANNIERE)
    print(f"▶ Indicateurs du système\n\n  items en base : {total}")
    print("  par statut    : " + (", ".join(f"{k}={v}" for k, v in par_statut.items()) or "—"))
    print("\n  top sources :")
    for r in par_source:
        print(f"    {r['source_nom'][:60]:<62} {r['c']:>4}")
    print("\n  derniers cycles :")
    for r in cycles:
        erreurs = ", ".join(json.loads(r["sources_erreur"] or "{}").keys()) or "—"
        print(f"    {r['date'][:16]}  +{r['nb_nouveaux']:>3} nouveaux  "
              f"{r['nb_collectes']:>3} collectés  erreurs : {erreurs}")
    conn.close()


# ---------------------------------------------------------------------------

def main():
    analyse = argparse.ArgumentParser(
        prog="veille",
        description="Système de veille — activités de consultance à Madagascar",
    )
    analyse.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sous = analyse.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("collecter", help="cycle complet de collecte (réseau)")
    p.add_argument("--offline", action="store_true",
                   help="mode hors-ligne sur les échantillons (aucun réseau)")
    p.add_argument("--sources", help="liste d'ids de sources, séparés par des virgules")
    p.set_defaults(func=cmd_collecter)

    p = sous.add_parser("demo", help="démonstration complète hors-ligne")
    p.set_defaults(func=cmd_demo)

    p = sous.add_parser("verifier", help="diagnostic de santé des sources")
    p.add_argument("--sources", help="liste d'ids, séparés par des virgules")
    p.set_defaults(func=cmd_verifier)

    p = sous.add_parser("rapport", help="digest Markdown de la période")
    p.add_argument("--jours", type=int, help="fenêtre en jours (défaut : settings.yml)")
    p.set_defaults(func=cmd_rapport)

    p = sous.add_parser("dashboard", help="tableau de bord HTML autonome")
    p.set_defaults(func=cmd_dashboard)

    p = sous.add_parser("exporter", help="export CSV")
    p.add_argument("--jours", type=int, default=0, help="0 = tous les items")
    p.set_defaults(func=cmd_exporter)

    p = sous.add_parser("ajouter", help="consigner une opportunité saisie manuellement")
    p.add_argument("source", help="id de la source (ex. linkedin_alertes)")
    p.add_argument("titre")
    p.add_argument("url")
    p.add_argument("--resume", default="")
    p.set_defaults(func=cmd_ajouter)

    p = sous.add_parser("statut", help="faire évoluer le statut d'un item")
    p.add_argument("id", type=int)
    p.add_argument("statut")
    p.set_defaults(func=cmd_statut)

    p = sous.add_parser("stats", help="indicateurs du système")
    p.set_defaults(func=cmd_stats)

    p = sous.add_parser("registre", help="régénère la documentation du registre des sources")
    p.set_defaults(func=cmd_registre)

    args = analyse.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
