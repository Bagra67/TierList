# Jalon 1 — MVP

[English](README.md) | Français

La conception de la première version jouable de TierList : **une room privée en direct entre amis**. Elle détaille, pour ce seul jalon, ce que liste [roadmap.fr.md](../roadmap.fr.md#jalon-1--mvp), avec le vocabulaire de [product.fr.md](../product.fr.md#glossaire) et les règles de [game-rules.fr.md](../game-rules.fr.md).

C'est de la **conception métier**, pas de la documentation technique : ni tables, ni endpoints, ni protocole temps réel. Ceux-ci s'écrivent dans `docs/technical/` une fois implémentés.

## Pages

| Page                                    | Contenu                                                                                 |
| --------------------------------------- | --------------------------------------------------------------------------------------- |
| [User stories](user-stories.fr.md)      | Ce que chaque acteur peut faire, avec des critères d'acceptation, regroupé par épopée.  |
| [Modèle de domaine](domain-model.fr.md) | Les concepts métier, leurs relations et leurs invariants (diagramme de classes).        |
| [Cycles de vie](lifecycles.fr.md)       | Les états d'une room, d'une partie, d'un tour et d'un participant (diagrammes d'états). |
| [Déroulé](game-flow.fr.md)              | Qui fait quoi, dans quel ordre, du template aux résultats (diagrammes de séquence).     |
| [Écrans](screens.fr.md)                 | Les wireframes basse fidélité de chaque écran, avec les stories qu'ils couvrent.        |

## Périmètre

### Inclus

- **Templates** : privés, tuiles texte et image (images envoyées, compressées par le serveur), **tiers par défaut S, A, B, C, D, E**, qu'on peut ajouter, supprimer, renommer, recolorer et réordonner.
- **Room privée** : créée à partir d'un de ses templates, rejointe par **lien** ou par **code**, avec un compte ou en **invité**.
- **Réglages de la room** : ordre des items (template ou aléatoire), passage automatique à l'item suivant (timer ou tout le monde a fini ; le passage manuel reste toujours possible), durée du cooldown final, l'admin de la room joue ou non.
- **Partie** : tours menés par l'admin de la room, **board privé**, classements ordonnés.
- **Cooldown final** : replacer toutes ses tuiles ; les deux placements sont gardés.
- **Joueurs absents** : votes absents, reconnexion à sa place, rattrapage des items manqués pendant le cooldown.
- **Room qui persiste** : relancer une partie dans la même room ; fermée par l'admin de la room ou après inactivité.
- **Résultats** : par joueur, globaux (répartition par item), **classement médian**, avec ou sans les votes absents.
- **Liens** : lien public des résultats ; lien perso de l'invité (30 jours max, mort une fois la room fermée).
- **Historique** des parties pour les comptes.
- **Limites de l'offre gratuite** : **10 joueurs** par room, **32 tuiles** par template.

### Non inclus

Prévu dans les jalons suivants ([roadmap.fr.md](../roadmap.fr.md)) : board public et hologrammes, mode ouvert, solo, mode à l'aveugle, marketplace et templates publics, partage de templates, tuiles son et vidéo, révélation animée, export en image, photos de profil, amis, modération, offres et paiement, chat et réactions, mobile.

## Hypothèses

Points pas encore décidés, pris dans leur version la plus simple pour ce jalon. Chacun peut être revu.

- **Les résultats sont visibles une fois la partie clôturée** (le réglage « avant ou après la clôture » vient plus tard).
- **Personne n'a de photo de profil** dans ce jalon : les participants sont affichés par leur nom affiché (compte) ou leur pseudo (invité).
- **Les durées** (timer par item, cooldown, inactivité avant fermeture, validité du lien invité) sont des réglages de la room ou de l'application, dont les valeurs par défaut se choisissent à l'implémentation.
- **Règles ajoutées par les user stories**, à confirmer :
  - un template garde **au moins un tier**, et une room a besoin d'un template avec **au moins une tuile** ;
  - le **pseudo d'un invité est unique** dans la room ;
  - les réglages de la room **ne changent pas pendant une partie** ;
  - un admin de la room qui ne joue pas **compte quand même** dans les 10 participants, mais ni dans « tout le monde a fini » ni dans les résultats ;
  - les items des tours passés **ne se déplacent pas** avant le cooldown final ;
  - sur un board privé, les participants voient **qui a placé** l'item en cours, pas où ;
  - l'admin de la room peut **terminer le cooldown plus tôt**.
- **Le calcul des stats** (médiane de classements ordonnés, effet des votes absents) se décide à l'implémentation (voir [roadmap.fr.md](../roadmap.fr.md#questions-techniques)).
