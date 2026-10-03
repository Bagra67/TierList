# TODO

[English](TODO.md) | Français

Étapes manuelles restantes : configuration, vérifications dans un navigateur, merges et décisions qui ne se font pas depuis le code. Cochez un point une fois fait, et supprimez une section une fois vide.

## 1. Configuration locale

- [ ] Créer `backend/.env` à partir de `backend/.env.example` (si ce n'est pas encore fait), et remplacer :
  - `POSTGRES_PASSWORD` (`changez-moi`) ;
  - `JWT_SECRET_KEY` par une clé aléatoire : `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` (dans `backend/`).
- [ ] **Configurer la connexion avec Google** (Google Cloud Console → API et services → Identifiants), voir le [guide de l'authentification](docs/authentication.fr.md#2-fonctionnement-technique), « Configurer Google » :
  1. configurer l'écran de consentement OAuth (nom de l'application, email d'assistance ; scopes `openid`, `email`, `profile`), et ajouter votre compte Google comme utilisateur test tant que l'écran est en mode « Test » ;
  2. créer un **ID client OAuth** de type **Application Web** ;
  3. ajouter l'URI de redirection autorisé `http://localhost:5173/api/auth/google/callback` (il doit être identique à `GOOGLE_REDIRECT_URI`) ;
  4. copier l'ID client et le secret dans `backend/.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), puis redémarrer le backend.

## 2. Vérifications dans un navigateur (`dev.ps1`)

- [ ] **Connexion avec Google**, une fois configurée :
  - « Continuer avec Google » crée un compte sans mot de passe et ouvre la page d'accueil ;
  - avec un email déjà inscrit par mot de passe, la connexion Google se relie à ce compte ;
  - annuler sur la page de Google affiche « Connexion avec Google annulée » sur `/login` ;
  - supprimer un compte Google plus de 5 minutes après la connexion demande de se reconnecter avec Google, puis rouvre le dialogue de suppression.
- [ ] **Traductions (#32)** :
  - avec un navigateur en anglais, l'interface est en anglais ;
  - le sélecteur de langue repasse en français, et le choix tient après un rechargement ;
  - une inscription avec un mot de passe trop court affiche « Le mot de passe doit contenir au moins 8 caractères » (en français) / « The password must be at least 8 characters long » (en anglais) ;
  - un mauvais mot de passe à la connexion affiche le message traduit ;
  - `/login?error=google_cancelled` affiche le message dans les deux langues.

## 3. Release

- [ ] Publier la prochaine release : `develop` contient des fonctionnalités pas encore publiées (inscription et connexion par email / mot de passe, suppression du compte, connexion avec Google, traductions). Suivre [docs/releasing.fr.md](docs/releasing.fr.md) : `scripts/prepare-release.sh` sur une branche `chore/release-vX.Y.Z`, puis la PR de release `develop` → `main` avec un **merge commit**.
- [ ] Après la release, vérifier que `origin/develop` existe toujours.

## 4. Avant le premier déploiement

- [ ] Choisir un hébergement, puis écrire les images Docker de production et le déploiement (décision ouverte, voir l'[architecture](docs/architecture.fr.md#décisions-en-attente)).
- [ ] Réglages de production (`backend/.env` ou variables de l'hébergeur) :
  - une `JWT_SECRET_KEY` différente de celle de développement ;
  - `AUTH_COOKIE_SECURE=true` (la valeur par défaut) et HTTPS ;
  - un `POSTGRES_PASSWORD` robuste.
- [ ] Google en production : ajouter l'URI de redirection HTTPS au client OAuth, y faire pointer `GOOGLE_REDIRECT_URI`, et publier l'écran de consentement (en mode « Test », seuls les utilisateurs test peuvent se connecter).

## 5. Décisions à prendre

- [ ] Bibliothèque d'interface (décision ouverte, voir l'[architecture](docs/architecture.fr.md#décisions-en-attente)).
- [ ] Fonctionnalités pas encore disponibles ([guide de l'authentification](docs/authentication.fr.md#pas-encore-disponible)) : vérification de l'adresse email et « mot de passe oublié » (il faut choisir un service d'envoi d'emails), limitation des tentatives de connexion répétées, autres fournisseurs d'identité.
- [ ] Passage en version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), quand l'API sera jugée stable.
