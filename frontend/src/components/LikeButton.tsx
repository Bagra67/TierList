import { Heart } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';
import { Link, type Location, useLocation } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { useLikeState, useSetLiked } from '../api/marketplace';
import { signInRedirectState } from '../auth/signInRedirect';
import { ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface LikeButtonProps {
  templateId: string;
  likeCount: number;
}

export function LikeButton({ templateId, likeCount }: LikeButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const location: Location = useLocation();
  const { data: user } = useCurrentUser();
  const { data: state } = useLikeState(templateId, Boolean(user));
  const setLiked = useSetLiked(templateId);
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
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="outline"
        aria-pressed={state.liked}
        disabled={setLiked.isPending}
        onClick={() => setLiked.mutate(!state.liked)}
        className="tabular-nums"
      >
        <Heart
          aria-hidden="true"
          className={state.liked ? 'fill-primary text-primary' : undefined}
        />
        {t('publicTemplate.like.button', { count: state.like_count })}
      </Button>
      {setLiked.isError && (
        <ErrorMessage className="text-sm">{translateError(t, setLiked.error)}</ErrorMessage>
      )}
    </div>
  );
}
