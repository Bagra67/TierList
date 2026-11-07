# Roadmap

[English](roadmap.md) | Français

Dans quel ordre le [produit](product.fr.md) est construit, et les questions techniques à trancher en chemin. Le jalon 1 (MVP) est **terminé** : il est en production depuis la v1.0.0 ([guide de déploiement](../technical/deployment.fr.md)). Le contenu public vient ensuite (jalons 2 et 3), puis le mode à l'aveugle (jalon 4).

Les jalons ne sont pas des numéros de version : les releases suivent toujours [releasing.fr.md](../technical/releasing.fr.md). Une fonctionnalité reçoit sa documentation technique (dans [architecture.fr.md](../technical/architecture.fr.md) ou sa propre page dans `docs/technical/`) une fois **implémentée**, pas avant.

## Jalon 1 — MVP

La première version jouable : une room en direct entre amis.

**Terminé** : toutes les user stories sont livrées ([jalon GitHub](https://github.com/Bagra67/TierList/milestone/1?closed=1)).

- **Templates** : tuiles texte et image (images envoyées), **tiers configurables** (ajout, suppression, réglages).
- **Room privée** : rejointe par lien ou par code, invités acceptés, **tours menés par l'admin de la room**.
- **Board privé** (pas d'hologramme).
- **Cooldown final** : les joueurs peuvent replacer toutes leurs tuiles.
- **Résultats** : par joueur, globaux, et le **classement médian**.
- **Joueurs absents** : votes absents, reconnexion, rattrapage pendant le cooldown final.
- **Room qui persiste** : nouvelles parties dans la même room, fermée par l'admin de la room ou après inactivité.
- **Liens** : lien public des résultats, lien perso de l'invité.
- **Limites de l'offre gratuite** : 10 joueurs par room, 32 tuiles par template.

Conception détaillée (user stories, modèle de domaine, cycles de vie, déroulé, wireframes) : [milestone-1/](milestone-1/README.fr.md).

## Jalon 2 — Templates publics

Le prochain jalon : des templates que tout le monde peut voir et jouer. Le contenu public demande d'abord de la modération.

- **Socle de modération** : rôle super admin vérifié côté serveur ([#123](https://github.com/Bagra67/TierList/issues/123)), signalements avec une file de traitement super admin, qui sert aussi de mécanisme de notification des contenus illicites ([#126](https://github.com/Bagra67/TierList/issues/126)), masquer ou supprimer une image ([#124](https://github.com/Bagra67/TierList/issues/124)), revue des derniers envois ([#125](https://github.com/Bagra67/TierList/issues/125)), page utilisateur et bannissement de comptes ([#127](https://github.com/Bagra67/TierList/issues/127)). Voir [permissions.fr.md](permissions.fr.md#modération).
- **Marketplace** : templates publics, recherche par tags et mots-clés, tri par popularité ou nouveauté, likes, favoris, forks ; une liste paginée ([#105](https://github.com/Bagra67/TierList/issues/105)). Voir [game-rules.fr.md](game-rules.fr.md#8-templates-et-marketplace).
- La **politique de confidentialité** change avec : les autres utilisateurs voient les templates publics et leurs images.

Conception détaillée (user stories, modèle de domaine, cycles de vie) : [milestone-2/](milestone-2/README.fr.md).

## Jalon 3 — Mode ouvert et page d'accueil

- **Mode ouvert** (asynchrone) : chacun classe un template seul, pendant une durée fixée, avec un compte. Voir [game-rules.fr.md](game-rules.fr.md#2-mode-ouvert).
- **Mise en avant sur la page d'accueil**, avec les résultats et les statistiques de tous les participants, mis à jour en direct.
- Plus de **statistiques** ([#133](https://github.com/Bagra67/TierList/issues/133), [game-rules.fr.md](game-rules.fr.md#6-statistiques)).

## Jalon 4 — Mode à l'aveugle

Templates à l'aveugle, tuiles cachées, vue admin avec les réponses, révélation après chaque tour ou à la fin, devinette avec points (trois modes de réponse, réponse libre jugée collectivement). Voir [game-rules.fr.md](game-rules.fr.md#4-mode-à-laveugle).

## Ensuite (ordre à décider)

- Board public avec **hologrammes**.
- **Partage de templates** : contributeurs et lecture seule.
- Mode **solo**.
- Tuiles **son et vidéo**.
- **Révélation animée** des résultats, item par item, avec qui l'a placé où (le MVP montre déjà la tier list apparaître tier par tier).
- **Export en image** des résultats.
- **Amis**, puis stats de profil, badges et fun facts.
- **Modération**, au-delà du socle du jalon 2 : vue super admin des templates supprimés, détection automatique NSFW, retrait d'une offre achetée.
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

| Sujet                      | Question                                                                                                                                                                                                                                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Temps réel**             | Comment les rooms envoient les tours, les placements et les hologrammes à chaque joueur (par ex. WebSockets), et comment ça tient la charge. Le principal risque de performance, et la raison du report des rooms publiques. **Décidé** : voir le [guide du temps réel](../technical/realtime.fr.md). |
| **Seuil des hologrammes**  | Un réglage de l'application qu'on peut augmenter sans rebuild : où il est stocké (environnement, base de données…).                                                                                                                                                                                   |
| **Statistiques**           | Résultats en direct du mode ouvert : recalcul complet ou mise à jour incrémentale, selon ce qui consomme le moins. Classement médian de classements ordonnés : **décidé**, voir le [guide des résultats](../technical/results.fr.md).                                                                 |
| **Images**                 | Compression côté serveur avant stockage : format (par ex. WebP), taille et qualité maximales ; où les fichiers sont stockés. **Décidé** : voir le [guide des images](../technical/images.fr.md).                                                                                                      |
| **Son sans spoil**         | Un lecteur YouTube affiche le titre et la miniature, ce qui gâche un blind test. Les règles de l'API YouTube semblent interdire de séparer l'audio de la vidéo (lecteur masqué) : à vérifier ; repli possible, un petit lecteur visible ou des fichiers envoyés.                                      |
| **Versions des templates** | Comment une partie reste figée sur la version du template avec laquelle elle a été jouée. **Décidé** : voir le [guide des templates](../technical/templates.fr.md#24-instantanés-versions-de-template).                                                                                               |
| **Liens invités**          | Jeton du lien perso de l'invité : validité (30 jours max), révoqué à la fermeture de la room. **Décidé** : voir le [guide des salles](../technical/rooms.fr.md#24-invités).                                                                                                                           |
| **Fermeture des rooms**    | Délai d'inactivité avant la fermeture automatique d'une room. **Décidé** : 24 heures sans changement et sans personne de connecté, voir le [guide des salles](../technical/rooms.fr.md#26-fermer-une-salle).                                                                                          |
| **Score à l'aveugle**      | Formule du bonus de rapidité, nombre de tentatives par item.                                                                                                                                                                                                                                          |
| **Paiement**               | Prestataire de paiement ; sur mobile, les stores prennent 15 à 30 % de commission.                                                                                                                                                                                                                    |
