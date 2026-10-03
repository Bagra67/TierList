# Journal des modifications

[English](CHANGELOG.md) | Français

Tous les changements notables du projet sont consignés dans ce fichier.
Les versions suivent le [Semantic Versioning](https://semver.org/lang/fr/) : voir [docs/releasing.fr.md](docs/releasing.fr.md).

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
