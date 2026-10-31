# Visual identity — "Le Plateau"

English | [Français](visual-identity.fr.md)

The visual identity of TierList, decided on real screens on 2026-10-28 (#213 to #222): the set of a TV game or quiz show, with its light **stage**, its deep **ink**, its **buzzer** and its **spotlight**. This page lists the values and the rules, and where they live in the code. The styled version, with live component previews, is the [design system "TierList — Le Plateau"](https://claude.ai/artifact/1HiN88pvwgBbSjy2p1QysC) (claude.ai, private to its owner, shared on request). When the two differ, **the code is the reference**.

## 1. Where it lives

| Piece                                               | Where                                                                                                 |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Color, radius and shadow tokens (light and `.dark`) | `frontend/src/index.css` (`:root`, `.dark`, `@theme inline`)                                          |
| Tier color presets (12)                             | `frontend/src/constants/templates.ts` (`TIER_COLOR_PRESETS`)                                          |
| Logo bars, ink and white for text on a tier         | `frontend/src/constants/brand.ts`                                                                     |
| Text color on a user-chosen color                   | `frontend/src/theme/contrast.ts` (`readableTextColor`)                                                |
| Panels, buttons, item chips, tier rows              | `components/ui/panel.ts`, `components/ui/button.tsx`, `components/boardStyles.ts`                     |
| Fonts                                               | `@fontsource-variable/anybody` (width axis) and `@fontsource-variable/geist`, imported by `index.css` |
| Favicon                                             | `frontend/public/favicon.svg`                                                                         |

The tokens are `oklch()` values; the hex values below are their sRGB equivalents.

## 2. Colors

| Role         | Token                          | Light     | Dark      | Use                                                                  |
| ------------ | ------------------------------ | --------- | --------- | -------------------------------------------------------------------- |
| Stage        | `background`                   | `#F4F5FA` | `#140F2B` | Background of every page.                                            |
| Ink          | `foreground`                   | `#1D1640` | `#ECEAF6` | Text and headings.                                                   |
| Surface      | `card`, `popover`              | `#FFFFFF` | `#1D1640` | Panels, cards, item chips, menus.                                    |
| Buzzer       | `primary`                      | `#D41E5B` | `#FF5C8A` | The main action of an area, the item to place now, the urgent timer. |
| On buzzer    | `primary-foreground`           | `#FFFFFF` | `#140F2B` | Text on the buzzer.                                                  |
| Neutral      | `secondary`, `muted`, `accent` | `#E9EAF3` | `#2A2257` | Secondary buttons, information strips, hover.                        |
| Muted text   | `muted-foreground`             | `#5E5878` | `#A49FBF` | Hints, captions, counters.                                           |
| Error        | `destructive`                  | `#B32517` | `#FA8467` | Errors and destructive actions.                                      |
| Border       | `border`                       | `#D5D6E4` | `#3A3170` | Panels, tier rows, separators.                                       |
| Field border | `input`                        | `#8C88A6` | `#6A6296` | Form fields (3:1 with the background).                               |
| Focus        | `ring`                         | `#3B5BDB` | `#8FA6FF` | Keyboard focus ring.                                                 |
| Success      | `success`                      | `#168057` | `#3FCB93` | Confirmations, online presence.                                      |
| Warning      | `warning`                      | `#AD7300` | `#FFC22E` | Warning border and light background, never text.                     |
| Spotlight    | `spotlight`                    | `#FFC22E` | `#FFC22E` | Solid background of the round timer and the host label, ink on it.   |

Rules:

- **One buzzer per area.** A second main action becomes secondary or outline.
- **The spotlight is a background, never a line.** As a border or text it is too pale on the light stage: warnings use `warning`.
- **An error never looks like the buzzer**: `destructive` differs in hue and lightness.
- **Focus is blue** (`ring`): it matches no tier color and not the buzzer.
- **The final touches** (final cooldown) are played on a **dark set whatever the theme**: the area takes the `.dark` tokens, with a `warning` border (`CooldownStage`).

## 3. Tier colors

| Tier | Color     |     | Preset   | Color     |
| ---- | --------- | --- | -------- | --------- |
| S    | `#FF3B6B` |     | Sky      | `#4FC3F7` |
| A    | `#FF8A2A` |     | Lilac    | `#A78BFA` |
| B    | `#FFC22E` |     | Orchid   | `#F06BD0` |
| C    | `#7BD94A` |     | Sand     | `#D4B483` |
| D    | `#2EC4B6` |     | Slate    | `#3D405B` |
| E    | `#5B7CFA` |     | New tier | `#9AA0B4` |

- The default tiers go from warm to cold; the picker offers these 12 colors in two rows of six, but any `#RRGGBB` is accepted.
- Text on a tier is the ink or white, whichever contrasts more (`readableTextColor`): never hard-code it.
- Tier colors are the same in both themes.

## 4. Typography

| Family                                  | Use                                                                                                                              |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Anybody** (variable weight and width) | Home title, section headings (`h1`, `h2`), tier letters, timer, product name. Weight 900, widened (`font-stretch` 115 to 125 %). |
| **Geist**                               | Everything else: text, buttons, fields, lists, and small headings (`h3`).                                                        |

| Style                | Family                   | Size / line height       | Weight |
| -------------------- | ------------------------ | ------------------------ | ------ |
| Home title           | Anybody 125 %            | 60 / 0.95 (48 on mobile) | 900    |
| Section title (`h2`) | Anybody 115 %            | 24 / 32                  | 900    |
| Tier letter          | Anybody 125 %            | 30 / 36                  | 900    |
| Timer (pill)         | Anybody, tabular figures | 24 / 32                  | 900    |
| Small heading (`h3`) | Geist                    | 16 / 24                  | 600    |
| Body                 | Geist                    | 16 / 24                  | 400    |
| UI (buttons, labels) | Geist                    | 14 / 20                  | 500    |
| Caption              | Geist                    | 12 / 16                  | 500    |

Changing numbers (timer, counters, results tables) use tabular figures.

## 5. Shapes, shadow and motion

- **Radii**: 8 px for an item chip or a field (`rounded-md`), 10 px for a button or a tier row (`rounded-lg`, `--radius`), 16 px for a panel, the current item card and the final touches set (`rounded-panel`); pills for the timer, tabs and presence dots.
- **Panels** (`panelVariants`): solid (a section or form), dashed (an area to fill or empty), list (separated rows), muted (an information strip).
- **No shadow except on what moves**: `shadow-lift` is reserved for the dragged item.
- **The current item card** is tilted by −2° (under `motion-safe`), like a card just turned over.
- **Motion**: the results reveal (each tier row slides in from the left, 420 ms) and the shake of the final touches as the end nears. With reduced motion, animations are instant and keep their final state; only the spinner keeps turning.

## 6. Logo and icons

- **Logo**: three stacked bars in the S, A and B tier colors, 22, 16 and 10 units wide out of 24 (`LOGO_BARS`), then **TierList** in Anybody 900 widened to 125 %. The drawing is decorative: the name is the link's label. Never reorder, recolor or stretch the bars.
- **Icons**: Lucide (`lucide-react`), at text size; an icon alone (close, delete) has an accessible name.

## 7. Accessibility

- Body text at least 4.5:1 in both themes (ink on stage 15.5:1; muted text 6.1:1 light, 7.3:1 dark; white on buzzer 5.1:1); field borders, focus rings and icons at least 3:1.
- Never color alone: a tier shows its letter, a status has a word.
- Tier rows do not clip their content (no `overflow-hidden`), so the focus ring stays whole.

## 8. Vocabulary

The interface wording (no English word in French when a French one exists: _modèle_, _élément_, _hôte_, _retouches finales_, _minuteur_) is in the [i18n guide](i18n.md#vocabulary).
