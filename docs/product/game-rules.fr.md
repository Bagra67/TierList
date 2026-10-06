# Règles du jeu

[English](game-rules.md) | Français

Les règles métier de TierList : comment se joue chaque mode, ce qui est configurable, et ce qui est sauvegardé. Vocabulaire : [product.fr.md](product.fr.md#glossaire). Qui peut faire chaque action : [permissions.fr.md](permissions.fr.md). La plupart de ces règles ne sont pas encore implémentées, voir [roadmap.fr.md](roadmap.fr.md).

## 1. Partie en room

### Rejoindre une room

- On rejoint une room par un **lien** ou par un **code** saisi dans l'appli.
- Les joueurs ont un compte ou sont **invités**. Un invité a moins d'options de personnalisation (par ex. pas de photo de profil).
- Une room **persiste entre les parties** : même salon, même code, on peut relancer une partie sur le même template.
- Une room est fermée par son **admin**, ou **automatiquement** après un temps d'inactivité.
- Le nombre maximal de joueurs dépend de l'[offre](#7-offres-et-limites) de l'admin de la room.

### Déroulé d'une partie

- Un **tour** = l'admin de la room **affiche un item**, et **tous les joueurs le placent en même temps**.
- Ordre des items : **celui du template** ou **aléatoire**, au choix de l'admin de la room.
- Passage à l'item suivant :
  - l'admin de la room peut **toujours** passer **à la main** ;
  - en option, automatiquement : à la fin d'un **timer** par item, ou **dès que tout le monde a placé** l'item.
- Un classement est **ordonné** : à l'intérieur d'un tier, la position de chaque tuile compte.
- L'admin de la room **joue ou non**, selon la configuration.
- **Chat et réactions** (emojis) en option : voulus, mais pas prioritaires.

### Visibilité du board

| Board      | Ce que voient les joueurs                                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Privé**  | Uniquement leur classement. Résultats et stats sont révélés après.                                                                                 |
| **Public** | Un **hologramme** semi-transparent de la tuile de chaque autre joueur, qui **bouge en direct** pendant qu'il la déplace (on voit les hésitations). |

Les hologrammes sont **désactivés au-delà d'un nombre de joueurs**. Ce seuil est un **réglage de l'application**, pas de la room, et il se change **sans rebuild**.

### Cooldown final

- Après le dernier item, un **cooldown configurable** permet à chaque joueur de **replacer toutes ses tuiles**, avec une interface « sous pression » (timer, ambiance).
- **Les deux placements sont gardés** : celui du tour (« à chaud ») et le final. Les stats utilisent le placement final et peuvent comparer les deux.

### Joueurs absents

- Un joueur qui manque un item (déconnecté, arrivé en retard) reçoit un **vote absent** pour cet item.
- Pendant le cooldown final, il **peut placer les items manqués**.
- Les stats se calculent **avec ou sans** les votes absents.

### Clôture et sauvegarde

- À la fin, la partie est **clôturée** et **sauvegardée pour tous les joueurs**.
- Une partie sauvegardée est **figée** sur la version du template avec laquelle elle a été jouée : modifier le template ensuite ne la change pas.

### Réglages d'une room

Les rooms privées sont **très configurables**. Réglages cités jusqu'ici :

- visibilité du board (privé / public) ;
- ordre des items (template / aléatoire) ;
- passage automatique à l'item suivant (aucun / timer / tout le monde a fini) ;
- durée du cooldown final ;
- l'admin de la room joue ou non ;
- moment où les résultats sont visibles (avant ou après la clôture) ;
- rythme de la révélation animée (mené par l'admin de la room ou automatique) ;
- validité du lien invité (30 jours max) ;
- réglages du mode à l'aveugle, voir la [section 4](#4-mode-à-laveugle).

Les **rooms publiques** (ouvertes à tous) sont possibles mais repoussées : elles posent des questions de performance si l'appli grandit, voir [roadmap.fr.md](roadmap.fr.md#questions-techniques).

## 2. Mode ouvert

- **Pas de room** : chacun remplit la tier list **dans son coin**.
- Ouvert pendant une **durée donnée**, puis clôturé.
- **Un compte est obligatoire** pour participer (évite les votes en masse).
- Un participant peut **modifier son classement** après l'avoir envoyé, tant que c'est ouvert.
- Résultats et stats **mis à jour en direct** à chaque envoi ou modification.
- **Pas d'hologramme**, pas de temps réel.
- Seul le **propriétaire du template** peut lancer un mode ouvert.
- **Mis en avant sur la page d'accueil**, selon le nombre de likes, ou en premier quand le propriétaire a un [grade spécial](permissions.fr.md#grade-spécial).
- Mode ouvert à l'aveugle : possible, mais **pas dans un premier temps**.

## 3. Solo

- Une tier list faite **seul**, à partir d'un template.
- **Un compte est obligatoire**.
- **Sauvegardée dans l'historique**, **partageable** et **exportable** comme une partie.

## 4. Mode à l'aveugle

Les joueurs classent des items **sans savoir ce que c'est**, puis les items sont révélés. Exemple : un blind test de sons, ou une dégustation où l'admin de la room fait goûter chaque item dans la vraie vie pendant que la tuile correspondante s'affiche. L'appli ne gère que le classement : rien de physique.

### Templates

- Un template est **classique** ou **à l'aveugle**.
- Un template classique se joue **seulement en classique**. Un template à l'aveugle se joue **à l'aveugle ou en classique**.
- Une tuile à l'aveugle a, en plus de son contenu : un **indice**, un **nom de réponse** et une **image de réponse** (montrée à la révélation).

### Pendant la partie

- Une tuile cachée s'affiche comme un **numéro**. Plus tard : d'autres apparences, choisies parmi des **presets**.
- **Sons** : chaque joueur peut lancer le son **sur son propre appareil** (les joueurs dans la même pièce s'organisent entre eux).
- L'admin de la room a une **vue différente qui affiche les réponses**.
- L'admin de la room **peut jouer**, mais ses votes sont **marqués « admin »** : ils comptent dans la tier list, **pas dans le score de devinette**.
- **Révélation** : **après chaque tour** ou **à la fin**, configurable.

### Devinette

- Les joueurs essaient de **deviner** chaque item et marquent des points.
- Le mode de réponse est **choisi par le créateur du template** :
  - choix parmi **tous les items du template** ;
  - choix parmi une **liste définie par le créateur** (propositions, leurres) ;
  - **réponse libre**, jugée comme dans K-Culture : les joueurs donnent un **avis collégial** (ça passe ou non), et l'**admin de la room a le dernier mot**.
- **1 point par bonne réponse** plus un **bonus de rapidité**. La formule du bonus et le nombre de tentatives par item se décident à l'implémentation.
- Le score est **affiché pendant la partie**, avec un **récap à la fin**.

## 5. Résultats et partage

- Les résultats s'affichent **par joueur**, **globaux**, et en **révélation animée** (chaque item révélé l'un après l'autre, avec qui l'a placé où), comme à la fin d'une partie de Gartic Phone.
- Les résultats sont visibles **avant ou après la clôture**, selon la configuration.
- Chaque partie a une **page de résultats dédiée**, **partageable** : **n'importe qui avec le lien** peut voir la partie.
- **Export en image** d'une tier list finie : chaque participant **choisit ce qu'il exporte** (son classement, le classement médian, des stats…).

### Liens

| Lien                          | Rôle                                                      | Validité                                                                 |
| ----------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Lien perso de l'invité**    | Permet à un invité de retrouver sa place et ses résultats | Configurable, **30 jours max** ; ne marche plus une fois la room fermée. |
| **Lien public des résultats** | Permet à n'importe qui de voir la partie                  | Reste valable.                                                           |

Un lien invité perdu ne se récupère pas, et une partie jouée en invité **ne peut pas être rattachée** à un compte créé ensuite. Un **compte** est nécessaire pour garder l'**historique à vie**.

## 6. Statistiques

Décidé :

- Classement **médian** et **moyen** de chaque item. Comme les classements sont ordonnés dans les tiers, un **rang global** par item donne une médiane et une moyenne plus fines que le tier seul.
- Stats **avec ou sans les votes absents**.
- **Changements d'avis** : placement du tour comparé au placement final.
- Disponibles **à la fin de la partie**, et **pendant** quand ça a du sens.

Idées, à confirmer quand la fonctionnalité sera conçue :

- Item le plus **consensuel** (faible dispersion) et le plus **clivant** (forte dispersion, par ex. autant de S que de D).
- Répartition des votes par item (histogramme S → D).
- Accord entre joueurs : le joueur le plus « mainstream » (le plus proche de la moyenne), le « rebelle » (le plus éloigné), les deux joueurs aux goûts les plus proches et les plus opposés.
- Le « hot take » de chaque joueur : son item le plus éloigné du consensus.
- D'une partie à l'autre sur le même template : évolution d'un item ou d'un joueur.
- Pendant la partie : temps de décision par item, **hésitations** (déplacements avant de poser une tuile).
- Fun facts de profil, par ex. « ce joueur est 30 % plus dans les extrêmes que ses amis ».

## 7. Offres et limites

| Offre        | Taille des rooms |
| ------------ | ---------------- |
| **Gratuite** | 10 joueurs       |
| **Niveau 2** | 32 joueurs       |
| **Spéciale** | Illimitée        |

- C'est l'**admin de la room** qui paie, **une fois** : l'offre appartient à son compte **à vie** (pas d'abonnement). La modération peut retirer une offre achetée.
- **Tout est gratuit pour l'instant** : les offres existent dès le départ pour pouvoir ajouter le paiement plus tard.
- Limites de l'offre gratuite sur les templates :
  - **32 tuiles** max par template ;
  - les images des tuiles sont **envoyées** puis **compressées par le serveur** avant stockage ;
  - **pas de vidéo** ;
  - son **uniquement par un lien YouTube**, idéalement sans l'image (voir [roadmap.fr.md](roadmap.fr.md#questions-techniques)).
- Les offres payantes ne débloquent rien d'autre **pour l'instant** (vidéo, son ou vidéo envoyés, plus de tuiles : décidé plus tard).

## 8. Templates et marketplace

- Les tuiles peuvent être du **texte**, une **image**, un **son** ou une **vidéo**. Son et vidéo peuvent être des **fichiers envoyés** ou des **liens intégrés** (YouTube…), dans les [limites de l'offre](#7-offres-et-limites).
- **Tiers par défaut** (S, A, B…) qu'on peut **ajouter**, **supprimer** et **configurer**.
- Les templates sont **privés** ou **publics**. Les templates publics apparaissent dans la **marketplace** : recherche par **tags** et **mots-clés**, tri par **popularité**, **nouveauté**, etc.
- On peut **liker** un template et l'ajouter à ses **favoris**.
- Un template peut être **forké** si son propriétaire l'autorise. Un fork **crédite toujours toute sa lignée** (fork d'un fork… jusqu'à l'original).
- Quand un template public repasse en privé ou est supprimé, les parties **en cours** ailleurs peuvent **se terminer**, mais **aucune nouvelle partie** ne peut être lancée avec, même dans une room qui persiste.

## 9. Social

- **Profil simple** au départ. Plus tard : stats de joueur, badges, fun facts.
- **Amis** : ajout par **demande et acceptation**. On peut **inviter directement** un ami dans une room, et voir ses templates et ses badges.
- **Visibilité du profil et de l'historique** : **au choix de chaque utilisateur**.

## 10. Notifications

Les emails doivent être utiles, jamais du spam.

| Type                                          | Événements                                                                                                                                                                                         |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Toujours envoyés** (compte)                 | Confirmation de l'email, mot de passe oublié (déjà en place), sanction de modération, achat d'une offre.                                                                                           |
| **Désactivables** par l'utilisateur           | Un template a été partagé avec toi, ton mode ouvert est terminé (résultats prêts), un mode ouvert auquel tu as participé est clôturé, ta demande de grade est traitée, ton signalement est traité. |
| **Jamais par email** (dans l'appli seulement) | Likes, forks, demandes d'amis.                                                                                                                                                                     |
