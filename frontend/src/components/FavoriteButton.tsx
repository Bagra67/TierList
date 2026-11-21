import { Bookmark } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Location, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { useFavoriteState, useSetFavorited } from '../api/marketplace';
import { signInRedirectState } from '../auth/signInRedirect';
import { ROUTES } from '../constants/routes';
import { ToggleActionButton } from './ToggleActionButton';
import { Button } from './ui/button';

interface FavoriteToggleProps {
  templateId: string;
  favorited: boolean;
  label?: string;
  ariaLabel?: string;
  compact?: boolean;
}

function FavoriteToggle({
  templateId,
  favorited,
  label,
  ariaLabel,
  compact = false,
}: FavoriteToggleProps) {
  const setFavorited = useSetFavorited(templateId);
  return (
    <ToggleActionButton
      pressed={favorited}
      onToggle={() => setFavorited.mutate(!favorited)}
      pending={setFavorited.isPending}
      error={setFavorited.error}
      icon={Bookmark}
      pressedIconClassName="fill-current"
      label={label}
      ariaLabel={ariaLabel}
      compact={compact}
    />
  );
}

interface CardFavoriteButtonProps {
  templateId: string;
  templateName: string;
}

export function CardFavoriteButton({ templateId, templateName }: CardFavoriteButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const { data: state } = useFavoriteState(templateId, false);

  if (state === undefined || !state.can_favorite) return null;
  return (
    <FavoriteToggle
      templateId={templateId}
      favorited={state.favorited}
      ariaLabel={t('marketplace.card.favorite', { name: templateName })}
      compact
    />
  );
}

export function FavoriteButton({ templateId }: { templateId: string }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const location: Location = useLocation();
  const { data: user } = useCurrentUser();
  const { data: state } = useFavoriteState(templateId, Boolean(user));

  if (user === null) {
    return (
      <Button asChild variant="outline">
        <Link to={ROUTES.LOGIN} state={signInRedirectState(location)}>
          <Bookmark aria-hidden="true" />
          {t('publicTemplate.favorite.signIn')}
        </Link>
      </Button>
    );
  }
  if (state === undefined || !state.can_favorite) return null;
  return (
    <FavoriteToggle
      templateId={templateId}
      favorited={state.favorited}
      label={t('publicTemplate.favorite.button')}
    />
  );
}
