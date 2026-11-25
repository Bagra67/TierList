import { Copy } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Location, type NavigateFunction, useLocation, useNavigate } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { type PublicTemplate, useCopyState } from '../api/marketplace';
import { type Template, useCopyTemplate } from '../api/templates';
import { signInRedirectState } from '../auth/signInRedirect';
import { ROUTES, templateEditorPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

export function CopyTemplateButton({ template }: { template: PublicTemplate }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const location: Location = useLocation();
  const navigate: NavigateFunction = useNavigate();
  const { data: user } = useCurrentUser();
  const { data: state } = useCopyState(template.id, Boolean(user) && template.copy_allowed);
  const copyMutation = useCopyTemplate();

  if (!template.copy_allowed || user === undefined) return null;
  if (user === null) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Button asChild variant="secondary">
          <Link to={ROUTES.LOGIN} state={signInRedirectState(location)}>
            <Copy aria-hidden="true" />
            {t('publicTemplate.copy.signIn')}
          </Link>
        </Button>
      </div>
    );
  }
  if (state === undefined || !state.can_copy) return null;

  async function handleClick() {
    let copy: Template;
    try {
      copy = await copyMutation.mutateAsync(template.id);
    } catch {
      return;
    }
    await navigate(templateEditorPath(copy.id));
  }

  return (
    <div className="flex max-w-xs flex-col items-start gap-1 sm:items-end">
      <Button
        type="button"
        variant="secondary"
        disabled={copyMutation.isPending}
        onClick={handleClick}
      >
        <Copy aria-hidden="true" />
        {copyMutation.isPending
          ? t('publicTemplate.copy.submitting')
          : t('publicTemplate.copy.button')}
      </Button>
      {copyMutation.isError ? (
        <ErrorMessage className="text-sm sm:text-right">
          {translateError(t, copyMutation.error)}
        </ErrorMessage>
      ) : (
        <p className="text-xs text-muted-foreground sm:text-right">
          {t('publicTemplate.copy.hint')}
        </p>
      )}
    </div>
  );
}
