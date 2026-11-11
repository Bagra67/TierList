import { useTranslation } from 'react-i18next';

import { useRequestEmailVerification } from '../api/auth';
import { translateError } from '../errors/apiError';
import { Button } from './ui/button';
import { ErrorMessage } from './ErrorMessage';

export function ResendVerificationEmailButton() {
  const resendMutation = useRequestEmailVerification();
  const { t } = useTranslation();

  return (
    <>
      {resendMutation.isSuccess && <p role="status">{t('account.verification.resent')}</p>}
      {resendMutation.isError && (
        <ErrorMessage>{translateError(t, resendMutation.error)}</ErrorMessage>
      )}
      <div>
        <Button
          type="button"
          variant="outline"
          disabled={resendMutation.isPending}
          onClick={() => resendMutation.mutate()}
        >
          {resendMutation.isPending
            ? t('account.verification.resending')
            : t('account.verification.resend')}
        </Button>
      </div>
    </>
  );
}
