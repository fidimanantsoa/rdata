"""Notification e-mail du digest (optionnelle).

S'active en plaçant `notification.actif: true` dans config/settings.yml et en
définissant les variables d'environnement :
    VEILLE_SMTP_HOTE, VEILLE_SMTP_PORT, VEILLE_SMTP_UTILISATEUR,
    VEILLE_SMTP_MOTDEPASSE, VEILLE_EMAIL_DESTINATAIRES (séparées par des virgules)

Le message est envoyé en texte brut (Markdown) pour une délivrabilité maximale.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def envoyer_digest(texte: str, sujet: str = "Digest de veille") -> tuple[bool, str]:
    hote = os.environ.get("VEILLE_SMTP_HOTE", "")
    port = int(os.environ.get("VEILLE_SMTP_PORT", "587"))
    utilisateur = os.environ.get("VEILLE_SMTP_UTILISATEUR", "")
    motdepasse = os.environ.get("VEILLE_SMTP_MOTDEPASSE", "")
    destinataires = [
        d.strip() for d in os.environ.get("VEILLE_EMAIL_DESTINATAIRES", "").split(",") if d.strip()
    ]

    if not all([hote, utilisateur, motdepasse, destinataires]):
        return False, (
            "Notification désactivée : définir VEILLE_SMTP_HOTE, VEILLE_SMTP_PORT, "
            "VEILLE_SMTP_UTILISATEUR, VEILLE_SMTP_MOTDEPASSE et VEILLE_EMAIL_DESTINATAIRES."
        )

    message = EmailMessage()
    message["Subject"] = sujet
    message["From"] = utilisateur
    message["To"] = ", ".join(destinataires)
    message.set_content(texte)

    try:
        with smtplib.SMTP(hote, port, timeout=30) as serveur:
            serveur.starttls()
            serveur.login(utilisateur, motdepasse)
            serveur.send_message(message)
        return True, f"Digest envoyé à {len(destinataires)} destinataire(s)."
    except (smtplib.SMTPException, OSError) as e:
        return False, f"Échec d'envoi : {e}"
