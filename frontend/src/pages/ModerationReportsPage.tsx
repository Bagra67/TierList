import { type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { type HiddenGame, useHiddenGames, useUnhideGame } from '../api/moderation';
import { ErrorMessage } from '../components/ErrorMessage';
import { ModerationReasonDialog } from '../components/ModerationReasonDialog';
import { ReportQueue } from '../components/ReportQueue';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { translateError } from '../errors/apiError';

export function ModerationReportsPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.reports.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.reports.intro')}</p>
      </div>
      <ReportQueue emptyMessage={t('moderation.reports.empty')} />
      <HiddenGames />
    </div>
  );
}

function HiddenGames() {
  const { t } = useTranslation();
  const { data, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } = useHiddenGames();
  const games: HiddenGame[] = data?.pages.flatMap((page) => page.games) ?? [];
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [chosenGame, setChosenGame] = useState<HiddenGame | null>(null);
  const unhideMutation = useUnhideGame();

  function openDialog(game: HiddenGame) {
    setChosenGame(game);
    dialogRef.current?.showModal();
  }

  async function unhide(reason: string): Promise<boolean> {
    if (chosenGame === null) return false;
    try {
      await unhideMutation.mutateAsync({ gameId: chosenGame.id, reason });
    } catch {
      return false;
    }
    return true;
  }

  if (isError) return <ErrorMessage>{translateError(t, error)}</ErrorMessage>;

  return (
    <>
      {games.length > 0 && (
        <section className="flex w-full flex-col items-start gap-3">
          <h2 className="text-lg font-semibold">{t('moderation.reports.hiddenGames.title')}</h2>
          <ul className={panelVariants({ variant: 'list' })}>
            {games.map((game: HiddenGame) => (
              <li key={game.id} className="flex flex-wrap items-center gap-2 px-4 py-2">
                <span className="font-medium">{game.template_name}</span>
                <span className="text-sm text-muted-foreground">
                  {t('moderation.reports.hiddenGames.hiddenAt', { date: new Date(game.hidden_at) })}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                  aria-label={t('moderation.reports.hiddenGames.unhideLabel', {
                    name: game.template_name,
                  })}
                  onClick={() => openDialog(game)}
                >
                  {t('moderation.reports.hiddenGames.unhide')}
                </Button>
              </li>
            ))}
          </ul>
          {hasNextPage && (
            <Button
              type="button"
              variant="outline"
              disabled={isFetchingNextPage}
              onClick={() => void fetchNextPage()}
            >
              {isFetchingNextPage ? t('common.loading') : t('moderation.reports.more')}
            </Button>
          )}
        </section>
      )}
      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t('moderation.reports.hiddenGames.dialogTitle')}
        description={t('moderation.reports.hiddenGames.dialogDescription')}
        submitLabel={t('moderation.reports.hiddenGames.unhide')}
        submittingLabel={t('moderation.reports.hiddenGames.unhiding')}
        destructive={false}
        isPending={unhideMutation.isPending}
        translatedFailureMessage={
          unhideMutation.isError ? translateError(t, unhideMutation.error) : null
        }
        onSubmit={unhide}
        onClose={() => {
          unhideMutation.reset();
          setChosenGame(null);
        }}
      />
    </>
  );
}
