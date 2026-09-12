"""Tableau de bord HTML autonome.

Le fichier produit embarque les données (JSON inline) et tout le nécessaire
(vanilla JS + CSS inline) : il s'ouvre en local (double-clic), sur GitHub
Pages ou n'importe quel hébergement statique, sans dépendance externe.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

GABARIT = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veille — Consultances Madagascar</title>
<style>
:root {
  --fond: #f6f7f9; --carte: #ffffff; --encre: #1f2937; --gris: #6b7280;
  --accent: #0e7490; --bordure: #e5e7eb;
  --evaluation_projet: #7c3aed; --collecte_donnees: #0891b2;
  --etudes_recherches: #4f46e5; --veille_economique: #16a34a;
  --promotion_investissements: #ea580c;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       background: var(--fond); color: var(--encre); }
header { background: linear-gradient(135deg, #0c4a6e, #0e7490); color: #fff;
         padding: 24px 32px; }
header h1 { margin: 0; font-size: 1.45rem; }
header p { margin: 6px 0 0; opacity: .85; font-size: .9rem; }
.barre { display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
         padding: 14px 32px; background: var(--carte);
         border-bottom: 1px solid var(--bordure); position: sticky; top: 0; z-index: 5; }
.barre input, .barre select { padding: 8px 10px; border: 1px solid var(--bordure);
         border-radius: 8px; font-size: .9rem; background: #fff; }
.barre input[type=search] { flex: 1; min-width: 200px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px; padding: 20px 32px; }
.kpi { background: var(--carte); border: 1px solid var(--bordure);
       border-radius: 12px; padding: 14px 16px; }
.kpi b { display: block; font-size: 1.5rem; }
.kpi span { color: var(--gris); font-size: .78rem; text-transform: uppercase;
       letter-spacing: .04em; }
main { padding: 0 32px 48px; }
.item { background: var(--carte); border: 1px solid var(--bordure);
        border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
        display: flex; gap: 14px; align-items: flex-start; }
.item:hover { border-color: var(--accent); }
.score { min-width: 52px; text-align: center; border-radius: 10px;
         background: #ecfeff; color: var(--accent); font-weight: 700;
         padding: 8px 6px; font-size: 1.05rem; }
.corps { flex: 1; }
.titre a { color: var(--encre); text-decoration: none; font-weight: 600; }
.titre a:hover { color: var(--accent); text-decoration: underline; }
.meta { color: var(--gris); font-size: .8rem; margin-top: 4px;
        display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.badge { font-size: .7rem; font-weight: 600; color: #fff; border-radius: 999px;
         padding: 2px 9px; background: var(--gris); }
.badge.evaluation_projet { background: var(--evaluation_projet); }
.badge.collecte_donnees { background: var(--collecte_donnees); }
.badge.etudes_recherches { background: var(--etudes_recherches); }
.badge.veille_economique { background: var(--veille_economique); }
.badge.promotion_investissements { background: var(--promotion_investissements); }
.alerte { color: #b91c1c; font-weight: 700; }
.statut { font-size: .72rem; border: 1px solid var(--bordure); border-radius: 6px;
          padding: 1px 7px; color: var(--gris); }
.statut.go { background: #dcfce7; color: #166534; border-color: #86efac; }
.statut.a_suivre { background: #fef9c3; color: #854d0e; border-color: #fde047; }
.statut.no_go { background: #fee2e2; color: #991b1b; border-color: #fca5a5; }
.vide { text-align: center; color: var(--gris); padding: 60px 0; }
footer { text-align: center; color: var(--gris); font-size: .78rem; padding: 18px; }
</style>
</head>
<body>
<header>
  <h1>🔍 Veille — Activités de consultance à Madagascar</h1>
  <p>Évaluations · Collecte de données · Études &amp; recherches · Veille économique · Promotion des investissements</p>
</header>

<div class="barre">
  <input type="search" id="q" placeholder="Rechercher un titre, un bailleur, un mot-clé…">
  <select id="f_domaine">
    <option value="">Tous les domaines</option>
    <option value="evaluation_projet">Évaluation de projets</option>
    <option value="collecte_donnees">Collecte de données</option>
    <option value="etudes_recherches">Études &amp; recherches</option>
    <option value="veille_economique">Veille économique</option>
    <option value="promotion_investissements">Investissements</option>
  </select>
  <select id="f_statut">
    <option value="">Tous les statuts</option>
    <option value="nouveau">Nouveaux</option>
    <option value="a_suivre">À suivre</option>
    <option value="go">Go</option>
    <option value="no_go">No-go</option>
    <option value="lu">Lu</option>
  </select>
  <select id="f_source"><option value="">Toutes les sources</option></select>
</div>

<div class="kpis" id="kpis"></div>
<main><div id="liste"></div></main>
<footer>Données collectées automatiquement — voir <b>digest Markdown</b> pour la synthèse éditoriale · Généré le __GENERE__</footer>

<script>
const ITEMS = __DONNEES__;
const LIBELLES = __LIBELLES__;
const DOMAINE_ORDRE = ["evaluation_projet","collecte_donnees","etudes_recherches",
                       "veille_economique","promotion_investissements"];

function badge(code){ return '<span class="badge '+code+'">'+(LIBELLES[code]||code)+'</span>'; }

function compteurs(liste){
  const par_domaine = {};
  DOMAINE_ORDRE.forEach(d => par_domaine[d] = 0);
  let go = 0, bientot = 0;
  liste.forEach(it => {
    (it.domaines||[]).forEach(d => { if(d in par_domaine) par_domaine[d]++; });
    if (it.statut === 'go') go++;
    if (it.jours_restants !== null && it.jours_restants >= 0 && it.jours_restants <= 10) bientot++;
  });
  let html = '<div class="kpi"><b>'+liste.length+'</b><span>items au total</span></div>';
  DOMAINE_ORDRE.forEach(d => {
    html += '<div class="kpi"><b>'+par_domaine[d]+'</b><span>'+LIBELLES[d]+'</span></div>';
  });
  html += '<div class="kpi"><b>'+go+'</b><span>statut go</span></div>'
       +  '<div class="kpi"><b>'+bientot+'</b><span>éch. &lt; 10 j</span></div>';
  document.getElementById('kpis').innerHTML = html;
}

function rendu(){
  const q = document.getElementById('q').value.toLowerCase();
  const d = document.getElementById('f_domaine').value;
  const s = document.getElementById('f_statut').value;
  const src = document.getElementById('f_source').value;
  const liste = ITEMS.filter(it =>
    (!d || (it.domaines||[]).includes(d)) &&
    (!s || it.statut === s) &&
    (!src || it.source_nom === src) &&
    (!q || (it.titre+' '+it.resume+' '+it.source_nom).toLowerCase().includes(q))
  );
  compteurs(liste);
  if (!liste.length){
    document.getElementById('liste').innerHTML = '<div class="vide">Aucun item ne correspond aux filtres.</div>';
    return;
  }
  document.getElementById('liste').innerHTML = liste.map(it => {
    const domaines = (it.domaines||[]).sort((a,b)=>DOMAINE_ORDRE.indexOf(a)-DOMAINE_ORDRE.indexOf(b)).map(badge).join(' ');
    const dl = it.date_limite
      ? '<span class="'+(it.jours_restants!==null && it.jours_restants<=10 ? 'alerte' : '')+'">⏰ '+it.date_limite
        +(it.jours_restants===null?'':' ('+(it.jours_restants<0?'clôturé':'J-'+it.jours_restants)+')')+'</span>'
      : '';
    return '<div class="item"><div class="score" title="score de pertinence">'+it.score+'</div>'
      + '<div class="corps"><div class="titre"><a href="'+it.url+'" target="_blank" rel="noopener">'+it.titre+'</a></div>'
      + '<div class="meta"><span>'+it.source_nom+'</span><span>'+ (it.date_publication||'').slice(0,10) +'</span>'
      + dl + '<span class="statut '+it.statut+'">'+it.statut+'</span></div>'
      + '<div class="meta">'+domaines+'</div></div></div>';
  }).join('');
}

// peuplement des sources
const sources = [...new Set(ITEMS.map(i => i.source_nom))].sort();
document.getElementById('f_source').innerHTML =
  '<option value="">Toutes les sources</option>'
  + sources.map(s => '<option>'+s+'</option>').join('');
['q','f_domaine','f_statut','f_source'].forEach(id =>
  document.getElementById(id).addEventListener('input', rendu));
rendu();
</script>
</body>
</html>
"""


def generer_dashboard(
    conn: sqlite3.Connection,
    config_domaines: dict,
    chemin_sortie: str | Path,
    limite: int = 300,
) -> int:
    """Exporte les `limite` items les plus récents/pertinents dans un HTML autonome."""
    lignes = conn.execute(
        """
        SELECT id, source_nom, titre, url, resume, date_publication, date_limite,
               domaines, score, statut, doublon, cree_le
        FROM items ORDER BY score DESC, cree_le DESC LIMIT ?
        """,
        (limite,),
    ).fetchall()

    from datetime import date
    aujourdhui = date.today()
    donnees = []
    for r in lignes:
        jr = None
        if r["date_limite"]:
            try:
                jr = (date.fromisoformat(r["date_limite"][:10]) - aujourdhui).days
            except ValueError:
                pass
        try:
            dict_domaines = json.loads(r["domaines"]) if r["domaines"] else {}
        except json.JSONDecodeError:
            dict_domaines = {}
        donnees.append(
            {
                "id": r["id"], "source_nom": r["source_nom"] or r["id"],
                "titre": r["titre"], "url": r["url"], "resume": (r["resume"] or "")[:400],
                "date_publication": r["date_publication"], "date_limite": r["date_limite"],
                "domaines": sorted(dict_domaines.keys()),
                "score": r["score"], "statut": r["statut"], "jours_restants": jr,
            }
        )

    libelles = {
        code: cfg.get("libelle", code)
        for code, cfg in config_domaines.get("domaines", {}).items()
    }
    html = (
        GABARIT.replace("__DONNEES__", json.dumps(donnees, ensure_ascii=False))
        .replace("__LIBELLES__", json.dumps(libelles, ensure_ascii=False))
        .replace("__GENERE__", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    )
    chemin = Path(chemin_sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(html, encoding="utf-8")
    return len(donnees)
