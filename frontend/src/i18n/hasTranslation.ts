// Vrai si `code` (reçu du backend : code d'erreur, paramètre d'URL…) a une traduction parmi
// `translations` (une branche de fr.ts) ; affine son type pour construire une clé typée.
export function hasTranslation<T extends object>(
  translations: T,
  code: string | null | undefined,
): code is Extract<keyof T, string> {
  return typeof code === 'string' && Object.hasOwn(translations, code);
}
