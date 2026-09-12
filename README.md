# Système de veille — Activités de consultance à Madagascar

Veille des opportunités de consultance (évaluation de projets, collecte de données,
études et recherches), de la conjoncture économique et de la promotion des
investissements à Madagascar.

**Le système est livré opérationnel** : collecte automatisée multi-sources,
classification par domaine, scoring de pertinence, détection des dates limites,
digest hebdomadaire, tableau de bord interactif, automatisation GitHub Actions.

## Démarrage express

```bash
pip install -r requirements.txt

# 1. Démonstration complète SANS réseau (échantillons réalistes)
python -m veille demo
#    → base data/veille.db, digest data/rapports/, tableau de bord data/dashboard/

# 2. Ouvrir le tableau de bord : double-cliquer sur data/dashboard/index.html
#    (fichier autonome, fonctionne partout)

# 3. Premier cycle réel (nécessite un réseau ouvert)
python -m veille verifier      # santé des 29 sources
python -m veille collecter     # cycle de collecte
python -m veille rapport       # digest Markdown
python -m veille dashboard     # tableau de bord HTML
```

## Documentation

| Document | Contenu |
|---|---|
| **[docs/00_methodologie.md](docs/00_methodologie.md)** | La méthode complète : objectifs, cartographie de la demande, architecture 5 étapes, règles de classification, workflow de décision, gouvernance, feuille de route |
| [docs/02_guide_outils.md](docs/02_guide_outils.md) | Guide d'utilisation : commandes, déploiement, automatisation, dépannage |
| [docs/registre_sources.md](docs/registre_sources.md) | Les 29 sources (généré depuis la configuration) |

## Architecture en 5 étapes

```
RELEVER → FILTRER → ANALYSER → DIFFUSER → PILOTER
(4 connecteurs : RSS, API ReliefWeb, API Banque mondiale, HTML piloté)
(dédoublonnage URL + titre, filtre Madagascar)
(classification multi-domaines, score 0–100, dates limites)
(digest MD, dashboard HTML, CSV, e-mail optionnel)
(revue mensuelle : verifier, stats, ajustement des YAML)
```

**Toute la configuration est déclarative** : ajouter une source ou un mot-clé =
éditer `config/sources.yml` ou `config/domaines.yml`, jamais le code.

## Automatisation

Le workflow [`.github/workflows/veille.yml`](.github/workflows/veille.yml) exécute
le cycle **mardi et vendredi à 06:00 UTC**, régénère les livrables et les archive
sur la branche. Activation : rien à faire si le dépôt est sur GitHub (Actions
activées). Publication web du tableau de bord possible via GitHub Pages.

## Qualité

- 23 tests unitaires (`python -m pytest tests/ -v`) : classification FR/EN,
  dédoublonnage, extraction de dates (6 formats), parsing des 4 connecteurs ;
- mode démonstration hors-ligne intégré (échantillons aux formats réels des sources) ;
- échec d'une source ≠ échec du cycle : erreurs consignées, base transactionnelle.
