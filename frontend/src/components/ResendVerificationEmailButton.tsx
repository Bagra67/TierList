import { useTranslation } from 'react-i18next';

import { useRequestEmailVerification } from '../api/auth';
import { translateError } from '../errors/apiError';
import { Button } from './ui/button';
import { ErrorMessage } from './ErrorMessage';

interface ResendVerificationEmailButtonProps {
  size?: 'default' | 'xs';
}

export function ResendVerificationEmailButton({
  size = 'default',
}: ResendVerificationEmailButtonProps) {
  const resendMutation = useRequestEmailVerification();
  const { t } = useTranslation();

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size={size}
        disabled={resendMutation.isPending}
        onClick={() => resendMutation.mutate()}
        className="self-start"
      >
        {resendMutation.isPending
          ? t('account.verification.resending')
          : t('account.verification.resend')}
      </Button>
      {resendMutation.isSuccess && (
        <p role="status" className="w-full">
          {t('account.verification.resent')}
        </p>
      )}
      {resendMutation.isError && (
        <ErrorMessage className="w-full">{translateError(t, resendMutation.error)}</ErrorMessage>
      )}
    </>
  );
}
