// Barres du logo, de haut en bas : couleurs des tiers S, A et B de la charte (rampe par défaut)
// et largeur sur 24, de plus en plus courtes comme le haut d'une tier list
export const LOGO_BARS = [
  { color: '#FF3B6B', width: 22 },
  { color: '#FF8A2A', width: 16 },
  { color: '#FFC22E', width: 10 },
] as const;

// Texte posé sur une couleur choisie par l'utilisateur (tier) : l'encre de la charte ou du blanc,
// celui des deux qui contraste le plus (theme/contrast.ts)
export const INK_TEXT_COLOR: string = '#1D1640';
export const WHITE_TEXT_COLOR: string = '#FFFFFF';
