import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { EmailVerificationBanner } from '../components/EmailVerificationBanner';
import { JoinRoomForm } from '../components/JoinRoomForm';
import { Button } from '../components/ui/button';
import { LOGO_BARS } from '../constants/brand';
import { ROUTES } from '../constants/routes';
import { readableTextColor } from '../theme/contrast';

// Les étapes d'une partie, dans l'ordre (home.steps.*), numérotées aux couleurs du logo : une
// étape de plus doit choisir sa couleur
const HOME_STEPS = [
  { key: 'template', color: LOGO_BARS[0].color },
  { key: 'room', color: LOGO_BARS[1].color },
  { key: 'play', color: LOGO_BARS[2].color },
] as const;

export function HomePage() {
  const { data: user } = useCurrentUser();
  const { t } = useTranslation();
  const stepsHeadingId: string = useId();

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      {user && <p className="text-sm">{t('auth.signedInAs', { name: user.display_name })}</p>}
      {user && <EmailVerificationBanner user={user} />}
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('home.title')}</h1>
        <p className="text-lg">{t('home.intro')}</p>
      </div>
      <section aria-labelledby={stepsHeadingId} className="flex w-full flex-col gap-3">
        <h2 id={stepsHeadingId} className="text-lg font-semibold">
          {t('home.steps.title')}
        </h2>
        <ol className="flex flex-col gap-2">
          {HOME_STEPS.map((step, index: number) => (
            <li key={step.key} className="flex items-center gap-3">
              {/* La liste numérotée annonce déjà le rang : le chiffre affiché est décoratif */}
              <span
                aria-hidden="true"
                style={{ backgroundColor: step.color, color: readableTextColor(step.color) }}
                className="flex size-8 shrink-0 items-center justify-center rounded-md font-heading font-black"
              >
                {index + 1}
              </span>
              {t(`home.steps.${step.key}`)}
            </li>
          ))}
        </ol>
        <Button asChild className="self-start">
          <Link to={ROUTES.TEMPLATES}>{t('home.prepareTemplate')}</Link>
        </Button>
      </section>
      <JoinRoomForm />
    </main>
  );
}
