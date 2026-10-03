import { useTranslation } from 'react-i18next';

import { useRequestEmailVerification, type User } from '../api/auth';
import { translateError } from '../errors/apiError';
import { Button } from './ui/button';

// Invite à confirmer l'adresse tant qu'elle ne l'est pas ; la connexion reste possible sans
export function EmailVerificationBanner({ user }: { user: User }) {
  const resendMutation = useRequestEmailVerification();
  const { t } = useTranslation();

  if (user.email_verified) return null;

  return (
    <section className="flex w-full flex-col gap-2 rounded-lg border bg-muted/50 p-4 text-sm">
      <p>{t('account.verification.pending', { email: user.email })}</p>
      {resendMutation.isSuccess && <p role="status">{t('account.verification.resent')}</p>}
      {resendMutation.isError && (
        <p role="alert" className="text-destructive">
          {translateError(t, resendMutation.error)}
        </p>
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
    </section>
  );
}
