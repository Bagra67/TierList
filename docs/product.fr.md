# Produit

[English](product.md) | Français

Ce qu'est TierList, pour qui, et le vocabulaire utilisé partout ailleurs. Les règles détaillées sont dans [game-rules.fr.md](game-rules.fr.md), qui peut faire quoi dans [permissions.fr.md](permissions.fr.md), et l'ordre de réalisation dans [roadmap.fr.md](roadmap.fr.md).

Cette page décrit le **produit visé**. La plupart n'est pas encore construite : [roadmap.fr.md](roadmap.fr.md) indique ce qui vient en premier.

## Vision

TierList est une application de **tier list communautaire**. Au lieu de classer seul, on rejoint une **room** et on classe les mêmes items **en même temps** : l'admin de la room affiche un item, chacun le place dans sa propre tier list, puis on compare les résultats (par joueur, globaux, classement médian, stats amusantes) et on les rejoue en révélation animée, comme à la fin d'une partie de Gartic Phone.

Autour de cette partie en direct :

- un **mode ouvert**, où une tier list reste ouverte un certain temps et chacun la remplit dans son coin ;
- un **mode solo**, pour faire une tier list seul ;
- un **mode à l'aveugle**, où l'on classe des items sans savoir ce que c'est (un son, une dégustation…) en essayant de les deviner ;
- une **marketplace** gratuite de templates publics.

## Glossaire

| Terme                | Sens                                                                                                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Template**         | Un set de tier list réutilisable : ses tuiles et ses tiers. Créé à l'avance, privé ou public. **Classique** ou **à l'aveugle**.                                         |
| **Tuile**            | Un item à classer : texte, image, son ou vidéo. Une tuile à l'aveugle a en plus un indice, un nom de réponse et une image de réponse.                                   |
| **Tier**             | Une ligne de la tier list (S, A, B…). Un template part de tiers par défaut qu'on peut ajouter, supprimer et configurer.                                                 |
| **Classement**       | La tier list d'un joueur : chaque tuile dans un tier, **ordonnée à l'intérieur du tier**.                                                                               |
| **Room**             | Un salon où les joueurs se retrouvent pour jouer en direct. On la rejoint par lien ou par code. Elle persiste entre les parties jusqu'à sa fermeture.                   |
| **Admin de la room** | La personne qui prépare la room, choisit le template, mène la partie et la configure. Joue ou non.                                                                      |
| **Joueur**           | Quelqu'un qui participe à une partie, avec un compte ou en invité.                                                                                                      |
| **Invité**           | Un joueur sans compte : moins d'options de personnalisation, accès à ses résultats uniquement par un lien temporaire.                                                   |
| **Partie**           | Une utilisation d'un template dans une room, du premier tour à la clôture. Sauvegardée pour tous les joueurs une fois clôturée, figée sur la version du template jouée. |
| **Tour**             | Un item affiché par l'admin de la room, placé par tous les joueurs en même temps.                                                                                       |
| **Cooldown final**   | Une phase chronométrée et configurable en fin de partie, pendant laquelle les joueurs peuvent replacer toutes leurs tuiles.                                             |
| **Board**            | Ce que voit un joueur pendant la partie. **Privé** : seulement le sien. **Public** : les placements de tous, en **hologrammes** semi-transparents.                      |
| **Vote absent**      | Enregistré pour un item qu'un joueur a manqué (déconnecté, arrivé en retard), pour calculer les stats avec ou sans les absences.                                        |
| **Mode ouvert**      | Une tier list ouverte à tous pendant une durée donnée, sans room : chacun la remplit dans son coin et l'envoie. Lancé par le propriétaire du template.                  |
| **Solo**             | Une tier list faite seul.                                                                                                                                               |
| **Mode à l'aveugle** | Les items sont cachés derrière un numéro pendant le classement, puis révélés. Les joueurs peuvent les deviner pour marquer des points.                                  |
| **Marketplace**      | Le catalogue gratuit des templates publics : recherche par tags et mots-clés, tri par popularité ou nouveauté, likes, favoris, forks.                                   |
| **Fork**             | Une copie d'un template, modifiable par quelqu'un d'autre, si le propriétaire l'autorise. Elle crédite toujours toute sa lignée.                                        |
| **Super admin**      | Un fondateur de l'application : voit tout et modère.                                                                                                                    |
| **Grade spécial**    | Un grade accordé sur demande aux créateurs (YouTuber, streamer…), dont les tier lists en mode ouvert sont mises en avant en premier.                                    |
| **Offre**            | La taille maximale des rooms : gratuite (10 joueurs), niveau 2 (32 joueurs), spéciale (illimitée). Achetée une fois, à vie ; tout est gratuit pour l'instant.           |

## Modes de jeu

| Mode                       | Comment on joue                                | Temps réel                                | Compte obligatoire                       | Détails                                                |
| -------------------------- | ---------------------------------------------- | ----------------------------------------- | ---------------------------------------- | ------------------------------------------------------ |
| **Room**                   | Ensemble, tour par tour, mené par l'admin      | Oui (hologrammes sur un board public)     | Non, invités acceptés                    | [Partie en room](game-rules.fr.md#1-partie-en-room)    |
| **Mode ouvert**            | Chacun dans son coin, pendant une durée donnée | Non (résultats mis à jour à chaque envoi) | Oui (évite les votes en masse)           | [Mode ouvert](game-rules.fr.md#2-mode-ouvert)          |
| **Solo**                   | Seul                                           | Non                                       | À décider (sauvegardé dans l'historique) | [Solo](game-rules.fr.md#3-solo)                        |
| **À l'aveugle** (variante) | En room, avec un template à l'aveugle          | Oui                                       | Comme pour une room                      | [Mode à l'aveugle](game-rules.fr.md#4-mode-à-laveugle) |

## Plateformes

L'application web d'abord. Une version **mobile** (glisser-déposer au doigt, petits écrans) est prévue bien plus tard.
