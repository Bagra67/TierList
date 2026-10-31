# Identité visuelle — « Le Plateau »

[English](visual-identity.md) | Français

L'identité visuelle de TierList, décidée sur de vrais écrans le 2026-10-28 (#213 à #222) : le plateau d'un jeu télé ou d'un quiz, avec sa **scène** claire, son **encre** profonde, son **buzzer** et son **projecteur**. Cette page liste les valeurs et les règles, et où elles vivent dans le code. La version mise en page, avec des aperçus des composants, est le [design system « TierList — Le Plateau »](https://claude.ai/artifact/1HiN88pvwgBbSjy2p1QysC) (claude.ai, privé à son propriétaire, partagé sur demande). Quand les deux diffèrent, **le code fait foi**.

## 1. Où elle vit

| Élément                                                    | Où                                                                                                         |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Tokens de couleur, de rayon et d'ombre (clair et `.dark`)  | `frontend/src/index.css` (`:root`, `.dark`, `@theme inline`)                                               |
| Couleurs proposées pour les tiers (12)                     | `frontend/src/constants/templates.ts` (`TIER_COLOR_PRESETS`)                                               |
| Barres du logo, encre et blanc pour le texte sur un tier   | `frontend/src/constants/brand.ts`                                                                          |
| Couleur du texte sur une couleur choisie par l'utilisateur | `frontend/src/theme/contrast.ts` (`readableTextColor`)                                                     |
| Panneaux, boutons, puces d'élément, lignes de tier         | `components/ui/panel.ts`, `components/ui/button.tsx`, `components/boardStyles.ts`                          |
| Polices                                                    | `@fontsource-variable/anybody` (axe de largeur) et `@fontsource-variable/geist`, importées par `index.css` |
| Favicon                                                    | `frontend/public/favicon.svg`                                                                              |

Les tokens sont des valeurs `oklch()` ; les valeurs hexadécimales ci-dessous sont leurs équivalents sRGB.

## 2. Couleurs

| Rôle             | Token                          | Clair     | Sombre    | Usage                                                                                  |
| ---------------- | ------------------------------ | --------- | --------- | -------------------------------------------------------------------------------------- |
| Scène            | `background`                   | `#F4F5FA` | `#140F2B` | Fond de toutes les pages.                                                              |
| Encre            | `foreground`                   | `#1D1640` | `#ECEAF6` | Texte et titres.                                                                       |
| Surface          | `card`, `popover`              | `#FFFFFF` | `#1D1640` | Panneaux, cartes, puces d'élément, menus.                                              |
| Buzzer           | `primary`                      | `#D41E5B` | `#FF5C8A` | L'action principale d'une zone, l'élément à placer maintenant, le minuteur qui presse. |
| Sur le buzzer    | `primary-foreground`           | `#FFFFFF` | `#140F2B` | Texte sur le buzzer.                                                                   |
| Neutre           | `secondary`, `muted`, `accent` | `#E9EAF3` | `#2A2257` | Boutons secondaires, bandeaux d'information, survol.                                   |
| Texte atténué    | `muted-foreground`             | `#5E5878` | `#A49FBF` | Aides, légendes, compteurs.                                                            |
| Erreur           | `destructive`                  | `#B32517` | `#FA8467` | Erreurs et actions destructrices.                                                      |
| Bordure          | `border`                       | `#D5D6E4` | `#3A3170` | Panneaux, lignes de tier, séparateurs.                                                 |
| Bordure de champ | `input`                        | `#8C88A6` | `#6A6296` | Champs de formulaire (3:1 avec le fond).                                               |
| Focus            | `ring`                         | `#3B5BDB` | `#8FA6FF` | Anneau de focus clavier.                                                               |
| Succès           | `success`                      | `#168057` | `#3FCB93` | Confirmations, présence en ligne.                                                      |
| Avertissement    | `warning`                      | `#AD7300` | `#FFC22E` | Bordure et fond léger d'un avertissement, jamais du texte.                             |
| Projecteur       | `spotlight`                    | `#FFC22E` | `#FFC22E` | Fond plein du minuteur de la manche et de l'étiquette de l'hôte, l'encre dessus.       |

Règles :

- **Un seul buzzer par zone.** Une deuxième action principale passe en secondaire ou en contour.
- **Le projecteur est un fond, jamais un trait.** En bordure ou en texte, il est trop pâle sur la scène claire : les avertissements utilisent `warning`.
- **Une erreur ne ressemble jamais au buzzer** : `destructive` en diffère par la teinte et la clarté.
- **Le focus est bleu** (`ring`) : il ne correspond à aucune couleur de tier, ni au buzzer.
- **Les retouches finales** (cooldown final) se jouent sur un **plateau sombre quel que soit le thème** : la zone prend les tokens `.dark`, avec une bordure `warning` (`CooldownStage`).

## 3. Couleurs des tiers

| Tier | Couleur   |     | Proposée     | Couleur   |
| ---- | --------- | --- | ------------ | --------- |
| S    | `#FF3B6B` |     | Ciel         | `#4FC3F7` |
| A    | `#FF8A2A` |     | Lilas        | `#A78BFA` |
| B    | `#FFC22E` |     | Orchidée     | `#F06BD0` |
| C    | `#7BD94A` |     | Sable        | `#D4B483` |
| D    | `#2EC4B6` |     | Ardoise      | `#3D405B` |
| E    | `#5B7CFA` |     | Nouveau tier | `#9AA0B4` |

- Les tiers par défaut vont du chaud au froid ; le sélecteur propose ces 12 couleurs sur deux lignes de six, mais n'importe quel `#RRGGBB` est accepté.
- Le texte sur un tier est l'encre ou le blanc, celui qui contraste le plus (`readableTextColor`) : ne jamais le fixer à la main.
- Les couleurs des tiers sont les mêmes dans les deux thèmes.

## 4. Typographie

| Famille                                         | Usage                                                                                                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Anybody** (variable en graisse et en largeur) | Titre d'accueil, titres de section (`h1`, `h2`), lettres de tier, minuteur, nom du produit. Graisse 900, élargie (`font-stretch` de 115 à 125 %). |
| **Geist**                                       | Tout le reste : texte, boutons, champs, listes, et petits intitulés (`h3`).                                                                       |

| Style                         | Famille                      | Taille / interligne       | Graisse |
| ----------------------------- | ---------------------------- | ------------------------- | ------- |
| Titre d'accueil               | Anybody 125 %                | 60 / 0,95 (48 sur mobile) | 900     |
| Titre de section (`h2`)       | Anybody 115 %                | 24 / 32                   | 900     |
| Lettre de tier                | Anybody 125 %                | 30 / 36                   | 900     |
| Minuteur (pastille)           | Anybody, chiffres tabulaires | 24 / 32                   | 900     |
| Petit intitulé (`h3`)         | Geist                        | 16 / 24                   | 600     |
| Texte                         | Geist                        | 16 / 24                   | 400     |
| Interface (boutons, libellés) | Geist                        | 14 / 20                   | 500     |
| Légende                       | Geist                        | 12 / 16                   | 500     |

Les nombres qui changent (minuteur, compteurs, tableaux de résultats) sont en chiffres tabulaires.

## 5. Formes, ombre et mouvement

- **Rayons** : 8 px pour une puce d'élément ou un champ (`rounded-md`), 10 px pour un bouton ou une ligne de tier (`rounded-lg`, `--radius`), 16 px pour un panneau, la carte de l'élément en cours et le plateau des retouches finales (`rounded-panel`) ; pilules pour le minuteur, les onglets et les pastilles de présence.
- **Panneaux** (`panelVariants`) : plein (une section ou un formulaire), pointillé (une zone à remplir ou vide), liste (des lignes séparées), atténué (un bandeau d'information).
- **Pas d'ombre, sauf sur ce qui bouge** : `shadow-lift` est réservée à l'élément qu'on fait glisser.
- **La carte de l'élément en cours** est inclinée de −2° (sous `motion-safe`), comme une carte qu'on vient de retourner.
- **Mouvement** : la révélation des résultats (chaque ligne de tier glisse depuis la gauche, 420 ms) et le tremblement des retouches finales à l'approche de la fin. Avec le mouvement réduit, les animations sont instantanées et gardent leur état final ; seul le cercle de chargement continue de tourner.

## 6. Logo et icônes

- **Logo** : trois barres empilées aux couleurs des tiers S, A et B, de 22, 16 et 10 unités sur 24 (`LOGO_BARS`), puis **TierList** en Anybody 900 élargi à 125 %. Le dessin est décoratif : le nom est l'intitulé du lien. Ne jamais réordonner, recolorer ni étirer les barres.
- **Icônes** : Lucide (`lucide-react`), à la taille du texte ; une icône seule (fermer, supprimer) a un nom accessible.

## 7. Accessibilité

- Texte courant d'au moins 4,5:1 dans les deux thèmes (encre sur scène 15,5:1 ; texte atténué 6,1:1 en clair, 7,3:1 en sombre ; blanc sur buzzer 5,1:1) ; bordures de champ, anneaux de focus et icônes d'au moins 3:1.
- Jamais la couleur seule : un tier montre sa lettre, un statut a un mot.
- Les lignes de tier ne rognent pas leur contenu (pas d'`overflow-hidden`), pour que l'anneau de focus reste entier.

## 8. Vocabulaire

Les mots de l'interface (pas d'anglicisme en français quand un mot français existe : _modèle_, _élément_, _hôte_, _retouches finales_, _minuteur_) sont dans le [guide i18n](i18n.fr.md#vocabulaire).
