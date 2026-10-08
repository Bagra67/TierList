# TODO

[English](TODO.md) | Français

Étapes manuelles restantes : configuration, vérifications dans un navigateur, merges et décisions qui ne se font pas depuis le code. Cochez un point une fois fait, et supprimez une section une fois vide.

## 1. Avant le premier déploiement

- [ ] Choisir un hébergement, puis écrire les images Docker de production et le déploiement (décision ouverte, voir l'[architecture](docs/technical/architecture.fr.md#décisions-en-attente)).
- [ ] Réglages de production (`backend/.env` ou variables de l'hébergeur) :
  - une `JWT_SECRET_KEY` différente de celle de développement ;
  - `AUTH_COOKIE_SECURE=true` (la valeur par défaut) et HTTPS ;
  - un `POSTGRES_PASSWORD` robuste.
- [ ] Emails en production ([guide des emails](docs/technical/emails.fr.md#4-en-production)) : choisir un fournisseur SMTP, autoriser le domaine (SPF, DKIM, DMARC), renseigner `SMTP_*`, `EMAIL_FROM` et `FRONTEND_BASE_URL`.
- [ ] Limiter les tentatives répétées (connexion, inscription, emails) au niveau de l'hébergeur (proxy, Cloudflare…), et configurer les en-têtes de proxy de confiance (`X-Forwarded-For`, `--forwarded-allow-ips`) pour que le backend voie la vraie IP.
- [ ] Google en production : ajouter l'URI de redirection HTTPS au client OAuth, y faire pointer `GOOGLE_REDIRECT_URI`, et publier l'écran de consentement (en mode « Test », seuls les utilisateurs test peuvent se connecter).
- [ ] Planifier la purge des templates supprimés une fois par jour : `uv run python scripts/purge_deleted_templates.py` dans `backend/` (cron ou tâche planifiée de l'hébergeur). Sans elle, les templates supprimés restent en base ; la durée de conservation est `DELETED_TEMPLATE_RETENTION_DAYS` (30 jours par défaut).

## 2. Décisions à prendre

- [ ] Fonctionnalités pas encore disponibles ([guide de l'authentification](docs/technical/authentication.fr.md#pas-encore-disponible)) : autres fournisseurs d'identité (Discord, GitHub…), à ajouter avec le premier réellement voulu. La limitation des tentatives est prévue au niveau de l'hébergeur (voir « Avant le premier déploiement »).
- [ ] Charte graphique (couleur d'accent, typographie, logo), **une fois l'éditeur de tier list et une ou deux fonctionnalités autour en place**, pour la concevoir sur de vrais écrans. D'ici là : uniquement les jetons du thème (`bg-primary`, `text-muted-foreground`…), aucune couleur en dur, pour que la charte se résume surtout à changer les variables de `frontend/src/index.css` ([README du frontend](frontend/README.fr.md#10-composants-dinterface)). Les couleurs des tiers (S, A, B…) se décident avec l'éditeur, en jetons clair et sombre.
- [ ] Passage en version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), quand l'API sera jugée stable.

## 3. Outillage

- [ ] **Tests de bout en bout (Playwright)**, à mettre en place **avec l'éditeur de tier list**, pas avant.
  - _Ce qu'ils apportent_ : les tests actuels tournent dans Vitest avec jsdom, un navigateur simulé avec un backend remplacé. Ils ne voient pas ce que seul un vrai navigateur fait : les cookies HttpOnly et le rafraîchissement de session face au vrai backend, le focus et `Échap` dans le `<dialog>` (`src/test/setup.ts` note que jsdom ne sait pas les tester), la mise en page, et surtout le **glisser-déposer** de l'éditeur. Playwright pilote Chromium, Firefox ou WebKit sur l'application lancée (backend + PostgreSQL + Mailpit).
  - _Coût_ : un job CI qui démarre PostgreSQL, Mailpit, le backend et le frontend (quelques minutes par PR) ; des tests plus lents et parfois instables (délais, animations) ; et de la maintenance à chaque changement d'écran (sélecteurs, parcours).
  - _Recommandation_ : **pas un test par écran**. Une poignée de parcours critiques (« smoke tests ») : inscription → confirmation de l'email (lien lu via l'API de Mailpit) → connexion → déconnexion, puis créer une tier list et déplacer des éléments entre les tiers. Tout le reste reste dans Vitest, rapide et stable. On n'ajoute un parcours que si une régression dessus serait grave et que jsdom ne peut pas la voir.
