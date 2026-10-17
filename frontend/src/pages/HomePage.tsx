import { useTranslation } from 'react-i18next';

import { useCurrentUser } from '../api/auth';
import { EmailVerificationBanner } from '../components/EmailVerificationBanner';
import { JoinRoomForm } from '../components/JoinRoomForm';

export function HomePage() {
  const { data: user } = useCurrentUser();
  const { t } = useTranslation();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      {user && <p className="text-sm">{t('auth.signedInAs', { name: user.display_name })}</p>}
      {user && <EmailVerificationBanner user={user} />}
      <h1 className="text-2xl font-semibold">{t('home.title')}</h1>
      <JoinRoomForm />
    </main>
  );
}
