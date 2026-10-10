# Résultats

[English](results.md) | Français

Comment les résultats d'une partie close sont calculés : répartition des votes, votes absents, classement médian. Décidé dans le spike #76 ; le calcul existe sous forme de fonction pure (§4), que l'API des résultats (#99) et la page (#100) utiliseront. Ce que les résultats montrent à l'utilisateur : [user stories](../product/milestone-1/user-stories.fr.md) US-5.2.

**En résumé** : pour chaque item, les placements de tous les joueurs sont convertis en **scores fins** (tier + position dans le tier), et l'item garde le **score médian**. Puis on construit la tier list médiane de tous les items : chaque item va dans le tier de son score médian, et dans un tier les items sont triés par score médian.

## 1. Vue fonctionnelle

Les résultats d'une partie (US-5.2) montrent :

- **le classement de chaque participant** : ses placements finaux tels quels, sans calcul ;
- la **vue globale** : pour chaque item, combien de joueurs l'ont mis dans chaque tier, et combien étaient absents ;
- le **classement médian** : une tier list où chaque item a un tier et une place.

Une case **« Inclure les votes absents »** recalcule la vue globale et le classement médian. Elle est cochée par défaut, comme sur l'[écran des résultats](../product/milestone-1/screens.fr.md).

### Règles

- Les résultats utilisent les **placements finaux** d'une partie close : le placement du tour, déplacé pendant le cooldown si le joueur a changé d'avis ([modèle du domaine](../product/milestone-1/domain-model.fr.md)).
- Un classement est **ordonné** : dans un tier, la position de chaque item compte.
- Seuls les **joueurs** comptent. L'admin de la room qui ne joue pas n'est pas dans les résultats.
- Les tiers sont ceux de l'instantané du template de la partie, du haut (le meilleur) vers le bas ; il y en a au moins un.

## 2. Conception technique

Notation : les tiers sont numérotés de haut en bas, `t = 0, 1, …` (`0` est le meilleur tier). Un score plus petit est meilleur.

### 2.1 Votes comptés

Pour un item, chaque joueur compte **au plus une fois** :

| Situation du joueur pour l'item                  | Case cochée            | Case décochée |
| ------------------------------------------------ | ---------------------- | ------------- |
| L'a placé pendant le tour                        | Vote (placement final) | Vote          |
| Absent au tour, l'a rattrapé pendant le cooldown | Vote (placement final) | Ignoré        |
| Absent au tour, ne l'a jamais placé              | Compté dans « Absent » | Ignoré        |

- **Cochée** : chaque joueur qui a classé l'item compte, rattrapages compris ; ceux qui ne l'ont jamais placé forment la ligne « Absent » de la vue globale, sans effet sur la médiane (ils n'ont pas de tier).
- **Décochée** : seuls comptent les votes faits pendant le tour, l'« avis à chaud » de la partie ; les absents sont retirés, même s'ils ont rattrapé l'item, et la ligne « Absent » est vide.

### 2.2 Score fin d'un vote

Le tier seul est trop grossier : deux items du même tier seraient toujours à égalité. Le **score fin** ajoute la position dans le tier :

```
score = t + (k + 1/2) / n
```

- `t` : indice du tier où le joueur a mis l'item ;
- `k` : rang de l'item dans ce tier pour ce joueur (`0` = premier) ; seul l'ordre des positions compte ;
- `n` : nombre d'items que le joueur a mis dans ce tier.

Le score est toujours strictement entre `t` et `t + 1` : trier par score trie donc aussi par tier. Diviser par `n` rend les joueurs comparables même quand leurs tiers ne contiennent pas le même nombre d'items. Exemple : le 2e item sur 4 du tier A (`t = 1`) a pour score `1 + 1,5 / 4 = 1,375`.

Un score est calculé sur le **classement complet du joueur**, quelle que soit la case : la décocher retire des votes, elle ne change pas les classements. Les scores sont des fractions exactes (`fractions.Fraction`), pour que les égalités soient exactes.

### 2.3 Score médian et tier médian

- Les scores des votes comptés sont triés par ordre croissant ; le **score médian** est celui d'indice `⌊N / 2⌋` (indices à partir de 0, `N` = nombre de votes).
- Avec un nombre **impair** de votes, c'est le vote du milieu. Avec un nombre **pair**, c'est le **moins bon des deux votes du milieu** : une majorité stricte des joueurs a mis l'item à ce niveau ou mieux (convention du jugement majoritaire). Exemple : votes A, A, B, B → B.
- Le **tier médian** est la partie entière du score médian. C'est toujours un tier où au moins un joueur a mis l'item.
- Le **score moyen** (moyenne des scores) est aussi calculé : il départage les égalités (§2.4) et servira au classement moyen prévu plus tard ([règles du jeu](../product/game-rules.fr.md)).

### 2.4 Classement médian

1. Chaque item va dans son tier médian.
2. Dans un tier, les items sont triés par **score médian**, puis par **score moyen**, puis par **ordre du template** (toujours différent : l'ordre est total et stable).
3. Un item **sans aucun vote compté** (tous les joueurs absents et jamais rattrapé, ou case décochée et personne n'a voté pendant le tour) n'a pas de tier médian : il est listé à part comme **non classé**, dans l'ordre du template.
4. Un tier peut rester vide.

### 2.5 Entrées et sorties

`compute_results(tier_count, tile_ids, players, include_absent_votes)` dans `app/services/results.py` :

| Entrée                 | Contenu                                                                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tier_count`           | Nombre de tiers de l'instantané.                                                                                                                            |
| `tile_ids`             | Les tuiles de l'instantané, dans l'ordre du template (dernier départage, ordre des non classés).                                                            |
| `players`              | Un `PlayerRanking` par joueur : `final_placements` (tuile → `FinalPlacement(tier_index, position)`) et `absent_tile_ids` (absent au tour, rattrapé ou non). |
| `include_absent_votes` | La case.                                                                                                                                                    |

La sortie, `GameResults`, contient pour chaque item un `ItemResults` (`votes_per_tier`, `absent_count`, `median_score`, `mean_score`, `median_tier_index`, les trois derniers à `None` quand l'item n'est pas classé), le `median_ranking` (un tuple de tuiles par tier, de haut en bas) et les `unranked_tile_ids`.

La fonction est pure (sans base de données) : l'API des résultats (#99) charge l'instantané et les placements, exclut l'admin qui ne joue pas, et transforme la sortie en son schéma de réponse. Au plus 10 joueurs et 32 items : le calcul est instantané, l'API peut le refaire à chaque requête, case comprise.

### 2.6 Limites connues

- Le mode ouvert (plus tard) a des statistiques en direct ; les recalculer entièrement ou de façon incrémentale reste à décider ([roadmap](../product/roadmap.fr.md#questions-techniques)). Cette fonction couvre les parties en room.
- Comparer les placements de tour et finaux (« changements d'avis ») est une statistique pour plus tard ; elle n'est pas calculée ici.

## 3. Exemples chiffrés

Les tests de `tests/test_results.py` recalculent chaque exemple ([guide des tests](testing.fr.md)). Les tiers sont S, A, B (`t = 0, 1, 2`) sauf mention contraire.

### Exemple 1 : cas de base

| Joueur | S                 | A               | B      |
| ------ | ----------------- | --------------- | ------ |
| Alice  | Paprika, Barbecue | Nature          |        |
| Bob    | Barbecue          | Paprika, Nature |        |
| Chloé  | Paprika           | Barbecue        | Nature |

| Item     | Scores fins (Alice, Bob, Chloé) | Triés         | Médiane | Moyenne | Votes S / A / B | Tier médian |
| -------- | ------------------------------- | ------------- | ------- | ------- | --------------- | ----------- |
| Paprika  | 1/4, 5/4, 1/2                   | 1/4, 1/2, 5/4 | 1/2     | 2/3     | 2 / 1 / 0       | S           |
| Barbecue | 3/4, 1/2, 3/2                   | 1/2, 3/4, 3/2 | 3/4     | 11/12   | 2 / 1 / 0       | S           |
| Nature   | 3/2, 7/4, 5/2                   | 3/2, 7/4, 5/2 | 7/4     | 23/12   | 0 / 2 / 1       | A           |

Classement médian : **S** Paprika, Barbecue (1/2 < 3/4) · **A** Nature · **B** vide.

### Exemple 2 : nombre pair de votes

Quatre joueurs mettent Paprika seul dans son tier : deux en A, deux en B. Scores 3/2, 3/2, 5/2, 5/2 ; indice `⌊4 / 2⌋ = 2` → **5/2**, tier **B** (le moins bon des deux votes du milieu).

### Exemple 3 : votes absents et case

| Joueur | S        | A       | B        | Absent au tour                          |
| ------ | -------- | ------- | -------- | --------------------------------------- |
| Alice  | Barbecue | Paprika |          |                                         |
| Dan    | Paprika  |         | Barbecue | Barbecue (rattrapé pendant le cooldown) |
| Eve    |          | Paprika |          | Barbecue (jamais placé)                 |

| Barbecue          | Votes comptés      | Votes S / A / B | Absents | Médiane | Tier médian |
| ----------------- | ------------------ | --------------- | ------- | ------- | ----------- |
| **Case cochée**   | Alice 1/2, Dan 5/2 | 1 / 0 / 1       | 1       | 5/2     | B           |
| **Case décochée** | Alice 1/2          | 1 / 0 / 0       | 0       | 1/2     | S           |

Paprika est en A les deux fois (scores 3/2, 1/2, 3/2 → médiane 3/2, moyenne 7/6, votes 1 / 2 / 0). Classement médian : cochée **A** Paprika · **B** Barbecue ; décochée **S** Barbecue · **A** Paprika.

### Exemple 4 : item que personne n'a placé

Alice (Paprika en S) et Bob (Paprika en A) ont tous deux raté Vinaigre et ne l'ont jamais placé. Vinaigre n'a aucun vote : **non classé**, avec 2 votes absents quand la case est cochée, 0 quand elle est décochée. Paprika est en A (scores 1/2 et 3/2, le moins bon des deux).

### Exemple 5 : départages

Tiers S, A (`t = 0, 1`).

| Joueur | S       | A       |
| ------ | ------- | ------- |
| Alice  |         | X, Y, Z |
| Bob    |         | Y, X, Z |
| Chloé  | Y, X, Z |         |

X : scores 7/6, 3/2, 1/2 → médiane **7/6**, moyenne **19/18**. Y : scores 3/2, 7/6, 1/6 → médiane **7/6**, moyenne **17/18**. Même score médian : la moyenne tranche, **Y avant X**, bien que X soit premier dans le template.

Si Alice classe S : X, Y et Bob S : Y, X, les deux items ont la médiane 3/4 et la moyenne 1/2 : l'**ordre du template** tranche, X avant Y.

## 4. Dans le code

| Partie  | Fichier                           | Contenu                                                                                                        |
| ------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Backend | `backend/app/services/results.py` | `compute_results` et ses classes de données (`FinalPlacement`, `PlayerRanking`, `ItemResults`, `GameResults`). |
| Tests   | `backend/tests/test_results.py`   | Les exemples du §3 ([guide des tests](testing.fr.md)).                                                         |

L'API (#99) et la page des résultats avec la case (#100) viennent ensuite.
