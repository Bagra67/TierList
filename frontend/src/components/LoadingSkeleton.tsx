import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { panelVariants } from './ui/panel';
import { Skeleton } from './ui/skeleton';

// Nombre de lignes dessinées : assez pour évoquer la page, sans prétendre en connaître la taille
const SKELETON_ROWS: readonly number[] = [0, 1, 2];

interface LoadingSkeletonProps {
  // list : lignes d'une liste (modèles, historique) ; board : lignes de tier (éditeur, salle, résultats)
  shape: 'list' | 'board';
}

// Chargement d'une page : la forme du contenu attendu, et « Chargement… » pour les lecteurs d'écran
export function LoadingSkeleton({ shape }: LoadingSkeletonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <div role="status" className="flex w-full flex-col gap-2">
      <span className="sr-only">{t('common.loading')}</span>
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
