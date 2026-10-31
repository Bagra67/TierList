# Jalon 2 — Templates publics

[English](README.md) | Français

La conception du deuxième jalon de TierList : **des templates que tout le monde peut voir et jouer**, et la **modération** que le contenu public demande d'abord. Elle détaille, pour ce seul jalon, ce que liste [roadmap.fr.md](../roadmap.fr.md#jalon-2--templates-publics), avec le vocabulaire de [product.fr.md](../product.fr.md#glossaire), les règles de [game-rules.fr.md](../game-rules.fr.md#8-templates-et-marketplace) et les rôles de [permissions.fr.md](../permissions.fr.md).

**Statut : conçu.** Les stories sont suivies dans le [jalon GitHub](https://github.com/Bagra67/TierList/milestone/3).

C'est de la **conception métier**, pas de la documentation technique : ni tables, ni endpoints, ni détails de stockage. Ceux-ci s'écrivent dans `docs/technical/` une fois implémentés.

## Pages

| Page                                    | Contenu                                                                                     |
| --------------------------------------- | ------------------------------------------------------------------------------------------- |
| [User stories](user-stories.fr.md)      | Ce que chaque acteur peut faire, avec ses critères d'acceptation, regroupé par épopée.      |
| [Modèle de domaine](domain-model.fr.md) | Les nouveaux concepts métier, leurs relations et leurs invariants (diagramme de classes).   |
| [Cycles de vie](lifecycles.fr.md)       | Les états d'un template, d'une image, d'un signalement et d'un compte (diagrammes d'états). |

Les maquettes des nouveaux écrans sont sur le [canevas « TierList — Écrans »](https://claude.ai/artifact/EYMsS8K3Yj5fAjXGgj9t5d) (claude.ai, privé à son propriétaire, partagé sur demande), page « Jalon 2 », en français, sur l'identité visuelle « Le Plateau ». Ce sont des ébauches : les stories ci-dessus font foi.

## Périmètre

### Inclus

- **Socle de modération**, avant que quoi que ce soit soit public :
  - un rôle **super admin**, attribué hors de l'application et vérifié côté serveur ;
  - des **signalements** sur un template, une image, un pseudo ou une partie, ouverts à tous, avec une **file** de traitement super admin ; c'est aussi le mécanisme de notification des contenus illicites ;
  - **masquer**, réafficher ou **supprimer** une image ou un template ; des **empreintes bannies** pour qu'une image supprimée ne puisse pas être renvoyée ;
  - une **revue des derniers envois** ;
  - une **page utilisateur** pour les super admins et des **sanctions de compte** : bannissement temporaire et définitif ;
  - un **journal de modération** de chaque décision.
- **Templates publics** : le propriétaire rend un template public, ou de nouveau privé ; seul un compte à l'**e-mail confirmé** peut publier.
- **Marketplace** : consultation **sans compte** (lecture seule), recherche par **mots-clés** et **tags**, tri par **popularité** ou **nouveauté**, une page par template public, **likes**, **favoris**, **forks** autorisés par le propriétaire et qui créditent toute leur lignée.
- **Rooms sur le template d'un autre** : tout utilisateur peut lancer une room avec un template public.
- **Pagination** de la marketplace et de _Mes templates_.

### Non inclus

Prévu pour des jalons suivants ([roadmap.fr.md](../roadmap.fr.md)) : mode ouvert et mise en avant sur la page d'accueil (jalon 3), mode à l'aveugle (jalon 4), partage de templates avec des contributeurs, profils et amis, notifications par e-mail, retrait d'une offre achetée, détection automatique NSFW, vue super admin des templates supprimés, grades spéciaux.

## Décidé

Décisions produit prises en concevant ce jalon (2026-10-31) :

- **Ordre** : le contenu public passe avant le mode à l'aveugle, pour que la marketplace et le mode ouvert fassent venir de nouveaux joueurs.
- **Toute la marketplace** de [game-rules.fr.md §8](../game-rules.fr.md#8-templates-et-marketplace) : recherche, tri, likes, favoris et forks.
- **Modération après publication** : un template est public dès que son propriétaire le publie, si l'e-mail du compte est confirmé. Les signalements et la revue des envois servent de filet.
- Les **visiteurs** sans compte peuvent parcourir la marketplace et ouvrir un template public ; liker, mettre en favori, forker et lancer une room demandent un compte.
- Les **sanctions de compte** (bannissement temporaire et définitif) font partie de ce jalon.
- **Vocabulaire** (validé sur les maquettes) : la marketplace s'appelle _modèles publics_ / _public templates_ dans l'interface, et un fork _copier dans mes modèles_ / _copy to my templates_ ([guide i18n](../../technical/i18n.fr.md#vocabulaire)). L'en-tête gagne un lien _Modèles publics_ pour tous, et un lien _Modération_ avec le nombre de signalements ouverts, pour les super admins seulement.

## Hypothèses

Points pas encore décidés, pris dans leur version la plus simple pour ce jalon. Chacun peut être revu avant l'implémentation de sa story.

- La **popularité** est le nombre de likes.
- Les **tags** sont des mots libres choisis par le propriétaire, **5 au plus** par template, comparés sans tenir compte de la casse ni des accents.
- Les **forks ne sont pas autorisés** tant que le propriétaire ne les autorise pas. Un fork est un nouveau template **privé** de la personne qui forke ; il garde sa lignée même si un ancêtre devient privé ou est supprimé (l'ancêtre est alors affiché sans lien).
- Les **likes et favoris** d'un template qui devient privé ou est masqué sont gardés mais pas affichés ; ils reviennent s'il redevient public.
- **Motifs de signalement** : contenu illicite, contenu sexuel, violence ou haine, harcèlement, spam, autre (avec un texte). Tout le monde peut signaler, invités et visiteurs compris, avec une limite de fréquence.
- Un template **masqué par la modération** quitte la marketplace, son propriétaire voit pourquoi et ne peut pas le rendre public tant qu'un super admin ne l'a pas réaffiché. Les parties en cours se terminent, comme pour un template rendu privé ([game-rules.fr.md §8](../game-rules.fr.md#8-templates-et-marketplace)).
- Un **compte banni** est déconnecté partout et ne peut pas se connecter avant la fin du bannissement ; ses templates publics quittent la marketplace le temps du bannissement.
- La personne concernée par une décision la voit **dans l'application**, avec son motif (pas d'e-mail : les notifications viennent plus tard).
- La **politique de confidentialité** est mise à jour avec les stories qui changent ce que voient les autres utilisateurs (templates publics, nom du propriétaire sur la marketplace) et avec les signalements et le journal de modération (nouvelles données personnelles).
