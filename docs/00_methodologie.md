# Méthodologie du système de veille
## Activités de consultance à Madagascar — évaluations, collecte de données, études & recherches, veille économique, promotion des investissements

> **Objet du document** : définir la méthode et les outils du système de veille, son
> architecture, ses règles de fonctionnement et sa gouvernance. Le système est livré
> opérationnel dans ce dépôt ; ce document explique *comment il fonctionne* et *comment
> le faire vivre*.

---

## 1. Cadrage

### 1.1 Objectifs

| # | Objectif | Indicateur de réussite |
|---|----------|------------------------|
| O1 | **Ne rater aucune opportunité de consultance** publiée sur les canaux publics accessibles (appels d'offres, avis de sélection de consultants, REOI) | 0 opportunité signalée a posteriori comme manquée sur les sources couvertes |
| O2 | **Détecter tôt** — en amont des avis formels — les besoins à venir (approbation de projets, publications d'évaluations, réformes) | ≥ 1 signal d'anticipation par mois exploitable en prospection |
| O3 | **Maintenir une connaissance économique à jour** du contexte malgache, mobilisable dans les propositions (chiffres de cadrage) | indicateurs macro rafraîchis chaque semaine dans la base |
| O4 | **Capitaliser** un historique structuré (qui publie quoi, quand, sur quels sujets) alimentant la stratégie commerciale | base d'historique consultable, export CSV pour CRM |
| O5 | **Limiter le coût de la veille** : automatisation maximale, temps humain concentré sur l'analyse et la décision | < 2 h/semaine de travail humain (validation du digest) |

### 1.2 Périmètre

**Domaines couverts** (les 5 axes demandés) :

1. `evaluation_projet` — évaluations de projets/programmes (baseline, mi-parcours, finale, impact) ;
2. `collecte_donnees` — enquêtes et collecte de données (ménages, CAPI/tablettes, gestion et qualité des données) ;
3. `etudes_recherches` — études de faisabilité, études sectorielles et de marché, recherches, diagnostics, cartographies ;
4. `veille_economique` — conjoncture, indicateurs macro, budgets, politique monétaire, pauvreté ;
5. `promotion_investissements` — climat des affaires, réformes, guichet unique, zones franches, PPP, attractivité.

**Hors périmètre** (explicitement) : marchés de travaux et de fournitures « physiques »
(ils sont collectés car présents dans les mêmes flux, mais non rattachés aux domaines —
donc filtrables en un clic), veille concurrentielle payante approfondie, opportunités
hors Madagascar.

### 1.3 Utilisateurs

Conçu pour un usage individuel (consultant indépendant ou petite structure), sans
infrastructure serveur : tout fonctionne sur un ordinateur portable ou dans GitHub
Actions (gratuit).

---

## 2. Cartographie de la demande

La demande de consultance à Madagascar émane de six familles de donneurs d'ordre,
qui ne publient pas au même endroit ni au même moment. La couverture du système
reflète cette cartographie :

| Famille | Qui exactement | Où publient-ils | Signal d'anticipation |
|---|---|---|---|
| **Système ONU** | PNUD, UNICEF, PAM, FAO, OMS, OIM… | UNGM, portails propres, ReliefWeb | Cadres de coopération pays (UNSDCF) |
| **Bailleurs multilatéraux** | Banque mondiale, BAD, FIDA, FMI | Agences d'exécution nationales, portails passation, UN Development Business | Approbation de projets (PAD), revues à mi-parcours |
| **Bailleurs bilatéraux** | AFD, UE, GIZ, JICA, USAID, DDC | Portails passation propres, délégations, ambassades | Programmation pluriannuelle, appels à propositions |
| **État et agences malgaches** | Ministères, FID, ONE, INSTAT, ARMP, EDBM | ARMP (e-GP/SIGMP), sites institutionnels, presse | Lois de finances, DSRP, PTA d'agences |
| **ONG et organisations** | CARE, CRS, Gret, AVC, consortiums bailleurs | ReliefWeb, sites propres, réseaux sociaux | Présence dans les zones d'intervention |
| **Secteur privé / ingénierie** | Bureaux d'études, EDBM, CCI, projets PPP | EDBM, CCI, presse économique | Annonces d'investissements (EIES à venir) |

**Conséquence méthodologique** : les avis formels (O1) sont largement automatisables ;
les signaux d'anticipation (O2) relèvent d'une lecture humaine guidée par le digest.
Le système distingue donc explicitement les deux.

---

## 3. Architecture du système

Le cycle de veille suit cinq étapes — **Relever → Filtrer → Analyser → Diffuser → Piloter** :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RELEVER (automatisé)                                                       │
│  29 sources (config/sources.yml) → 4 connecteurs :                          │
│    • RSS/Atom (feedparser)        : UNDP, BAD, presse…                      │
│    • API JSON (requests)          : ReliefWeb (jobs, reports),              │
│                                     indicateurs Banque mondiale             │
│    • HTML piloté (bs4 + sélecteurs): FID, ARMP, INSTAT, EDBM…               │
│    • Canaux manuels documentés    : UNGM, LinkedIn, EU, réseaux sociaux     │
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FILTRER (automatisé — veille/traitement.py)                                │
│    • filtre « Madagascar » sur les flux mondiaux                            │
│    • dédoublonnage : URL normalisée (utrm retirés) + empreinte de titre     │
│    • normalisation : accents, casse, espaces                                │
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ANALYSER (automatisé)                                                      │
│    • classification multi-domaines par mots-clés pondérés (titre × résumé)  │
│    • score de pertinence 0–100 (mots-clés + priorité source + fraîcheur)    │
│    • extraction heuristique des dates limites (6 formats FR/EN/ISO)        │
│    • stockage SQLite (data/veille.db) — items, sources, cycles              │
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DIFFUSER (automatisé + 30 min/semaine d'humain)                            │
│    • digest Markdown hebdomadaire (data/rapports/YYYY-MM-JJ_digest.md)      │
│    • tableau de bord HTML autonome (data/dashboard/index.html)              │
│    • export CSV (data/exports/) — réutilisable tableur/CRM                  │
│    • e-mail optionnel (SMTP)                                                │
│    • workflow de décision : nouveau → lu → à suivre → go / no-go            │
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PILOTER (humain, revue mensuelle — 30 min)                                 │
│    • santé des sources (python -m veille verifier)                          │
│    • ajustement des mots-clés / priorités / statuts                         │
│    • KPI : couverture, fraîcheur, faux positifs, taux de conversion         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Principe clé : toute la configuration utile est déclarative** (`config/*.yml`).
Ajouter une source, un mot-clé, changer un seuil ou un sélecteur CSS = éditer du
YAML, jamais du code. Le code (paquet `veille/`) est le moteur générique.

---

## 4. Le registre des sources

Document de référence : **`docs/registre_sources.md`** (généré par
`python -m veille registre` depuis `config/sources.yml`).

Règles de gestion du registre :

- chaque source porte un **statut** : 🟢 opérationnel / 🟠 à calibrer / 🔵 manuel ;
  au déploiement, `python -m veille verifier` teste chaque connecteur et le statut
  est mis à jour après correction des sélecteurs/URL de flux ;
- chaque source porte une **priorité (1–5)** qui pondère le score de pertinence :
  les sources qui publient *des consultances* priment sur celles qui publient
  *du contexte* ;
- une source muette pendant 4 semaines consécutives est examinée en revue
  (URL changée ? flux supprimé ?) puis soit corrigée, soit archivée ;
- les canaux payants (Devex, DevelopmentAid, UNDB) sont en **manuel** : le système
  documente où et quoi vérifier, la saisie passe par `python -m veille ajouter`.

Couverture actuelle : 29 sources réparties en 5 catégories — opportunités (16),
études/évaluations (3), veille économique (7), investissements (3).

---

## 5. Plan de collecte

| Type de source | Fréquence de collecte | Mode | Volume attendu |
|---|---|---|---|
| Flux RSS bailleurs/ONU (UNDP, BAD) | 2×/semaine (mardi, vendredi) | automatique | 5–20 items |
| API ReliefWeb (jobs + reports) | 2×/semaine | automatique | 5–15 items |
| API indicateurs Banque mondiale | 1×/semaine | automatique | ~5 relevés |
| HTML institutionnels (FID, ARMP, INSTAT, EDBM, ONE) | 1×/semaine | automatique (sélecteurs) | 10–40 items |
| Canaux manuels (UNGM, LinkedIn, EU, presse, réseaux) | passe humaine hebdomadaire guidée par le digest | manuel | 0–10 items |

**Robustesse** (mode dégradé prévu) :
- une source indisponible n'interrompt jamais le cycle : l'erreur est consignée dans
  la table `cycles` et dans le bilan du cycle ;
- le mode `--offline` rejoue le pipeline sur les échantillons (`demo/fixtures/`),
  sans réseau — utile pour tester toute évolution du code sans dépendance externe ;
- un échec réseau global (coupure, DNS) ne corrompt pas la base : chaque insertion
  est transactionnelle.

**Ethique et conformité de la collecte** :
- uniquement des **contenus publics** ; aucune donnée personnelle n'est stockée ;
- user-agent identifiable, un seul passage par source et par cycle, pas de contournement
  de paywall ; avant d'automatiser un site (ex. agrégateurs privés), vérifier CGU et
  `robots.txt` — en cas de doute, garder la source en mode manuel ;
- citation systématique de la source et du lien dans toutes les restitutions.

---

## 6. Traitement et analyse

### 6.1 Dédoublonnage

1. **URL normalisée** (casse du domaine, `/` final, paramètres `utm_*` retirés) :
   un item déjà en base est ignoré — le même avis repris par un agrégateur ne
   crée pas de doublon ;
2. **Empreinte de titre** (minuscules, sans accents ni ponctuation) : un titre déjà
   vu sous une autre URL est inséré mais **marqué `doublon=1`** — le même avis publié
   sur deux canaux reste une information utile (éventuellement avec des dates
   différentes), on préfère marquer que supprimer.

### 6.2 Classification par domaine

- multi-étiquettes : un avis « évaluation + collecte de données » est rattaché aux
  deux domaines ;
- mots-clés **pondérés** : *forts* (ex. « évaluation à mi-parcours ») valent 3,
  *moyens* (ex. « étude ») valent 1 ; un mot-clé dans le **titre** compte ×3,
  dans le résumé ×1 ; le premier match neutralise la portion de texte (pas de
  double comptage « évaluation finale » / « évaluation ») ;
- **rattachement par défaut de source** : les items FID sont d'office rattachés à
  `collecte_donnees` et `evaluation_projet`, les items EDBM à `promotion_investissements`…
  Cela garantit qu'aucun item d'une source mono-domaine n'est perdu par absence de
  mot-clé ;
- seuil d'attribution : score local ≥ 3 (`config/domaines.yml` → `seuils`) ;
- le lexique est **bilingue FR/EN** : les avis des bailleurs sont publiés dans les
  deux langues.

### 6.3 Score de pertinence (0–100)

```
score = Σ points de mots-clés (par domaine, max conservé)
      + priorité de la source (1–5) × 2
      + 8 si publié depuis moins de 7 jours
      (plafonné à 100)
```

Le score **ordonne** la lecture (haut de liste du digest), il ne décide pas :
la décision reste humaine (cf. 6.5).

### 6.4 Extraction des dates limites (heuristique)

Six familles de formats reconnues (ISO `2026-10-03`, FR `3 octobre 2026`,
EN `October 3, 2026`, abrégé UNDP `03-Oct-26`, numérique `03/10/2026`,
numérique US). Priorité : date **proche d'un mot de contexte** (« clôture »,
« deadline », « au plus tard »…) ; sinon première date future plausible ;
fenêtre de validité [J-30 ; J+365]. C'est une heuristique assumée : la date
affichée dans le digest doit toujours être vérifiée sur l'avis original avant
d'engager une réponse — c'est le rôle du champ « à vérifier » du workflow.

### 6.5 Workflow de décision humain (le cœur de la méthode)

Chaque item porte un **statut** piloté à la main :

```
nouveau ──lu──▶ [pas pertinent] ──▶ no_go (archivé, purge après 18 mois)
   │
   └─lu─▶ [pertinent mais pas pour moi maintenant] ──▶ a_suivre (reste visible)
   │
   └─lu─▶ [je candidate / je sollicite] ──▶ go (conservé durablement)
```

Commandes : `python -m veille statut <id> go|a_suivre|no_go|lu`.
Le passage manuel sur le digest (§7) est le moment de ces décisions :
compter ~30 minutes, deux fois par semaine.

---

## 7. Diffusion et capitalisation

| Livrable | Format | Fréquence | Destination |
|---|---|---|---|
| **Digest** | Markdown (`data/rapports/`) | 2×/semaine (mardi/vendredi) | lecture humaine, socle de la passe de décision |
| **Tableau de bord** | HTML autonome (`data/dashboard/index.html`) | régénéré à chaque cycle | filtres domaines/sources/statuts/recherche — ouvrable partout, publiable (Pages) |
| **Export CSV** | `data/exports/` | à la demande | tableur, CRM, pipeline commercial |
| **E-mail** | texte (SMTP optionnel) | à chaque digest | diffusion à une équipe |
| **Base SQLite** | `data/veille.db` | continu | historique, stats, requêtes ad hoc |

Le digest suit une structure fixe : synthèse chiffrée → sections par domaine
(items triés par score, avec échéance et lien) → **encart « échéances ≤ 10 jours »**
→ rappel du workflow. Cette régularité est volontaire : elle réduit le coût de
lecture et rend l'exécution mesurable.

---

## 8. Automatisation et déploiement

Trois scénarios, du plus simple au plus robuste (documentés dans
`docs/02_guide_outils.md`) :

1. **Local manuel** : `python -m veille collecter && python -m veille rapport && python -m veille dashboard` ;
2. **Local planifié** : cron/Planificateur de tâches 2×/semaine (lignes fournies) ;
3. **GitHub Actions (recommandé)** : workflow `.github/workflows/veille.yml` fourni —
   cycle mardi/vendredi 06:00 UTC, régénération digest + tableau de bord, commit
   automatique sur la branche. Le tableau de bord peut être publié via GitHub Pages
   (dossier `data/dashboard`). Coût : 0 €, maintenance minimale.

Le premier déploiement suit la **procédure d'initialisation** :
1. `pip install -r requirements.txt` ;
2. `python -m veille verifier` → calibrer les sélecteurs/URL des sources 🟠 (les
   ajustements se font dans `config/sources.yml`) ;
3. `python -m veille collecter` → premier cycle réel ;
4. `python -m veille rapport` et `python -m veille dashboard` → premiers livrables ;
5. revoir le lexique (`config/domaines.yml`) après 2 semaines sur la base des faux
   positifs/négatifs observés.

---

## 9. Gouvernance : faire vivre le système

### 9.1 Revue mensuelle (30 minutes, rituel calé au calendrier)

- lancer `python -m veille verifier` et traiter les sources en erreur ;
- compter les items par source sur 30 jours (`python -m veille stats`) : une source
  qui ne produit rien est recalibrée ou archivée ;
- relire un échantillon de 20 items : faux positifs → durcir le lexique (retirer un
  mot-clé trop générique) ; faux négatifs → l'enrichir ;
- noter les évolutions dans `docs/journal_veille.md` (chronologique).

### 9.2 Indicateurs de santé du système

| Indicateur | Cible | Où le lire |
|---|---|---|
| Taux de sources opérationnelles | ≥ 80 % des sources automatisables | `verifier` |
| Nouveaux items / semaine | 20–60 (sous 10 : couverture à revoir ; au-delà : durcir seuils) | `stats` |
| Items `go` / mois | qualitatif (tendance) | `stats` |
| Faux positifs dans le digest | < 20 % des items non-domaines | lecture du digest |
| Écart publication → détection | ≤ 48 h sur les sources quotidiennes | comparaison dates |

### 9.3 Feuille de route d'enrichissement (phases 2 et 3)

- **P2 (court terme)** : calibrage réel des sources 🟠 au premier déploiement ;
  notification e-mail activée ; publication du tableau de bord sur GitHub Pages ;
  comptes/alertes créés sur les canaux 🔵 (UNGM, EU, LinkedIn) ;
- **P3 (moyen terme)** : scoring personnalisé (pondérations apprises sur les items
  `go`), veille « projects pipeline » systématique (API projets Banque mondiale /
  BAD → alerte avant les avis), résumés automatiques des avis longs (LLM local ou
  API), tableau de bord comparé des concurrents (qui gagne quel type de marché),
  extension géographique (Comores, Maurice, La Réunion — marchés voisins accessibles).

---

## 10. Ce qui est livré dans ce dépôt

```
config/
  sources.yml          ← registre des sources (29) — à faire vivre
  domaines.yml         ← lexique de classification + pondérations + seuils
  settings.yml         ← chemins, fréquences, rétention, notification
veille/
  __main__.py          ← CLI (collecter, demo, verifier, rapport, dashboard,
  pipeline.py            exporter, ajouter, statut, stats, registre)
  modele.py            ← schéma SQLite + dédoublonnage
  traitement.py        ← normalisation, classification, scoring, dates limites
  rapports.py          ← digest Markdown + export CSV
  dashboard.py         ← tableau de bord HTML autonome
  notifier.py          ← e-mail optionnel (SMTP)
  collecteurs/         ← 4 connecteurs (rss, reliefweb, worldbank, html)
tests/                 ← 23 tests unitaires (moteur + connecteurs)
demo/fixtures/         ← échantillons hors-ligne aux formats réels
data/                  ← base, rapports, exports, tableau de bord (générés)
.github/workflows/     ← automatisation GitHub Actions
docs/                  ← méthodologie (ce document), guide outils, registre
```

*Dernière mise à jour : 2026-09-12.*
