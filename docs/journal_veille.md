# Journal de veille du système

*Journal chronologique des évolutions du système (sources, lexique, réglages),
alimenté lors de la revue mensuelle décrite dans la méthodologie (§9.1).*

---

## 2026-09-12 — Mise en place initiale (v1.0.0)

**Contexte** : construction du système de veille selon la demande — la méthode et
les outils avant les résultats.

**Décisions structurantes**

1. **Approche déclarative** : registre de sources, lexique de classification et
   paramètres en YAML ; le code Python est un moteur générique (aucune source
   codée en dur).
2. **4 connecteurs normalisés** : RSS/Atom (feedparser), API ReliefWeb (jobs et
   rapports), API indicateurs Banque mondiale, scraping HTML piloté par sélecteurs
   CSS. Canaux non automatisables documentés comme sources « manuelles ».
3. **Statuts honnêtes des sources** : 29 sources enregistrées ; `operationnel`
   uniquement quand l'accès technique est vérifié (RSS UNDP, API ReliefWeb, API
   indicateurs BM, structure FID) ; `a_valider` pour les sources à calibrer au
   premier déploiement réseau ; `manuel` pour l'inscription/alertes.
4. **Dédoublonnage à deux niveaux** : URL normalisée (ignore) + empreinte de
   titre (marque sans supprimer).
5. **Mode démonstration hors-ligne** : échantillons aux formats réels → le pipeline
   complet est démontrable et testable sans réseau.
6. **Automatisation GitHub Actions** plutôt que serveur : coût nul, maintenance
   minimale, réseau ouvert.

**Réglages initiaux** : seuil d'attribution 3 ; pondérations fort 3 / moyen 1 /
titre ×3 / résumé ×1 ; bonus source priorité×2 ; bonus fraîcheur 8 ; purge à
18 mois ; fenêtre digest 7 jours.

**À traiter à la première revue après déploiement réel** : calibrage des sources
🟠 (BAD, ARMP, INSTAT, EDBM, ONE, presse, PiloConsult), création des comptes
d'alertes des canaux 🔵, activation e-mail, premier ajustement du lexique sur
faux positifs/négatifs observés.
