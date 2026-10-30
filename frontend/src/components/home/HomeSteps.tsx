import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import { LOGO_BARS } from '../../constants/brand';
import { readableTextColor } from '../../theme/contrast';

// Les étapes d'une partie, dans l'ordre (home.steps.*), numérotées aux couleurs du logo : une
// étape de plus doit choisir sa couleur. C'est une vraie séquence, d'où les numéros
const HOME_STEPS = [
  { key: 'template', color: LOGO_BARS[0].color },
  { key: 'room', color: LOGO_BARS[1].color },
  { key: 'play', color: LOGO_BARS[2].color },
] as const;

export function HomeSteps() {
  const { t } = useTranslation();
  const headingId: string = useId();

  return (
    <section aria-labelledby={headingId} className="flex w-full flex-col gap-4">
      <h2 id={headingId} className="text-lg font-semibold">
        {t('home.steps.title')}
      </h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {HOME_STEPS.map((step, index: number) => (
          <li key={step.key} className="flex items-start gap-3">
            {/* La liste numérotée annonce déjà le rang : le chiffre affiché est décoratif */}
            <span
              aria-hidden="true"
              style={{ backgroundColor: step.color, color: readableTextColor(step.color) }}
              className="flex size-8 shrink-0 items-center justify-center rounded-md font-heading font-black"
            >
              {index + 1}
            </span>
            <span className="pt-1">{t(`home.steps.${step.key}`)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
