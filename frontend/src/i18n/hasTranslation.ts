export function hasTranslation<T extends object>(
  translations: T,
  code: string | null | undefined,
): code is Extract<keyof T, string> {
  return typeof code === 'string' && Object.hasOwn(translations, code);
}
