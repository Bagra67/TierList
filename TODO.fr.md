# TODO

[English](TODO.md) | Français

Étapes manuelles restantes : configuration, vérifications dans un navigateur, merges et décisions qui ne se font pas depuis le code. Cochez un point une fois fait, et supprimez une section une fois vide.

## 1. Avant le premier déploiement

- [ ] Choisir un hébergement, puis écrire les images Docker de production et le déploiement (décision ouverte, voir l'[architecture](docs/architecture.fr.md#décisions-en-attente)).
- [ ] Réglages de production (`backend/.env` ou variables de l'hébergeur) :
  - une `JWT_SECRET_KEY` différente de celle de développement ;
  - `AUTH_COOKIE_SECURE=true` (la valeur par défaut) et HTTPS ;
  - un `POSTGRES_PASSWORD` robuste.
- [ ] Emails en production ([guide des emails](docs/emails.fr.md#4-en-production)) : choisir un fournisseur SMTP, autoriser le domaine (SPF, DKIM, DMARC), renseigner `SMTP_*`, `EMAIL_FROM` et `FRONTEND_BASE_URL`.
- [ ] Limiter les tentatives répétées (connexion, inscription, emails) au niveau de l'hébergeur (proxy, Cloudflare…), et configurer les en-têtes de proxy de confiance (`X-Forwarded-For`, `--forwarded-allow-ips`) pour que le backend voie la vraie IP.
- [ ] Google en production : ajouter l'URI de redirection HTTPS au client OAuth, y faire pointer `GOOGLE_REDIRECT_URI`, et publier l'écran de consentement (en mode « Test », seuls les utilisateurs test peuvent se connecter).

## 2. Décisions à prendre

- [ ] Fonctionnalités pas encore disponibles ([guide de l'authentification](docs/authentication.fr.md#pas-encore-disponible)) : autres fournisseurs d'identité (Discord, GitHub…), à ajouter avec le premier réellement voulu. La limitation des tentatives est prévue au niveau de l'hébergeur (voir « Avant le premier déploiement »).
- [ ] Charte graphique (couleur d'accent, typographie, logo), **une fois l'éditeur de tier list et une ou deux fonctionnalités autour en place**, pour la concevoir sur de vrais écrans. D'ici là : uniquement les jetons du thème (`bg-primary`, `text-muted-foreground`…), aucune couleur en dur, pour que la charte se résume surtout à changer les variables de `frontend/src/index.css` ([README du frontend](frontend/README.fr.md#10-composants-dinterface)). Les couleurs des tiers (S, A, B…) se décident avec l'éditeur, en jetons clair et sombre.
- [ ] Passage en version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), quand l'API sera jugée stable.
