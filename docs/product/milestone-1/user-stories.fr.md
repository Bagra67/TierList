# Jalon 1 — User stories

[English](user-stories.md) | Français

Ce que chaque acteur peut faire dans le [jalon 1](README.fr.md), regroupé par épopée. Chaque story a un identifiant, une priorité et des critères d'acceptation écrits en _Étant donné / Quand / Alors_. Vocabulaire : [product.fr.md](../product.fr.md#glossaire). Écrans : [screens.fr.md](screens.fr.md).

**Priorité** : **Must** = indispensable pour que le jalon soit jouable ; **Should** = attendu dans le jalon, peut glisser au suivant si besoin.

## Acteurs

| Acteur               | Qui                                                                                                        |
| -------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Utilisateur**      | Un compte connecté (les comptes existent déjà : [authentification](../../technical/authentication.fr.md)). |
| **Admin de la room** | L'utilisateur qui a créé la room.                                                                          |
| **Joueur**           | Un participant de la room avec un compte.                                                                  |
| **Invité**           | Un participant de la room sans compte.                                                                     |
| **Visiteur**         | N'importe qui avec un lien public de résultats, connecté ou non.                                           |

« Participant » désigne un joueur ou un invité.

## E1 — Templates

### US-1.1 Créer un template — Must

En tant qu'**utilisateur**, je veux créer un template de tier list, afin de le jouer ensuite dans une room.

- _Étant donné_ que je suis connecté, _quand_ je crée un template avec un nom, _alors_ il est créé **privé**, à moi, avec les **tiers par défaut S, A, B, C, D, E** et sans tuile.
- _Étant donné_ un nom vide, _quand_ j'enregistre, _alors_ le template n'est pas créé et le champ affiche une erreur.

### US-1.2 Ajouter des tuiles texte et image — Must

En tant que **propriétaire du template**, je veux ajouter des tuiles avec un texte et/ou une image, afin que les joueurs aient des items à classer.

- _Étant donné_ mon template, _quand_ j'ajoute une tuile avec un texte, une image, ou les deux, _alors_ la tuile est ajoutée à la fin de la liste des tuiles.
- _Étant donné_ que j'envoie une image, _quand_ elle est acceptée, _alors_ le serveur la **compresse** avant de la stocker, et la tuile affiche la version stockée.
- _Étant donné_ un fichier qui n'est pas une image acceptée, ou trop lourd, _quand_ je l'envoie, _alors_ il est refusé avec un message.
- _Étant donné_ que mon template a déjà **32 tuiles**, _quand_ j'essaie d'en ajouter une, _alors_ c'est refusé avec un message qui indique la limite.
- _Étant donné_ une tuile sans texte ni image, _quand_ j'enregistre, _alors_ elle est refusée.

### US-1.3 Modifier, réordonner et supprimer des tuiles — Must

En tant que **propriétaire du template**, je veux modifier, réordonner et supprimer des tuiles, afin que le template corresponde à ce que je veux classer.

- _Étant donné_ une tuile, _quand_ je change son texte ou son image, _alors_ la modification est enregistrée.
- _Étant donné_ plusieurs tuiles, _quand_ j'en déplace une, _alors_ le nouvel **ordre du template** est enregistré (utilisé quand une room joue les items dans l'ordre du template).
- _Étant donné_ une tuile, _quand_ je la supprime, _alors_ elle disparaît du template.

### US-1.4 Configurer les tiers — Must

En tant que **propriétaire du template**, je veux ajouter, supprimer, renommer, recolorer et réordonner les tiers, afin que la tier list colle à son sujet.

- _Étant donné_ mon template, _quand_ j'ajoute un tier, _alors_ il apparaît en bas avec un nom et une couleur par défaut.
- _Étant donné_ un tier, _quand_ je le renomme, change sa couleur ou le déplace, _alors_ la modification est enregistrée.
- _Étant donné_ qu'il ne reste **qu'un tier**, _quand_ j'essaie de le supprimer, _alors_ c'est refusé : une tier list a besoin d'au moins un tier.

### US-1.5 Lister mes templates — Must

En tant qu'**utilisateur**, je veux voir mes templates, afin de les modifier ou de lancer une room.

- _Étant donné_ que je suis connecté, _quand_ j'ouvre mes templates, _alors_ je vois chacun avec son nom, son nombre de tuiles et la date de sa dernière modification.
- _Étant donné_ que je n'ai aucun template, _quand_ j'ouvre la page, _alors_ un état vide m'invite à en créer un.

### US-1.6 Supprimer un template — Should

En tant que **propriétaire du template**, je veux supprimer un template, afin de garder une liste propre.

- _Étant donné_ mon template, _quand_ je le supprime après confirmation, _alors_ il disparaît de mes templates.
- _Étant donné_ que des parties ont déjà été jouées avec, _quand_ je le supprime, _alors_ ces parties et leurs résultats **restent disponibles** : elles sont figées sur la version avec laquelle elles ont été jouées.
- _Étant donné_ qu'une room l'utilise, _quand_ je le supprime, _alors_ une partie en cours peut se terminer, mais aucune nouvelle partie ne peut être lancée avec.

### US-1.7 Modifier un template déjà joué — Must

En tant que **propriétaire du template**, je veux continuer à modifier un template après l'avoir joué, afin de l'améliorer.

- _Étant donné_ un template déjà joué, _quand_ je le modifie, _alors_ les parties passées **ne changent pas**, et la prochaine partie utilise la nouvelle version.

## E2 — Room

### US-2.1 Créer une room — Must

En tant qu'**utilisateur**, je veux créer une room à partir d'un de mes templates, afin de jouer avec des amis.

- _Étant donné_ un de mes templates avec au moins une tuile, _quand_ je crée une room, _alors_ j'en suis l'**admin**, et la room reçoit un **lien** et un **code** court.
- _Étant donné_ un template sans tuile, _quand_ j'essaie de créer une room, _alors_ c'est refusé.

### US-2.2 Configurer la room — Must

En tant qu'**admin de la room**, je veux choisir les réglages de la room, afin que la partie convienne à mon groupe.

- _Étant donné_ ma room avant le début d'une partie, _quand_ je règle l'**ordre des items** (template ou aléatoire), le **passage automatique** (aucun, timer par item avec sa durée, ou quand tout le monde a placé), la **durée du cooldown** et **si je joue**, _alors_ la prochaine partie utilise ces réglages.
- _Étant donné_ une partie en cours, _quand_ j'ouvre les réglages, _alors_ ils ne sont pas modifiables avant la clôture de la partie.

### US-2.3 Inviter des joueurs — Must

En tant qu'**admin de la room**, je veux partager le lien ou le code de la room, afin que mes amis la rejoignent.

- _Étant donné_ ma room, _quand_ je copie le lien ou lis le code, _alors_ n'importe qui les ayant peut la rejoindre (US-2.4, US-2.5).

### US-2.4 Rejoindre avec un compte — Must

En tant qu'**utilisateur**, je veux rejoindre une room par son lien ou son code, afin de jouer.

- _Étant donné_ un lien ou un code valide, _quand_ je rejoins en étant connecté, _alors_ j'entre dans la room comme **joueur**, affiché avec mon nom affiché.
- _Étant donné_ un mauvais code ou une room fermée, _quand_ j'essaie de rejoindre, _alors_ un message indique que la room est introuvable ou fermée.
- _Étant donné_ que je suis déjà dans la room, _quand_ j'ouvre à nouveau le lien, _alors_ je retrouve ma place au lieu d'en prendre une seconde.

### US-2.5 Rejoindre en invité — Must

En tant qu'**invité**, je veux rejoindre une room sans compte, afin de jouer tout de suite.

- _Étant donné_ un lien ou un code valide et pas de compte, _quand_ je saisis un **pseudo**, _alors_ j'entre dans la room comme **invité** et je reçois mon **lien perso**.
- _Étant donné_ un pseudo vide, ou déjà pris dans la room, _quand_ je rejoins, _alors_ c'est refusé avec un message.

### US-2.6 Limite de taille de la room — Must

En tant qu'**application**, je veux limiter les rooms à la taille de l'offre gratuite, afin de pouvoir appliquer les offres plus tard.

- _Étant donné_ une room avec **10 participants**, _quand_ quelqu'un d'autre essaie de la rejoindre, _alors_ c'est refusé avec un message qui indique la limite.
- _Étant donné_ que l'admin de la room ne joue pas, _alors_ il compte quand même dans les 10 (à confirmer à l'implémentation).

### US-2.7 Fermer la room — Must

En tant qu'**admin de la room**, je veux fermer ma room, afin que plus personne ne puisse la rejoindre ni y jouer.

- _Étant donné_ ma room sans partie en cours, _quand_ je la ferme, _alors_ on ne peut plus la rejoindre, les liens perso des invités ne marchent plus, et les liens publics des résultats **continuent de marcher**.
- _Étant donné_ une partie en cours, _quand_ je ferme la room, _alors_ je dois confirmer, la partie est d'abord clôturée (US-5.1), puis la room.

### US-2.8 Fermeture automatique — Should

En tant qu'**application**, je veux fermer les rooms inactives, afin que les rooms abandonnées ne restent pas ouvertes indéfiniment.

- _Étant donné_ une room sans activité pendant le délai d'inactivité (réglage de l'application), _alors_ elle est fermée comme dans US-2.7.

### US-2.9 Rejouer — Must

En tant qu'**admin de la room**, je veux lancer une nouvelle partie dans la même room, afin que mon groupe rejoue sans nouveau lien.

- _Étant donné_ une partie clôturée dans ma room, _quand_ je lance une nouvelle partie, _alors_ les participants encore dans la room y prennent part, avec le même lien et le même code, sur la version **actuelle** du template.

## E3 — Partie

### US-3.1 Lancer la partie — Must

En tant qu'**admin de la room**, je veux lancer la partie, afin que le premier tour commence.

- _Étant donné_ ma room avec au moins un participant qui place les items (moi compris si je joue), _quand_ je lance la partie, _alors_ la partie est figée sur la version actuelle du template, l'ordre des items est fixé (ordre du template ou mélangé), et le premier item s'affiche pour tout le monde.

### US-3.2 Voir l'item en cours — Must

En tant que **participant**, je veux voir l'item à classer, afin de le placer.

- _Étant donné_ un tour en cours, _alors_ je vois l'item en cours (texte et/ou image), son numéro sur le total, ma propre tier list et, si un timer est réglé, le temps restant.

### US-3.3 Placer l'item — Must

En tant que **participant**, je veux déposer l'item en cours dans un tier, à la position voulue, afin que mon classement reflète mon avis.

- _Étant donné_ l'item en cours, _quand_ je le dépose dans un tier, avant, entre ou après les items déjà présents, _alors_ il est enregistré à ce **tier et cette position**.
- _Étant donné_ que je l'ai déjà placé, _quand_ je le déplace pendant le même tour, _alors_ la nouvelle place remplace l'ancienne.
- _Étant donné_ des items des **tours passés**, _alors_ je ne peux pas les déplacer avant le cooldown final.
- _Étant donné_ un **board privé**, _alors_ je ne vois jamais les classements des autres participants pendant la partie ; je vois seulement qui a placé l'item en cours.

### US-3.4 Passer à l'item suivant — Must

En tant qu'**admin de la room**, je veux passer à l'item suivant, afin que la partie avance au bon rythme.

- _Étant donné_ un tour, _quand_ je clique sur « suivant », _alors_ le tour se termine et l'item suivant s'affiche, **quel que soit le réglage automatique** et même si des participants ne l'ont pas placé.
- _Étant donné_ le réglage « timer », _quand_ le temps est écoulé, _alors_ le tour se termine automatiquement.
- _Étant donné_ le réglage « tout le monde a fini », _quand_ tous les participants connectés ont placé l'item, _alors_ le tour se termine automatiquement.
- _Étant donné_ qu'un participant n'a pas placé l'item à la fin du tour, _alors_ il reçoit un **vote absent** pour cet item (US-4.3).
- _Étant donné_ le dernier item, _quand_ son tour se termine, _alors_ le cooldown final commence (US-4.1).

### US-3.5 Jouer ou seulement animer — Must

En tant qu'**admin de la room**, je veux jouer ou seulement animer, selon les réglages.

- _Étant donné_ « l'admin de la room joue », _alors_ je place les items comme n'importe quel participant, et j'ai aussi les commandes.
- _Étant donné_ « l'admin de la room ne joue pas », _alors_ j'ai seulement les commandes et je vois l'item en cours, sans tier list ; je ne compte ni dans « tout le monde a fini » ni dans les résultats.

## E4 — Cooldown final et absences

### US-4.1 Cooldown final — Must

En tant que **participant**, je veux un dernier moment chronométré pour déplacer toutes mes tuiles, afin d'ajuster mon classement avec toute la liste sous les yeux.

- _Étant donné_ que le cooldown a commencé, _alors_ je vois un compte à rebours et une interface « sous pression », et je peux déplacer **n'importe laquelle** de mes tuiles.
- _Étant donné_ le cooldown, _quand_ le temps est écoulé ou que l'admin de la room y met fin, _alors_ mon classement est définitif et la partie est clôturée (US-5.1).

### US-4.2 Garder les deux placements — Must

En tant qu'**application**, je veux garder le placement de chaque tour et le placement final, afin de mesurer les changements d'avis.

- _Étant donné_ un item placé pendant son tour, puis déplacé pendant le cooldown, _alors_ les deux placements sont gardés.
- _Étant donné_ un item non déplacé pendant le cooldown, _alors_ son placement final est son placement du tour.

### US-4.3 Vote absent — Must

En tant qu'**application**, je veux enregistrer un vote absent quand un participant manque un item, afin de calculer les stats avec ou sans les absences.

- _Étant donné_ un participant déconnecté ou pas encore arrivé pendant un tour, _quand_ le tour se termine, _alors_ un **vote absent** est enregistré pour lui sur cet item.

### US-4.4 Retrouver ma place — Must

En tant que **participant**, je veux retrouver ma place après une déconnexion, afin de garder mon classement.

- _Étant donné_ que j'ai été déconnecté, _quand_ je reviens (connecté, ou avec mon lien perso d'invité), _alors_ je retrouve mon classement et le tour en cours.

### US-4.5 Rejoindre pendant une partie — Must

En tant qu'**utilisateur** ou **invité**, je veux rejoindre une partie déjà commencée, afin de jouer la suite.

- _Étant donné_ une partie en cours et une place libre, _quand_ je rejoins, _alors_ je participe à partir du tour en cours, et les tours passés comptent comme des **votes absents** pour moi.

### US-4.6 Rattraper les items manqués — Must

En tant que **participant** avec des votes absents, je veux placer les items manqués pendant le cooldown, afin que mon classement soit complet.

- _Étant donné_ des items avec un vote absent, _quand_ le cooldown commence, _alors_ ils s'affichent à part, et je peux les placer dans ma tier list.
- _Étant donné_ que je place un tel item, _alors_ il reçoit un placement final et **garde son vote absent** pour le tour (pas de placement du tour).

## E5 — Résultats

### US-5.1 Clôturer et sauvegarder la partie — Must

En tant qu'**application**, je veux clôturer la partie à la fin du cooldown et la sauvegarder pour tous, afin de garder les résultats.

- _Étant donné_ que le cooldown est terminé, _alors_ la partie est **clôturée**, ses classements ne peuvent plus changer, et elle est sauvegardée dans l'historique de chaque participant **avec un compte**.

### US-5.2 Voir les résultats — Must

En tant que **participant**, je veux voir les résultats de la partie, afin de comparer nos classements.

- _Étant donné_ une partie clôturée, _alors_ je peux voir :
  - **le classement de chaque participant** ;
  - la **vue globale** : pour chaque item, combien de participants l'ont mis dans chaque tier (et combien étaient absents) ;
  - le **classement médian**.
- _Étant donné_ les résultats, _quand_ je bascule « avec / sans les votes absents », _alors_ les stats sont recalculées en conséquence.

### US-5.3 Partager les résultats — Must

En tant que **participant**, je veux un lien public vers les résultats, afin de les partager.

- _Étant donné_ une partie clôturée, _quand_ je copie son lien public, _alors_ n'importe quel **visiteur** qui l'ouvre voit les résultats (US-5.2), en lecture seule, sans compte.
- _Étant donné_ que la room est fermée plus tard, _alors_ le lien public **continue de marcher**.

### US-5.4 Lien perso de l'invité — Must

En tant qu'**invité**, je veux un lien perso, afin de retrouver ma place et mes résultats sans compte.

- _Étant donné_ que j'ai rejoint en invité, _alors_ je reçois un lien perso, valable pendant une durée fixée par l'application (**30 jours max**).
- _Étant donné_ que le lien a expiré ou que la room est fermée, _quand_ je l'ouvre, _alors_ un message indique qu'il n'est plus valable ; le lien public des résultats marche toujours.
- _Étant donné_ que je le perds, _alors_ il ne se récupère pas, et ma partie d'invité ne peut pas être rattachée à un compte créé ensuite.

### US-5.5 Historique — Should

En tant qu'**utilisateur**, je veux voir les parties auxquelles j'ai participé, afin de revoir leurs résultats.

- _Étant donné_ que je suis connecté, _quand_ j'ouvre mon historique, _alors_ je vois mes parties clôturées (nom du template, date, nombre de participants) et je peux ouvrir leurs résultats.
- _Étant donné_ qu'il n'y a encore aucune partie, _alors_ un état vide s'affiche.
