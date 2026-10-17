# TODO

[English](TODO.md) | Français

Étapes manuelles restantes : configuration, vérifications dans un navigateur, merges et décisions qui ne se font pas depuis le code. Cochez un point une fois fait, et supprimez une section une fois vide.

## 1. Avant le premier déploiement

- [x] Choisir un hébergement : pods MineStrator derrière un Cloudflare Tunnel ([guide du déploiement](docs/technical/deployment.fr.md)).
- [x] Bundle de release, script de démarrage du pod et déploiement continu (#158, #160, #161).
- [x] Créer les pods, le tunnel et les environnements GitHub, puis déployer le staging : [premier déploiement](docs/technical/deployment.fr.md#5-premier-déploiement-pas-à-pas) (#159, #163).
- [ ] Pareil pour la production ([production](docs/technical/deployment.fr.md#59-production)) : pod de production, base `tierlist_prod`, route `tierlist.ladwein.dev`, environnements `production` et `backup-production`.
- [ ] Afficher les pods en ligne dans le panel MineStrator : écrire `change this part` une fois que l'application répond (`deploy/start.sh`) et dans la commande de démarrage du tunnel ([pods](docs/technical/deployment.fr.md#51-pods-minestrator-159)).
- [ ] Durcir PostgreSQL : `scram-sha-256`, pas de superutilisateur à distance ([PostgreSQL](docs/technical/deployment.fr.md#52-postgresql)).
- [ ] Réglages de production (environnements GitHub, [guide du déploiement](docs/technical/deployment.fr.md#4-environnements-secrets-et-variables-github)) :
  - une `JWT_SECRET_KEY` différente de celle de développement ;
  - `AUTH_COOKIE_SECURE=true` (la valeur par défaut) et HTTPS ;
  - un `POSTGRES_PASSWORD` robuste.
- [ ] Emails en production ([guide des emails](docs/technical/emails.fr.md#4-en-production)) : choisir un fournisseur SMTP, autoriser le domaine (SPF, DKIM, DMARC), renseigner `SMTP_*`, `EMAIL_FROM` et `FRONTEND_BASE_URL`. Fait sur le staging : Scaleway Transactional Email, domaine `ladwein.dev` vérifié ([Scaleway](docs/technical/deployment.fr.md#54-scaleway-163)).
- [ ] Limiter les tentatives répétées (connexion, inscription, emails) au niveau de l'hébergeur (règles de limitation de Cloudflare). Les en-têtes de proxy de confiance sont réglés (`TRUSTED_PROXY_IPS`, `--forwarded-allow-ips`).
- [ ] Google en production : ajouter l'URI de redirection HTTPS au client OAuth, y faire pointer `GOOGLE_REDIRECT_URI`, et publier l'écran de consentement (en mode « Test », seuls les utilisateurs test peuvent se connecter).
- [x] Purge des templates supprimés et des images inutilisées chaque nuit : dans le processus de l'application (#192, `MAINTENANCE_ENABLED`).
- [ ] Sauvegardes de la base : configurer les environnements `backup-*` et essayer une restauration sur le staging (#162).
- [ ] Images des tuiles ([guide des images](docs/technical/images.fr.md#27-stockage-et-service)), une fois #81 construite : Scaleway Object Storage, un bucket par environnement en lecture publique, les réglages `IMAGE_*` dans les environnements GitHub (fait sur le staging ; **les envois ne posent pas encore l'ACL `public-read`**, [Scaleway](docs/technical/deployment.fr.md#54-scaleway-163)) ; plus tard, un CDN capable de **purger une URL** (nécessaire pour masquer une image).

## 2. Décisions à prendre

- [ ] Fonctionnalités pas encore disponibles ([guide de l'authentification](docs/technical/authentication.fr.md#pas-encore-disponible)) : autres fournisseurs d'identité (Discord, GitHub…), à ajouter avec le premier réellement voulu. La limitation des tentatives est prévue au niveau de l'hébergeur (voir « Avant le premier déploiement »).
- [ ] Charte graphique (couleur d'accent, typographie, logo), **une fois l'éditeur de tier list et une ou deux fonctionnalités autour en place**, pour la concevoir sur de vrais écrans. D'ici là : uniquement les jetons du thème (`bg-primary`, `text-muted-foreground`…), aucune couleur en dur, pour que la charte se résume surtout à changer les variables de `frontend/src/index.css` ([README du frontend](frontend/README.fr.md#10-composants-dinterface)). Les couleurs des tiers (S, A, B…) se décident avec l'éditeur, en jetons clair et sombre.
- [ ] Passage en version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), quand l'API sera jugée stable.

## 3. Outillage

- [ ] **Tests de bout en bout (Playwright)**, à mettre en place **avec l'éditeur de tier list**, pas avant.
  - _Ce qu'ils apportent_ : les tests actuels tournent dans Vitest avec jsdom, un navigateur simulé avec un backend remplacé. Ils ne voient pas ce que seul un vrai navigateur fait : les cookies HttpOnly et le rafraîchissement de session face au vrai backend, le focus et `Échap` dans le `<dialog>` (`src/test/setup.ts` note que jsdom ne sait pas les tester), la mise en page, et surtout le **glisser-déposer** de l'éditeur. Playwright pilote Chromium, Firefox ou WebKit sur l'application lancée (backend + PostgreSQL + Mailpit).
  - _Coût_ : un job CI qui démarre PostgreSQL, Mailpit, le backend et le frontend (quelques minutes par PR) ; des tests plus lents et parfois instables (délais, animations) ; et de la maintenance à chaque changement d'écran (sélecteurs, parcours).
  - _Recommandation_ : **pas un test par écran**. Une poignée de parcours critiques (« smoke tests ») : inscription → confirmation de l'email (lien lu via l'API de Mailpit) → connexion → déconnexion, puis créer une tier list et déplacer des éléments entre les tiers. Tout le reste reste dans Vitest, rapide et stable. On n'ajoute un parcours que si une régression dessus serait grave et que jsdom ne peut pas la voir.
