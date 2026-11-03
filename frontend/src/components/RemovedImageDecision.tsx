import { useTranslation } from 'react-i18next';

interface RemovedImageDecisionProps {
  status: 'hidden' | 'deleted';
  reason: string | null;
}

export function RemovedImageDecision({ status, reason }: RemovedImageDecisionProps) {
  const { t } = useTranslation();
  return (
    <p className="text-xs break-words text-muted-foreground">
      <span className="block font-medium">
        {status === 'hidden'
          ? t('templates.removedImage.hidden')
          : t('templates.removedImage.deleted')}
      </span>
      {reason !== null && t('templates.hidden.reason', { reason })}
    </p>
  );
}
