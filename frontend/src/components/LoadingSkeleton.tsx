import { useEffect, useState } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { panelVariants } from './ui/panel';
import { Skeleton } from './ui/skeleton';

const SKELETON_ROWS: readonly number[] = [0, 1, 2];

interface LoadingSkeletonProps {
  shape: 'list' | 'board';
}

export function LoadingSkeleton({ shape }: LoadingSkeletonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const [isAnnounced, setIsAnnounced] = useState<boolean>(false);
  useEffect(() => {
    const timer: number = window.setTimeout(() => setIsAnnounced(true), 0);
    return () => window.clearTimeout(timer);
  }, []);
  return (
    <div role="status" className="flex w-full flex-col gap-2">
      <span className="sr-only">{isAnnounced && t('common.loading')}</span>
      {shape === 'list' ? (
        <div className={panelVariants({ variant: 'list' })}>
          {SKELETON_ROWS.map((row: number) => (
            <div key={row} className="flex flex-col gap-2 px-4 py-3">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        SKELETON_ROWS.map((row: number) => (
          <div key={row} className="flex h-14 w-full gap-2 sm:h-16">
            <Skeleton className="w-16 rounded-[10px] sm:w-20" />
            <Skeleton className="flex-1 rounded-[10px]" />
          </div>
        ))
      )}
    </div>
  );
}
