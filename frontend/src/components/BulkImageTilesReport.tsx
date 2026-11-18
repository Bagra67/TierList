import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { BulkImageTiles, SkippedImage } from './useBulkImageTiles';

export function BulkImageTilesReport({ report }: { report: BulkImageTiles }) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const progress: number = report.total === 0 ? 100 : (report.done / report.total) * 100;

  return (
    <div role="status" className="flex w-full flex-col gap-2 text-sm">
      {report.isRunning ? (
        <>
          <p>{t('templates.editor.bulk.progress', { done: report.done, total: report.total })}</p>
          <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
        </>
      ) : (
        <p className="font-medium">
          {t('templates.editor.bulk.added', { count: report.addedCount })}
        </p>
      )}
      {report.skipped.length > 0 && (
        <div className="flex flex-col gap-1 text-destructive">
          <p>{t('templates.editor.bulk.skipped', { count: report.skipped.length })}</p>
          <ul className="list-disc pl-5">
            {report.skipped.map((skippedImage: SkippedImage, index: number) => (
              <li key={`${skippedImage.fileName}-${index}`}>
                {t('templates.editor.bulk.skippedImage', {
                  name: skippedImage.fileName,
                  reason: skippedImage.reason,
                })}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
