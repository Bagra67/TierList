import { useTranslation } from 'react-i18next';

interface DeletionDetailsProps {
  deletedAt: string;
  deletionReason: string | null;
}

export function DeletionDetails({ deletedAt, deletionReason }: DeletionDetailsProps) {
  const { t } = useTranslation();
  const date: Date = new Date(deletedAt);
  if (deletionReason === null) {
    return (
      <p className="text-sm text-muted-foreground">
        {t('moderation.deletedTemplates.deletedByOwner', { date })}
      </p>
    );
  }
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
      <span>{t('moderation.deletedTemplates.deletedOn', { date })}</span>
      <span className="rounded-md border border-border px-2 py-0.5 text-xs font-semibold text-foreground">
        {t('moderation.deletedTemplates.byModeration')}
      </span>
      <span className="italic">
        {t('moderation.deletedTemplates.reason', { reason: deletionReason })}
      </span>
    </p>
  );
}
