import { useTranslation } from 'react-i18next';

import type { User } from '../api/auth';
import { ResendVerificationEmailButton } from './ResendVerificationEmailButton';

export function EmailVerificationBanner({ user }: { user: User }) {
  const { t } = useTranslation();

  if (user.email_verified) return null;

  return (
    <section className="flex w-full flex-col gap-2 rounded-lg border bg-muted/50 p-4 text-sm">
      <p>{t('account.verification.pending', { email: user.email })}</p>
      <ResendVerificationEmailButton />
    </section>
  );
}
