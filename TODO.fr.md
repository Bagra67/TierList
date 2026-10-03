# TODO

[English](TODO.md) | Français

Étapes manuelles restantes : configuration, vérifications dans un navigateur, merges et décisions qui ne se font pas depuis le code. Cochez un point une fois fait, et supprimez une section une fois vide.

## 1. Avant le premier déploiement

- [ ] Choisir un hébergement, puis écrire les images Docker de production et le déploiement (décision ouverte, voir l'[architecture](docs/architecture.fr.md#décisions-en-attente)).
- [ ] Réglages de production (`backend/.env` ou variables de l'hébergeur) :
  - une `JWT_SECRET_KEY` différente de celle de développement ;
  - `AUTH_COOKIE_SECURE=true` (la valeur par défaut) et HTTPS ;
  - un `POSTGRES_PASSWORD` robuste.
- [ ] Google en production : ajouter l'URI de redirection HTTPS au client OAuth, y faire pointer `GOOGLE_REDIRECT_URI`, et publier l'écran de consentement (en mode « Test », seuls les utilisateurs test peuvent se connecter).

## 2. Décisions à prendre

- [ ] Bibliothèque d'interface (décision ouverte, voir l'[architecture](docs/architecture.fr.md#décisions-en-attente)).
- [ ] Fonctionnalités pas encore disponibles ([guide de l'authentification](docs/authentication.fr.md#pas-encore-disponible)) : vérification de l'adresse email et « mot de passe oublié » (il faut choisir un service d'envoi d'emails), limitation des tentatives de connexion répétées, autres fournisseurs d'identité.
- [ ] Passage en version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), quand l'API sera jugée stable.
