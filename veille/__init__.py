"""Système de veille — activités de consultance à Madagascar.

Pipeline en 5 étapes : Relever -> Filtrer -> Analyser -> Diffuser -> Piloter.

Utilisation :
    python -m veille <commande> [options]

Principales commandes :
    collecter    cycle complet de collecte (sources actives)
    demo         cycle complet sur le jeu d'échantillons hors-ligne (aucun réseau)
    verifier     diagnostic de santé des sources (HTTP + parsing)
    rapport      génération du digest Markdown
    dashboard    génération du tableau de bord HTML
    exporter     export CSV des items
    ajouter      consigner manuellement une opportunité (LinkedIn, bouche-à-oreille…)
    statut       faire évoluer le statut d'un item (a_suivre / go / no_go / lu)
    stats        indicateurs du système
"""

__version__ = "1.0.0"
