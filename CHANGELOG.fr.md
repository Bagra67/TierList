# Journal des modifications

[English](CHANGELOG.md) | Français

Tous les changements notables du projet sont consignés dans ce fichier.
Les versions suivent le [Semantic Versioning](https://semver.org/lang/fr/) : voir [docs/technical/releasing.fr.md](docs/technical/releasing.fr.md).

## [0.5.0] - 2026-10-16

### Fonctionnalités

- backend : API CRUD des templates avec des tiers par défaut (#107)
- frontend : page « Mes templates » avec création et suppression (#117)
- configuration des tiers d'un template (#118)
- modification des tuiles texte d'un template (#119)
- décision et calcul des résultats d'une partie (classement médian, votes absents) (#132)
- images : envoi et compression des images des tuiles vers un stockage S3 (#134)
- templates : images rattachées aux tuiles, avec une limite d'envoi et un nettoyage (#135)
- frontend : envoi et affichage des images des tuiles dans l'éditeur de template (#137)
- templates : version figée du template au démarrage d'une partie (#140)
- salles : création des salles et configuration de leurs réglages (#142)
- frontend : création d'une salle et affichage de son lobby (#143)
- salles : rejoindre une salle avec un compte (#144)
- salles : rejoindre une salle en invité (#145)
- salles : suivi en direct d'une salle par un canal WebSocket, avec la présence (#147)
- salles : retrait ou bannissement d'un participant (#149)

### Corrections

- ci : les événements de labels n'annulent plus la vérification des docs (#116)

### Refactorisation

- backend : modèles des utilisateurs séparés et mixins de modèles adoptés (#115)

### Build & CI

- vérification que les docs bilingues et le guide des tests restent synchronisés (#68)
- précision : le workflow de release est lu depuis develop (#108)

### Documentation

- description du produit, des règles du jeu, des permissions et de la roadmap (#69)
- docs séparées en dossiers produit et technique (#70)
- produit : conception du milestone 1 (user stories, domaine, cycles de vie, déroulé, maquettes) (#73)
- décision du transport temps réel des salles (#122)
- décision de l'envoi, de la compression et du stockage des images des tuiles (#129)
- le démarrage d'une partie renvoie à #91 au lieu de #90 (#141)

### Maintenance

- deps : sqlalchemy passe de 2.1.2 à 2.1.3 dans /backend (#110)
- deps : 7 mises à jour du groupe frontend-minor-patch dans /frontend (#111)
- deps-dev : @types/node passe de 24.19.0 à 26.6.4 dans /frontend (#112)
- passage du runtime à Node 26 (#113)
- frontend : serveur de dev Vite servi sur 127.0.0.1 (#121)
- ouverture des liens de dev dans le navigateur au lancement de dev.sh (#131)
- deps : astral-sh/setup-uv passe de 10.2.0 à 10.3.0 (#150)
- deps : 3 mises à jour du groupe backend-minor-patch dans /backend (#151)
- deps : 12 mises à jour du groupe frontend-minor-patch dans /frontend (#152)

## [0.4.0] - 2026-10-04

### Fonctionnalités

- backend : refus des access tokens émis avant une déconnexion ou une réinitialisation du mot de passe (#56)
- frontend : page « introuvable » pour les adresses inconnues (#61)
- frontend : les erreurs d'affichage sont rattrapées par une error boundary (#62)

### Corrections

- backend : gestion de deux premières connexions Google simultanées (#54)
- backend : suppression des refresh tokens expirés à la connexion (#55)
- frontend : un utilisateur connecté est redirigé hors des pages de connexion (#60)

### Refactorisation

- backend : noms déterministes pour les contraintes de la base (#52)
- frontend : vérification des erreurs d'API mise en commun (#58)
- frontend : mise en page des pages de compte et message d'erreur mis en commun (#59)

### Documentation

- todo : tests de bout en bout prévus avec l'éditeur de tier list (#64)

### Tests

- backend : vérification que les migrations correspondent aux modèles (#51)

### Maintenance

- retrait de la démo Hello World (#57)
- frontend : lint d'accessibilité avec eslint-plugin-jsx-a11y-x (#63)
- frontend : détection des exports, fichiers et dépendances inutilisés avec knip (#65)

## [0.3.0] - 2026-10-03

### Fonctionnalités

- frontend : Tailwind CSS et shadcn/ui comme bibliothèque d'interface (#41)
- frontend : mode sombre (clair / sombre / système) (#42)
- backend : envoi des emails transactionnels par SMTP (#45)
- vérification de l'adresse email par un lien envoyé par email (#46)
- réinitialisation d'un mot de passe oublié par un lien envoyé par email (#48)

### Corrections

- backend : tolérance au décalage d'horloge lors de la vérification des id_token Google (#39)

### Documentation

- CHANGELOG en français, tenu à jour par le script de release (#38)
- todo : retrait des sections terminées (configuration, vérifications, release) (#40)
- todo : charte graphique prévue une fois l'éditeur de tier list en place (#44)

## [0.2.0] - 2026-10-03

### Fonctionnalités

- auth : inscription et connexion par e-mail et mot de passe (#26)
- auth : suppression de son compte par l'utilisateur (#27)
- auth : connexion avec Google (#29)
- api : code d'erreur stable dans chaque réponse d'erreur (#31)
- frontend : interface traduite en anglais (i18n fr / en) (#32)

### Refactorisation

- regroupement des constantes, des réglages et des exceptions (#30)

### Build & CI

- release : `pnpm version` ne vérifie plus que l'arbre de travail est propre (#35)

### Documentation

- agents : pourquoi la suppression automatique des branches fusionnées est désactivée (#25)
- agents : fusion d'une pile de PR avec `gh stack merge` (#34)

## [0.1.0] - 2026-10-02

### Fonctionnalités

- backend : configuration des logs de l'application (#5)
- frontend : données serveur récupérées avec TanStack Query et openapi-fetch (#10)
- backend : toutes les erreurs de l'API dans un format JSON unique (#12)
- backend : sonde de vie /health indépendante de la base de données (#13)
- dev : démarrage de la base de données par les scripts de dev (#14)

### Build & CI

- mise en place de GitHub Actions, du typage, des tests et de Dependabot (#4)
- rapport par test dans le résumé de la CI (#7)
- types d'API du frontend générés depuis le schéma OpenAPI du backend (#8)
- CI lancée sur chaque pull request, y compris les PR empilées (#11)
- recherche de secrets avec gitleaks avant chaque commit et dans la CI (#17)
- vérification des messages de commit avec commitlint (#18)
- versions SemVer calculées à partir des Conventional Commits (#22)
- release : git-cliff lancé depuis la racine du dépôt (#23)

### Documentation

- agents : stratégie de fusion, messages git en anglais et docs bilingues (#3)
- guide des tests (#6)
- agents : suppression des branches de travail une fois fusionnées dans develop (#9)
- vue d'ensemble de l'architecture et clôture de la feuille de route du starter (#19)
- job Secrets ajouté aux vérifications CI obligatoires (#20)
- suppression de la feuille de route du starter, terminée (#21)

### Maintenance

- initialise le monorepo TierList (backend FastAPI + frontend React)
- initialise le starter (Hello World, PostgreSQL, outillage) (#1)
- .editorconfig partagé par tous les éditeurs (#15)
- vscode : configurations de débogage pour FastAPI et Vitest (#16)
