import { INK_TEXT_COLOR, WHITE_TEXT_COLOR } from '../constants/brand';

const SRGB_LINEAR_THRESHOLD: number = 0.04045;
const WCAG_RED_LUMINANCE_WEIGHT: number = 0.2126;
const WCAG_GREEN_LUMINANCE_WEIGHT: number = 0.7152;
const WCAG_BLUE_LUMINANCE_WEIGHT: number = 0.0722;

function srgbChannelToLinear(channelFrom0To255: number): number {
  const ratio: number = channelFrom0To255 / 255;
  if (ratio <= SRGB_LINEAR_THRESHOLD) return ratio / 12.92;
  return ((ratio + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(hexColor: string): number {
  const red: number = srgbChannelToLinear(parseInt(hexColor.slice(1, 3), 16));
  const green: number = srgbChannelToLinear(parseInt(hexColor.slice(3, 5), 16));
  const blue: number = srgbChannelToLinear(parseInt(hexColor.slice(5, 7), 16));
  return (
    WCAG_RED_LUMINANCE_WEIGHT * red +
    WCAG_GREEN_LUMINANCE_WEIGHT * green +
    WCAG_BLUE_LUMINANCE_WEIGHT * blue
  );
}

export function contrastRatio(firstColor: string, secondColor: string): number {
  const first: number = relativeLuminance(firstColor);
  const second: number = relativeLuminance(secondColor);
  const lighter: number = Math.max(first, second);
  const darker: number = Math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

export function readableTextColor(backgroundColor: string): string {
  const inkContrast: number = contrastRatio(INK_TEXT_COLOR, backgroundColor);
  const whiteContrast: number = contrastRatio(WHITE_TEXT_COLOR, backgroundColor);
  return inkContrast >= whiteContrast ? INK_TEXT_COLOR : WHITE_TEXT_COLOR;
}
