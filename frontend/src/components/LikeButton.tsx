import { cn } from 'cn';
import { Heart } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Location, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { type LikeState, useLikeState, useSetLiked } from '../api/marketplace';
import { signInRedirectState } from '../auth/signInRedirect';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface LikeButtonProps {
  templateId: string;
  likeCount: number;
}

interface LikeToggleProps {
  templateId: string;
  state: LikeState;
  label: string;
  ariaLabel?: string;
  compact?: boolean;
}

function LikeToggle({ templateId, state, label, ariaLabel, compact = false }: LikeToggleProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const setLiked = useSetLiked(templateId);
  return (
    <div className={cn('flex flex-col items-end gap-1', compact && 'relative z-10')}>
      <Button
        type="button"
        variant={compact ? 'ghost' : 'outline'}
        size={compact ? 'sm' : 'default'}
        aria-pressed={state.liked}
        aria-label={ariaLabel}
        disabled={setLiked.isPending}
        onClick={() => setLiked.mutate(!state.liked)}
        className={cn('tabular-nums', compact && 'font-medium text-primary')}
      >
        <Heart
          aria-hidden="true"
          className={state.liked ? 'fill-primary text-primary' : undefined}
        />
        {label}
      </Button>
      {setLiked.isError && (
        <ErrorMessage className={compact ? 'text-right text-xs' : 'text-sm'}>
          {translateError(t, setLiked.error)}
        </ErrorMessage>
      )}
    </div>
  );
}

interface CardLikeButtonProps extends LikeButtonProps {
  templateName: string;
}

export function CardLikeButton({ templateId, templateName, likeCount }: CardLikeButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const { data: state } = useLikeState(templateId, false);

  if (state === undefined || !state.can_like) {
    return (
      <p className="flex items-center gap-1.5 text-sm font-medium text-primary tabular-nums">
        <Heart aria-hidden="true" className="size-4" />
        {t('publicTemplate.like.count', { count: state?.like_count ?? likeCount })}
      </p>
    );
  }
  return (
    <LikeToggle
      templateId={templateId}
      state={state}
      label={t('publicTemplate.like.count', { count: state.like_count })}
      ariaLabel={t('marketplace.card.like', { name: templateName, count: state.like_count })}
      compact
    />
  );
}

export function LikeButton({ templateId, likeCount }: LikeButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const location: Location = useLocation();
  const { data: user } = useCurrentUser();
  const { data: state } = useLikeState(templateId, Boolean(user));
  const count: string = t('publicTemplate.like.count', { count: likeCount });

  if (user === null) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Button asChild variant="outline">
          <Link to={ROUTES.LOGIN} state={signInRedirectState(location)}>
            <Heart aria-hidden="true" />
            {t('publicTemplate.like.signIn')}
          </Link>
        </Button>
        <p className="text-sm text-muted-foreground tabular-nums">{count}</p>
      </div>
    );
  }
  if (state === undefined || !state.can_like) {
    return (
      <p className="flex h-9 items-center gap-1.5 text-sm text-muted-foreground tabular-nums">
        <Heart aria-hidden="true" className="size-4" />
        {count}
      </p>
    );
  }
  return (
    <LikeToggle
      templateId={templateId}
      state={state}
      label={t('publicTemplate.like.button', { count: state.like_count })}
    />
  );
}
