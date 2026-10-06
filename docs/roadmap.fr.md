# Roadmap

[English](roadmap.md) | Français

Dans quel ordre le [produit](product.fr.md) est construit, et les questions techniques à trancher en chemin. Aujourd'hui, le dépôt contient les fondations : comptes et connexion ([authentication.fr.md](authentication.fr.md)), traductions ([i18n.fr.md](i18n.fr.md)) et emails ([emails.fr.md](emails.fr.md)).

Les jalons ne sont pas des numéros de version : les releases suivent toujours [releasing.fr.md](releasing.fr.md). Une fonctionnalité reçoit sa documentation technique (dans [architecture.fr.md](architecture.fr.md) ou sa propre page) une fois **implémentée**, pas avant.

## Jalon 1 — MVP

La première version jouable : une room en direct entre amis.

- **Templates** : tuiles texte et image (images envoyées), **tiers configurables** (ajout, suppression, réglages).
- **Room privée** : rejointe par lien ou par code, invités acceptés, **tours menés par l'admin de la room**.
- **Board privé** (pas d'hologramme).
- **Cooldown final** : les joueurs peuvent replacer toutes leurs tuiles.
- **Résultats** : par joueur, globaux, et le **classement médian**.

## Jalon 2 — Mode à l'aveugle

Juste après le MVP, et rapidement : templates à l'aveugle, tuiles cachées, vue admin avec les réponses, révélation après chaque tour ou à la fin, devinette avec points (trois modes de réponse, réponse libre jugée collectivement). Voir [game-rules.fr.md](game-rules.fr.md#4-mode-à-laveugle).

## Ensuite (ordre à décider)

- Board public avec **hologrammes**.
- **Mode ouvert** (asynchrone), puis mise en avant sur la page d'accueil.
- **Marketplace** : templates publics, recherche, likes, favoris, forks.
- **Partage de templates** : contributeurs et lecture seule.
- Mode **solo**.
- Tuiles **son et vidéo**.
- **Révélation animée** des résultats.
- **Export en image** des résultats.
- Plus de **statistiques** (voir [game-rules.fr.md](game-rules.fr.md#6-statistiques)).
- **Amis**, puis stats de profil, badges et fun facts.
- **Modération** : signalements, panel admin, sanctions, vues fondateurs.
- Demandes de **grade spécial**.
- **Offres** et limites de taille des rooms, puis **paiement**.
- **Notifications** (emails et dans l'appli).
- **Chat et réactions** dans les rooms.
- **Rooms publiques**.
- **Mode ouvert à l'aveugle**.

## Bien plus tard

- Version **mobile**.
- Un **bot Discord** qui rejoint le salon vocal pour jouer les sons du mode à l'aveugle pour tout le monde.
- Apparence des tuiles cachées choisie parmi des **presets** (mode à l'aveugle).
- **Critères automatiques** pour les demandes de grade spécial.

## Questions techniques

À trancher quand la fonctionnalité concernée est conçue ; la décision va alors dans la documentation technique.

| Sujet                      | Question                                                                                                                                                                                                                                                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Temps réel**             | Comment les rooms envoient les tours, les placements et les hologrammes à chaque joueur (par ex. WebSockets), et comment ça tient la charge. Le principal risque de performance, et la raison du report des rooms publiques.                                     |
| **Seuil des hologrammes**  | Un réglage de l'application qu'on peut augmenter sans rebuild : où il est stocké (environnement, base de données…).                                                                                                                                              |
| **Statistiques**           | Résultats en direct du mode ouvert : recalcul complet ou mise à jour incrémentale, selon ce qui consomme le moins. Classement médian de classements ordonnés : à partir du rang global (moyenne ou médiane des positions) ?                                      |
| **Images**                 | Compression côté serveur avant stockage : format (par ex. WebP), taille et qualité maximales ; où les fichiers sont stockés.                                                                                                                                     |
| **Son sans spoil**         | Un lecteur YouTube affiche le titre et la miniature, ce qui gâche un blind test. Les règles de l'API YouTube semblent interdire de séparer l'audio de la vidéo (lecteur masqué) : à vérifier ; repli possible, un petit lecteur visible ou des fichiers envoyés. |
| **Versions des templates** | Comment une partie reste figée sur la version du template avec laquelle elle a été jouée.                                                                                                                                                                        |
| **Liens invités**          | Jeton du lien perso de l'invité : validité (30 jours max), révoqué à la fermeture de la room.                                                                                                                                                                    |
| **Fermeture des rooms**    | Délai d'inactivité avant la fermeture automatique d'une room.                                                                                                                                                                                                    |
| **Score à l'aveugle**      | Formule du bonus de rapidité, nombre de tentatives par item.                                                                                                                                                                                                     |
| **Paiement**               | Prestataire de paiement ; sur mobile, les stores prennent 15 à 30 % de commission.                                                                                                                                                                               |
