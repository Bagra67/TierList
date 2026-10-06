# Permissions

[English](permissions.md) | Français

Qui peut faire quoi dans TierList : sur les templates, dans les rooms et en modération. Vocabulaire : [product.fr.md](product.fr.md#glossaire). Règles du jeu : [game-rules.fr.md](game-rules.fr.md). Ces permissions ne sont pas encore implémentées, voir [roadmap.fr.md](roadmap.fr.md). Comme pour l'authentification, elles sont vérifiées par le **backend** : masquer un bouton dans l'interface n'est jamais la barrière de sécurité.

## Rôles

| Rôle                 | Qui                                                                        |
| -------------------- | -------------------------------------------------------------------------- |
| **Propriétaire**     | Le créateur d'un template (ou d'un fork).                                  |
| **Contributeur**     | Quelqu'un à qui le template a été partagé, **avec droit de modification**. |
| **Lecture seule**    | Quelqu'un à qui le template a été partagé, **sans droit de modification**. |
| **Utilisateur**      | N'importe quel compte connecté.                                            |
| **Admin de la room** | L'utilisateur qui a créé la room.                                          |
| **Joueur**           | Un membre de la room, connecté ou invité.                                  |
| **Invité**           | Un joueur sans compte.                                                     |
| **Super admin**      | Un fondateur de l'application.                                             |

## Templates

| Action                                         | Propriétaire | Contributeur | Lecture seule | Autre utilisateur                               |
| ---------------------------------------------- | :----------: | :----------: | :-----------: | ----------------------------------------------- |
| Modifier le template                           |     Oui      |     Oui      |      Non      | Non                                             |
| Le partager (en contributeur ou lecture seule) |     Oui      |     Oui      |      Non      | Non                                             |
| Lancer une room avec                           |     Oui      |     Oui      |      Oui      | Seulement si le template est public             |
| Lancer un mode ouvert avec                     |     Oui      |     Non      |      Non      | Non                                             |
| Le rendre public ou privé                      |     Oui      |     Non      |      Non      | Non                                             |
| Autoriser les forks                            |     Oui      |     Non      |      Non      | Non                                             |
| Le forker                                      |      —       |      —       |       —       | S'il est public et que les forks sont autorisés |
| Le supprimer                                   |     Oui      |     Non      |      Non      | Non                                             |
| Le liker, l'ajouter aux favoris                |      —       |      —       |       —       | S'il est public                                 |
| Le signaler                                    |      —       |      —       |       —       | Oui                                             |

Un template **privé** ne peut servir à lancer une room que par son propriétaire et par les personnes avec qui il a été partagé.

## Rooms et parties

| Action                                                                         |       Admin de la room        | Joueur (compte) | Invité                                |
| ------------------------------------------------------------------------------ | :---------------------------: | :-------------: | ------------------------------------- |
| Configurer la room, lancer une partie, passer à l'item suivant, fermer la room |              Oui              |       Non       | Non                                   |
| Voir les réponses en mode à l'aveugle                                          |              Oui              |       Non       | Non                                   |
| Avoir le dernier mot sur une réponse libre                                     |              Oui              | Donne son avis  | Donne son avis                        |
| Placer les items                                                               |    Si configuré pour jouer    |       Oui       | Oui                                   |
| Marquer des points de devinette (à l'aveugle)                                  | Non (votes marqués « admin ») |       Oui       | Oui                                   |
| Choisir un pseudo et une photo de profil                                       |              Oui              |       Oui       | Limité                                |
| Garder la partie dans l'historique                                             |              Oui              |       Oui       | Non : lien perso temporaire seulement |
| Inviter directement un ami                                                     |              Oui              |        —        | —                                     |
| Exporter une image des résultats                                               |              Oui              |       Oui       | Oui                                   |

N'importe qui avec le **lien public des résultats** peut voir une partie clôturée (voir [game-rules.fr.md](game-rules.fr.md#liens)).

La taille de la room est limitée par l'**offre de l'admin de la room** (voir [game-rules.fr.md](game-rules.fr.md#7-offres-et-limites)).

## Grade spécial

- Accordé **sur demande** aux créateurs (YouTuber, streamer…) par les super admins.
- La demande **doit fournir des preuves** : liens Twitch, YouTube, Discord…
- Plus tard : **critères automatiques** d'acceptation ou de refus.
- Effet : les modes ouverts du propriétaire sont **mis en avant en premier** sur la page d'accueil.

## Modération

- N'importe quel utilisateur peut **signaler** un contenu.
- Chaque signalement est traité **à la main**, dans un **panel admin** qui montre le nombre de signalements et leur détail.
- Les **super admins voient tout** (vues fondateurs) et peuvent **tout modérer** : templates, médias, pseudos, parties…
- Sanctions : **masquer**, **supprimer**, **bannir temporairement**, **bannir définitivement**, **retirer une offre achetée**.
