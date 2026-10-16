[English](emails.md) | Français

# Emails

Le backend envoie des emails transactionnels (vérification de l'adresse email, réinitialisation du mot de passe) par **SMTP**. Le fournisseur n'est qu'une configuration : en changer ne demande pas de modifier le code.

## 1. Fonctionnement

| Élément            | Où                                   | Rôle                                                                                                                    |
| ------------------ | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `Email`            | `backend/app/services/email.py`      | Un email : destinataire, sujet, version texte et version HTML.                                                          |
| `EmailSender`      | `backend/app/services/email.py`      | Envoie un `Email` avec `smtplib` (bibliothèque standard), avec STARTTLS et identification quand elles sont configurées. |
| `get_email_sender` | `backend/app/api/dependencies.py`    | Injecte l'expéditeur dans les routes ; les tests le remplacent par un faux qui garde les emails.                        |
| Réglages SMTP      | `backend/app/core/config.py`, `.env` | `SMTP_*`, `EMAIL_FROM`, `FRONTEND_BASE_URL` (voir plus bas).                                                            |

- **Envoi après la réponse** (`BackgroundTasks` de FastAPI) : la requête n'attend pas le serveur SMTP, et le temps de réponse ne révèle pas si un email est parti.
- **Un échec est journalisé, jamais levé** : personne ne pourrait le traiter une fois la réponse partie, et l'utilisateur peut redemander l'email. Seul le type d'erreur est journalisé, jamais l'adresse.
- **Sans `SMTP_HOST`**, aucun email ne part : l'envoi est seulement journalisé en avertissement. L'application continue de fonctionner.
- **Les emails sont le seul texte destiné à l'utilisateur produit par le backend.** Ils sont rédigés en français et en anglais, dans la langue envoyée par le frontend. Tout le reste suit la règle habituelle : des codes d'erreur traduits par le frontend ([guide i18n](i18n.fr.md)).

## 2. En développement : Mailpit

[Mailpit](https://mailpit.axllent.org/) (`compose.yaml`) reçoit les emails **sans jamais les distribuer** : on peut écrire à n'importe quelle adresse sans risque.

- Il démarre avec la base : `docker compose up -d --wait` (ou `dev.ps1` / `dev.sh`).
- Les emails se lisent sur **http://localhost:8025**.
- `backend/.env.example` pointe déjà vers lui : `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_STARTTLS=false`.

## 3. Réglages

| Variable               | Rôle                                                                          | Défaut                          |
| ---------------------- | ----------------------------------------------------------------------------- | ------------------------------- |
| `SMTP_HOST`            | Serveur SMTP ; sans lui, aucun email ne part                                  | — (facultatif)                  |
| `SMTP_PORT`            | Port                                                                          | `587`                           |
| `SMTP_USERNAME`        | Identifiant chez le fournisseur SMTP                                          | — (facultatif)                  |
| `SMTP_PASSWORD`        | Mot de passe ou clé d'API du fournisseur SMTP                                 | — (facultatif)                  |
| `SMTP_STARTTLS`        | Chiffre la connexion avec STARTTLS ; `false` seulement pour Mailpit, en local | `true`                          |
| `SMTP_TIMEOUT_SECONDS` | Délai des échanges avec le serveur SMTP                                       | `10`                            |
| `EMAIL_FROM`           | Expéditeur, ex. `TierList <no-reply@example.com>`                             | `TierList <no-reply@localhost>` |
| `FRONTEND_BASE_URL`    | Adresse du frontend vue par l'utilisateur, base des liens envoyés par email   | `http://localhost:5173`         |

## 4. En production

1. **Choisir un fournisseur** qui propose le SMTP (Brevo, Resend, Postmark, Amazon SES, Mailgun…) et créer des identifiants SMTP (souvent une clé d'API utilisée comme mot de passe).
2. **Autoriser votre domaine** chez le fournisseur : enregistrements DNS SPF, DKIM et DMARC. Sans eux, les emails finissent en spam ou sont refusés.
3. Renseigner `SMTP_HOST`, `SMTP_PORT` (en général `587`), `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` (une adresse du domaine autorisé) et `FRONTEND_BASE_URL` (l'adresse HTTPS du site). Garder `SMTP_STARTTLS=true`.

Le port 465 (TLS implicite, sans STARTTLS) n'est pas géré : tous les fournisseurs ci-dessus proposent aussi le 587.

## 5. Rédiger un email

Les contenus sont dans `backend/app/emails/templates.py`, un jeu de textes par langue (`fr`, `en`), avec une version texte et une version HTML. La langue est celle envoyée par le frontend (champ `language`, français par défaut). Les valeurs choisies par l'utilisateur (nom affiché) sont échappées dans le HTML. Aujourd'hui : la confirmation de l'adresse email (`verification_email`) et la réinitialisation du mot de passe (`password_reset_email`).
