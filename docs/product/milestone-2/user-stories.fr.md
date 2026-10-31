# Jalon 2 — User stories

[English](user-stories.md) | Français

Ce que chaque acteur peut faire dans le [jalon 2](README.fr.md), regroupé par épopée. Chaque story a un identifiant, une priorité et des critères d'acceptation écrits en _Étant donné / Quand / Alors_. Vocabulaire : [product.fr.md](../product.fr.md#glossaire). Rôles : [permissions.fr.md](../permissions.fr.md). Les points notés comme hypothèses dans le [README](README.fr.md#hypothèses) peuvent encore changer.

**Priorité** : **Must** = nécessaire avant que les templates puissent être publics ; **Should** = attendu dans le jalon, peut glisser au suivant si besoin.

**Ordre** : l'épopée E1 (modération) est livrée **avant** que E2 (templates publics) soit ouvert aux utilisateurs : rien n'est public sans un moyen de le signaler et de le retirer.

## Acteurs

| Acteur                       | Qui                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| **Utilisateur**              | Un compte connecté.                                                                         |
| **Propriétaire du template** | L'utilisateur qui a créé un template (ou un fork).                                          |
| **Visiteur**                 | Quiconque parcourt la marketplace sans être connecté.                                       |
| **Participant**              | Un participant d'une room, joueur ou invité ([jalon 1](../milestone-1/user-stories.fr.md)). |
| **Super admin**              | Un fondateur de l'application, qui modère.                                                  |

## E1 — Modération

### US-1.1 Rôle super admin — Must

En tant que **super admin**, je veux un rôle que seuls les fondateurs ont, pour que la modération leur soit réservée.

- _Étant donné_ un compte, _quand_ le rôle est attribué **hors de l'application** (une commande serveur), _alors_ le compte est super admin. Aucun écran ni aucune requête d'API ne peut l'attribuer ou le retirer.
- _Étant donné_ que je suis super admin, _quand_ j'ouvre l'application, _alors_ j'accède à l'**espace de modération** ; les autres utilisateurs ne le voient pas.
- _Étant donné_ une action de modération, _quand_ elle est demandée par un compte qui n'est pas super admin, _alors_ le serveur la refuse, quoi que montre l'interface.

### US-1.2 Signaler un contenu — Must

En tant que **n'importe qui** (utilisateur, participant ou visiteur), je veux signaler un template, une image, un pseudo ou une partie, pour que les super admins retirent ce qui enfreint les règles ou la loi.

- _Étant donné_ un template public, l'image d'une tuile, le pseudo d'un participant ou une page de résultats publique, _quand_ je le signale avec un **motif** (et un texte pour « autre »), _alors_ le signalement est enregistré et je vois qu'il est envoyé.
- _Étant donné_ que j'ai déjà signalé ce contenu, _quand_ je le signale à nouveau, _alors_ aucun second signalement n'est créé, et on m'indique qu'il est déjà signalé.
- _Étant donné_ que j'envoie beaucoup de signalements en peu de temps, _alors_ les suivants sont refusés un moment, avec un message (limite de fréquence).
- _Étant donné_ un signalement, _alors_ la personne signalée **ne sait jamais** qui l'a signalée.

### US-1.3 Traiter les signalements — Must

En tant que **super admin**, je veux une file des signalements ouverts, pour traiter chacun à la main.

- _Étant donné_ des signalements ouverts, _quand_ j'ouvre la file, _alors_ je les vois **regroupés par contenu**, avec le nombre de signalements, les motifs, le contenu lui-même et son propriétaire, les plus signalés en premier.
- _Étant donné_ un contenu signalé, _quand_ je **classe sans suite** les signalements, _alors_ ils sont fermés et le contenu reste tel quel.
- _Étant donné_ un contenu signalé, _quand_ je le **masque** ou le **supprime** (US-1.4, US-1.5) ou **sanctionne** son propriétaire (US-1.8), _alors_ ses signalements ouverts sont fermés avec cette décision.
- _Étant donné_ une décision, _alors_ elle est écrite dans le **journal de modération** (US-1.9).

### US-1.4 Masquer ou supprimer une image — Must

En tant que **super admin**, je veux masquer ou supprimer l'image d'une tuile, pour qu'elle ne soit plus montrée nulle part.

- _Étant donné_ une image visible, _quand_ je la **masque** avec un motif, _alors_ elle n'est plus servie : partout où elle apparaît (templates, parties en cours, résultats passés, liens publics), un visuel « image retirée » la remplace.
- _Étant donné_ une image masquée, _quand_ je la **réaffiche**, _alors_ elle est de nouveau montrée partout.
- _Étant donné_ une image, _quand_ je la **supprime**, _alors_ son fichier est effacé pour de bon et le visuel « image retirée » reste ; la suppression est définitive.
- _Étant donné_ une image supprimée, _alors_ son **empreinte** est bannie : le même fichier, renvoyé par n'importe qui, est refusé (US-1.6).

### US-1.5 Masquer ou supprimer un template — Must

En tant que **super admin**, je veux masquer ou supprimer un template, pour qu'il quitte la marketplace.

- _Étant donné_ un template public, _quand_ je le **masque** avec un motif, _alors_ il quitte la marketplace et sa page, aucune nouvelle room ne peut démarrer avec lui, et les parties en cours **se terminent**.
- _Étant donné_ un template masqué, _alors_ son propriétaire le voit marqué « masqué par la modération » avec le motif, peut encore le modifier, mais **ne peut pas le rendre public** de nouveau.
- _Étant donné_ un template masqué, _quand_ je le **réaffiche**, _alors_ il revient à l'état choisi par son propriétaire (public ou privé).
- _Étant donné_ un template, _quand_ je le **supprime**, _alors_ il est supprimé comme si son propriétaire l'avait supprimé ; les parties déjà jouées gardent leur version figée.

### US-1.6 Refuser les images bannies — Should

En tant que **super admin**, je veux qu'une image supprimée reste dehors, pour que le même fichier ne revienne pas.

- _Étant donné_ une empreinte bannie, _quand_ quelqu'un envoie le **même fichier**, _alors_ l'envoi est refusé avec le message habituel « image refusée », sans dire pourquoi.
- _Plus tard_ (pas dans ce jalon) : repérer les variantes réencodées de la même image.

### US-1.7 Revoir les derniers envois — Should

En tant que **super admin**, je veux voir les dernières images envoyées, pour trouver un problème avant qu'on le signale.

- _Étant donné_ l'espace de modération, _quand_ j'ouvre les derniers envois, _alors_ je vois une **grille paginée**, des plus récents aux plus anciens, avec l'auteur, la date et le nombre de templates et de parties qui utilisent chaque image.
- _Étant donné_ la grille, _quand_ je filtre par auteur, date ou statut (visible, masquée), _alors_ seules les images correspondantes sont montrées.
- _Étant donné_ une image, _alors_ je peux ouvrir la page de son auteur (US-1.8) et les templates qui l'utilisent, et la masquer ou la supprimer (US-1.4).

### US-1.8 Page utilisateur et sanctions — Must

En tant que **super admin**, je veux une page par compte et des sanctions, pour arrêter les abus répétés.

- _Étant donné_ un compte, _quand_ j'ouvre sa page, _alors_ je vois ses informations (nom affiché, e-mail, date de création, e-mail confirmé), ses templates, ses images envoyées, les signalements sur ses contenus et son historique de modération.
- _Étant donné_ la page, _quand_ je **masque toutes ses images** d'un coup, _alors_ chacune est masquée comme dans US-1.4.
- _Étant donné_ la page, _quand_ je **bannis** le compte **temporairement** (avec une date de fin) ou **définitivement**, avec un motif, _alors_ il est déconnecté partout, ne peut pas se connecter avant la fin du bannissement, et ses templates publics quittent la marketplace le temps du bannissement.
- _Étant donné_ un compte banni, _quand_ il essaie de se connecter, _alors_ c'est refusé avec le motif et, pour un bannissement temporaire, sa date de fin.
- _Étant donné_ un bannissement, _quand_ je le **lève**, ou que sa date de fin est atteinte, _alors_ le compte peut de nouveau se connecter et ses templates publics reviennent.
- _Étant donné_ que je suis super admin, _alors_ je ne peux me bannir ni moi-même ni un autre super admin.

### US-1.9 Journal de modération — Must

En tant que **super admin**, je veux que chaque décision soit enregistrée, pour savoir qui a fait quoi et pourquoi.

- _Étant donné_ une action de modération (classer sans suite, masquer, réafficher, supprimer, bannir, lever un bannissement), _alors_ le journal enregistre **qui**, **quand**, **quoi** (l'action et sa cible) et **pourquoi** (le motif).
- _Étant donné_ l'espace de modération, _quand_ j'ouvre le journal, _alors_ je vois les actions, des plus récentes aux plus anciennes, et je peux les filtrer par cible ou par super admin.
- _Étant donné_ le journal, _alors_ personne ne peut modifier ni supprimer une entrée.

### US-1.10 Voir une décision sur mon contenu — Should

En tant que **propriétaire d'un template**, je veux savoir quand la modération a agi sur mon contenu, pour comprendre pourquoi il n'est plus montré.

- _Étant donné_ que mon template ou mon image a été masqué ou supprimé, _quand_ j'ouvre mes templates, _alors_ je vois lequel, la décision et son motif.

## E2 — Templates publics

### US-2.1 Rendre un template public — Must

En tant que **propriétaire d'un template**, je veux rendre mon template public, pour que tout le monde puisse le trouver et le jouer.

- _Étant donné_ mon template privé avec au moins une tuile, et mon e-mail **confirmé**, _quand_ je le rends public, _alors_ il apparaît aussitôt dans la marketplace.
- _Étant donné_ que mon e-mail **n'est pas confirmé**, _quand_ j'essaie, _alors_ c'est refusé, avec un lien pour renvoyer l'e-mail de confirmation.
- _Étant donné_ que mon template est **masqué par la modération** ou que mon compte est banni, _quand_ j'essaie, _alors_ c'est refusé avec le motif.
- _Étant donné_ un template public, _quand_ je le modifie, _alors_ la marketplace montre la nouvelle version ; les parties déjà commencées gardent la leur.

### US-2.2 Ajouter des tags — Must

En tant que **propriétaire d'un template**, je veux ajouter des tags à mon template, pour qu'on le trouve par sujet.

- _Étant donné_ mon template, _quand_ j'ajoute des tags, _alors_ ils sont enregistrés, **5 au plus**, chacun un mot ou une courte expression ; les doublons (sans tenir compte de la casse ni des accents) sont fusionnés.
- _Étant donné_ mon template, _quand_ je retire un tag, _alors_ il ne sert plus à trouver le template.

### US-2.3 Rendre de nouveau privé un template public — Must

En tant que **propriétaire d'un template**, je veux rendre mon template public privé, ou le supprimer, pour décider qui peut l'utiliser.

- _Étant donné_ mon template public, _quand_ je le rends privé ou le supprime, _alors_ il quitte la marketplace, aucune **nouvelle partie** ne peut démarrer avec lui, même dans une room qui persiste, et les parties **en cours** ailleurs peuvent **se terminer** ([game-rules.fr.md §8](../game-rules.fr.md#8-templates-et-marketplace)).
- _Étant donné_ que d'autres utilisateurs l'ont liké ou mis en favori, _alors_ il n'apparaît plus dans leurs favoris ; il revient si je le rends de nouveau public.

### US-2.4 Lancer une room avec un template public — Must

En tant qu'**utilisateur**, je veux lancer une room avec le template public de quelqu'un d'autre, pour le jouer avec mes amis.

- _Étant donné_ un template public, _quand_ je lance une room avec, _alors_ la room fonctionne comme au [jalon 1](../milestone-1/user-stories.fr.md#e2--room), et j'en suis l'admin ; le template reste à son propriétaire et je ne peux pas le modifier.
- _Étant donné_ que le template devient privé, masqué ou supprimé, _alors_ une partie en cours se termine, mais ma room ne peut pas démarrer de nouvelle partie avec lui.
- _Étant donné_ que je suis visiteur, _quand_ j'essaie de lancer une room, _alors_ on me demande de me connecter, et je reviens au template ensuite.

### US-2.5 Paginer mes templates — Should

En tant qu'**utilisateur** avec beaucoup de templates, je veux que ma liste se charge par pages, pour qu'elle reste rapide.

- _Étant donné_ plus de templates qu'une page, _quand_ j'arrive en bas de la liste, _alors_ les suivants sont chargés.

## E3 — Marketplace

### US-3.1 Parcourir la marketplace — Must

En tant que **n'importe qui**, connecté ou non, je veux parcourir les templates publics, pour trouver quelque chose à jouer.

- _Étant donné_ la marketplace, _quand_ je l'ouvre, _alors_ je vois les templates publics, page après page, chacun avec son nom, le nom affiché de son propriétaire, ses tags, son nombre de tuiles et de likes, et un aperçu (l'image de sa première tuile, s'il y en a une).
- _Étant donné_ qu'aucun template public ne correspond, _alors_ un état vide l'indique.
- _Étant donné_ un template masqué ou d'un compte banni, _alors_ il n'apparaît jamais.

### US-3.2 Rechercher et trier — Must

En tant que **n'importe qui**, je veux rechercher et trier dans la marketplace, pour trouver un template sur un sujet.

- _Étant donné_ la marketplace, _quand_ je tape des **mots-clés**, _alors_ je vois les templates dont le nom ou les tags correspondent, sans tenir compte de la casse ni des accents.
- _Étant donné_ la marketplace, _quand_ je choisis un **tag**, _alors_ seuls les templates qui l'ont sont montrés.
- _Étant donné_ les résultats, _quand_ je trie par **popularité** (likes) ou **nouveauté** (date de passage en public), _alors_ l'ordre change ; la popularité est le tri par défaut.

### US-3.3 Ouvrir un template public — Must

En tant que **n'importe qui**, je veux voir un template public avant de le jouer, pour savoir ce qu'il contient.

- _Étant donné_ un template public, _quand_ j'ouvre sa page, _alors_ je vois son nom, son propriétaire, ses tags, ses tiers, ses tuiles, son nombre de likes et, pour un fork, sa lignée (US-3.7).
- _Étant donné_ la page, _alors_ je peux lancer une room (US-2.4), le liker (US-3.4), le mettre en favori (US-3.5), le forker (US-3.7) ou le signaler (US-1.2).
- _Étant donné_ que le template n'est plus public, _quand_ j'ouvre son lien, _alors_ je vois qu'il n'est pas disponible, sans dire pourquoi.

### US-3.4 Liker un template — Must

En tant qu'**utilisateur**, je veux liker un template public, pour que les bons templates montent dans la marketplace.

- _Étant donné_ un template public qui n'est pas le mien, _quand_ je le like, _alors_ son nombre de likes augmente de un ; _quand_ je le like de nouveau, _alors_ mon like est retiré.
- _Étant donné_ mon propre template, _alors_ je ne peux pas le liker.
- _Étant donné_ que je suis visiteur, _quand_ j'essaie, _alors_ on me demande de me connecter.

### US-3.5 Favoris — Should

En tant qu'**utilisateur**, je veux garder des templates publics en favoris, pour les retrouver.

- _Étant donné_ un template public, _quand_ je le mets en favori, _alors_ il apparaît dans **Mes favoris** ; _quand_ je le retire, _alors_ il disparaît.
- _Étant donné_ un favori qui n'est plus public, _alors_ il n'est pas affiché, et revient s'il redevient public.

### US-3.6 Autoriser les forks — Should

En tant que **propriétaire d'un template**, je veux choisir si mon template public peut être forké, pour garder la main sur les copies.

- _Étant donné_ mon template, _quand_ j'autorise les forks, _alors_ les autres utilisateurs peuvent le forker tant qu'il est public ; les forks **ne sont pas autorisés** tant que je ne l'ai pas choisi.
- _Étant donné_ que je n'autorise plus les forks, _alors_ aucun nouveau fork ne peut être fait ; les forks existants restent.

### US-3.7 Forker un template — Should

En tant qu'**utilisateur**, je veux forker un template public, pour l'adapter à mon goût.

- _Étant donné_ un template public dont le propriétaire autorise les forks, _quand_ je le forke, _alors_ j'obtiens un nouveau template **privé** à moi, avec une copie de ses tiers, de ses tuiles et de ses tags, que je modifie comme n'importe lequel de mes templates.
- _Étant donné_ un fork, _alors_ sa page et la marketplace **créditent toute sa lignée** : le template dont il est forké, jusqu'à l'original, avec leurs propriétaires.
- _Étant donné_ un ancêtre devenu privé, masqué ou supprimé, _alors_ la lignée montre encore son nom, sans lien.
- _Étant donné_ que les forks ne sont pas autorisés, ou que je suis visiteur, _alors_ je ne peux pas forker (un visiteur est invité à se connecter).
