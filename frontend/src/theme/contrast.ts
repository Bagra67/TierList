import { INK_TEXT_COLOR, WHITE_TEXT_COLOR } from '../constants/brand';

// Calculs de contraste WCAG 2 (https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio) sur des
// couleurs #RRGGBB, le format des couleurs de tier

// Passe une composante (0 à 255) de l'espace sRGB à l'espace linéaire
function linearChannel(value: number): number {
  const ratio: number = value / 255;
  if (ratio <= 0.04045) return ratio / 12.92;
  return ((ratio + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(hexColor: string): number {
  const red: number = linearChannel(parseInt(hexColor.slice(1, 3), 16));
  const green: number = linearChannel(parseInt(hexColor.slice(3, 5), 16));
  const blue: number = linearChannel(parseInt(hexColor.slice(5, 7), 16));
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

// De 1 (aucun contraste) à 21 (noir sur blanc), dans n'importe quel ordre
export function contrastRatio(firstColor: string, secondColor: string): number {
  const first: number = relativeLuminance(firstColor);
  const second: number = relativeLuminance(secondColor);
  const lighter: number = Math.max(first, second);
  const darker: number = Math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

// Couleur du texte posé sur un fond choisi par l'utilisateur : l'encre ou le blanc, selon
// lequel se lit le mieux
export function readableTextColor(backgroundColor: string): string {
  const inkContrast: number = contrastRatio(INK_TEXT_COLOR, backgroundColor);
  const whiteContrast: number = contrastRatio(WHITE_TEXT_COLOR, backgroundColor);
  return inkContrast >= whiteContrast ? INK_TEXT_COLOR : WHITE_TEXT_COLOR;
}
