import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { ImageModerationAction, RecentUpload } from '../api/moderation';
import { moderationAccountPath } from '../constants/routes';
import { Button } from './ui/button';

interface UploadCardProps {
  upload: RecentUpload;
  onAction: (upload: RecentUpload, action: ImageModerationAction) => void;
}

export function UploadCard({ upload, onAction }: UploadCardProps) {
  const { t } = useTranslation();
  const author: string = upload.author_name ?? t('moderation.uploads.deletedAccount');
  const date: Date = new Date(upload.created_at);
  const isHidden: boolean = upload.status === 'hidden';
  const actions: ImageModerationAction[] = isHidden ? ['unhide', 'delete'] : ['hide', 'delete'];

  return (
    <li className="flex flex-col gap-3 rounded-panel border bg-card p-3">
      <div className="relative">
        <img
          src={upload.url}
          alt={t('moderation.uploads.imageAlt', { author, date })}
          className="aspect-video w-full rounded-lg bg-muted object-contain"
        />
        {isHidden && (
          <span className="absolute top-2 left-2 rounded-md bg-background/90 px-2 py-0.5 text-xs font-semibold">
            {t('moderation.uploads.hiddenBadge')}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1 text-sm">
        {upload.author_id === null ? (
          <span className="font-semibold">{author}</span>
        ) : (
          <Link
            to={moderationAccountPath(upload.author_id)}
            className="font-semibold underline-offset-4 hover:underline"
          >
            {author}
          </Link>
        )}
        <span className="text-muted-foreground">{t('moderation.uploads.at', { date })}</span>
        <span className="text-muted-foreground">
          {t('moderation.uploads.templates', { count: upload.template_names.length })}
          {' · '}
          {t('moderation.uploads.games', { count: upload.game_count })}
        </span>
        {upload.template_names.length > 0 && (
          <span className="text-muted-foreground">
            {t('moderation.uploads.templateNames', { names: upload.template_names })}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {actions.map((action: ImageModerationAction) => (
          <Button
            key={action}
            type="button"
            size="sm"
            variant={action === 'delete' ? 'destructive' : 'secondary'}
            aria-label={t(`moderation.uploads.actionLabel.${action}`, { author, date })}
            onClick={() => onAction(upload, action)}
          >
            {t(`moderation.actions.${action}`)}
          </Button>
        ))}
      </div>
    </li>
  );
}
