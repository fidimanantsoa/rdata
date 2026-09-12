# Guide d'utilisation des outils

> Prérequis : Python 3.10+. Installation : `pip install -r requirements.txt`.
> Aucune configuration supplémentaire n'est nécessaire pour le mode démonstration.

---

## 1. Commandes de référence

| Commande | Rôle | Fréquence d'usage |
|---|---|---|
| `python -m veille demo` | **pipeline complet hors-ligne** sur les échantillons — à essayer en premier | tests, formations |
| `python -m veille collecter` | cycle de collecte réel (réseau) | 2×/semaine (automatisé) |
| `python -m veille verifier` | santé des sources : HTTP + parsing + aperçu | revue mensuelle, déploiement |
| `python -m veille rapport` | digest Markdown de la période (`--jours N`) | 2×/semaine (automatisé) |
| `python -m veille dashboard` | tableau de bord HTML autonome | à chaque cycle (automatisé) |
| `python -m veille exporter` | export CSV (`--jours N`, 0 = tout) | à la demande |
| `python -m veille ajouter <source> "<titre>" <url> --resume "…"` | consigner une opportunité manuelle (LinkedIn, WhatsApp…) | au fil de l'eau |
| `python -m veille statut <id> go\|a_suivre\|no_go\|lu` | workflow de décision | pendant la lecture du digest |
| `python -m veille stats` | volumes, statuts, top sources, derniers cycles | revue mensuelle |
| `python -m veille registre` | régénère `docs/registre_sources.md` | après édition de sources.yml |
| `python -m pytest tests/ -v` | 23 tests unitaires du moteur | après toute évolution |

Sous-ensemble de sources : `python -m veille collecter --sources undp_pn,fid_ao`.
Mode hors-ligne du collecteur : `python -m veille collecter --offline`.

## 2. Premier déploiement (poste local)

```bash
pip install -r requirements.txt

# 1. Démonstration sans réseau : comprendre ce que produit le système
python -m veille demo

# 2. Diagnostic des sources réelles
python -m veille verifier
#    → les sources 🟠 échouent ou retournent des items parasites :
#      ajuster leurs sélecteurs CSS / URL de flux dans config/sources.yml
#      puis relancer jusqu'à obtention d'items propres
#    → mettre à jour le champ `statut: operationnel` des sources calibrées

# 3. Premier cycle réel + livrables
python -m veille collecter
python -m veille rapport
python -m veille dashboard

# 4. Vérifier les résultats
python -m veille stats
```

## 3. Automatisation

### 3.1 GitHub Actions (recommandé — inclus)

Le workflow `.github/workflows/veille.yml` :
- s'exécute **mardi et vendredi à 06:00 UTC** (`cron: "0 6 * * 2,5"`) et à la demande
  (onglet Actions → *Run workflow*) ;
- installe les dépendances, lance le cycle, régénère digest + tableau de bord ;
- **commite automatiquement** la base et les livrables sur la branche active.

Après activation, le tableau de bord peut être publié en continu via GitHub Pages :
*Settings → Pages → Deploy from a branch → branche `main`, dossier `/data/dashboard`*.

### 3.2 Cron local (alternative)

```cron
# mardi et vendredi, 07h30 (heure locale)
30 7 * * 2,5  cd /chemin/vers/rdata && python -m veille collecter >> data/cycle.log 2>&1
35 7 * * 2,5  cd /chemin/vers/rdata && python -m veille rapport >> data/cycle.log 2>&1
36 7 * * 2,5  cd /chemin/vers/rdata && python -m veille dashboard >> data/cycle.log 2>&1
```

## 4. Configuration utile

### Ajouter une source (aucun code)

Dans `config/sources.yml`, ajouter une entrée :

```yaml
  - id: ma_nouvelle_source          # identifiant unique
    nom: "Nom lisible"
    categorie: opportunites          # ou etudes / veille_economique / investissements / presse
    type: rss                        # rss | api_reliefweb | api_wb_indicateurs | html | manuel
    url: "https://exemple.mg/flux.xml"
    priorite: 4                      # 1–5, pondère le score
    frequence: hebdomadaire
    statut: a_valider                # -> operationnel après calibrage (verifier)
    domaines_defaut: [etudes_recherches]
```

Puis `python -m veille verifier --sources ma_nouvelle_source`, calibrer, et
`python -m veille registre` pour mettre à jour la documentation.

### Ajuster la classification

Tout est dans `config/domaines.yml` : ajouter/retirer des mots-clés (forts/moyens,
FR/EN), modifier le seuil d'attribution ou les pondérations. Rejouer
`python -m pytest tests/` puis `python -m veille demo` pour visualiser l'effet.

### Activer l'e-mail

1. dans `config/settings.yml` : `notification.actif: true` ;
2. définir les variables d'environnement : `VEILLE_SMTP_HOTE`, `VEILLE_SMTP_PORT`,
   `VEILLE_SMTP_UTILISATEUR`, `VEILLE_SMTP_MOTDEPASSE`, `VEILLE_EMAIL_DESTINATAIRES` ;
3. le digest partira à chaque `python -m veille rapport`.

## 5. Dépannage

| Symptôme | Cause probable | Remède |
|---|---|---|
| Source en erreur `HTTPSConnectionPool` | site indisponible ou réseau restreint | relancer plus tard ; si persistant, l'URL a changé |
| Source ✗ mais site accessible | sélecteurs CSS obsolètes (refonte du site) | inspecter la page, mettre à jour `selecteurs` |
| Beaucoup d'items sans domaine | lexique incomplet ou source bruitée | enrichir `domaines.yml` ou filtrer via `filtre_inclut` |
| Dates limites erronées | heuristique (formats ambigus) | vérifier sur l'avis original — signalées « à vérifier » |
| Base corrompue | interruption en cours d'écriture | restaurer depuis git (la base est versionnée à chaque cycle) |

## 6. Accès direct à la base

```bash
sqlite3 data/veille.db
sqlite> SELECT titre, date_limite, score FROM items
        WHERE statut='a_suivre' ORDER BY date_limite;
sqlite> SELECT source_id, COUNT(*) FROM items
        WHERE cree_le >= date('now','-30 days') GROUP BY source_id;
```
