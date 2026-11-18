import { useEffect } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

export function useDocumentTitle(page: string | undefined): void {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const siteTitle: string = t('documentTitle.site');
  const pageTitle: string | undefined =
    page === undefined ? undefined : t('documentTitle.page', { page });

  useEffect(() => {
    if (pageTitle === undefined) {
      return undefined;
    }
    document.title = pageTitle;
    return () => {
      document.title = siteTitle;
    };
  }, [pageTitle, siteTitle]);
}
