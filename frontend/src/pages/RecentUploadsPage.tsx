import { type FormEvent, type RefObject, useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  type ImageModerationAction,
  type ListedImageStatus,
  type RecentUpload,
  type RecentUploadsFilters,
  useModerateImage,
  useRecentUploads,
} from '../api/moderation';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ModerationReasonDialog } from '../components/ModerationReasonDialog';
import { TextField } from '../components/TextField';
import { UploadCard } from '../components/UploadCard';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { NativeSelect } from '../components/ui/native-select';
import { translateError } from '../errors/apiError';

// Début d'un jour choisi (AAAA-MM-JJ), dans le fuseau du super admin, en date ISO avec fuseau
function startOfDay(day: string): string {
  return new Date(`${day}T00:00:00`).toISOString();
}

// Début du jour suivant : le dernier jour choisi est inclus en entier
function startOfNextDay(day: string): string {
  const next: Date = new Date(`${day}T00:00:00`);
  next.setDate(next.getDate() + 1);
  return next.toISOString();
}

interface PendingAction {
  upload: RecentUpload;
  action: ImageModerationAction;
}

// Derniers envois (US-1.7) : les images envoyées, des plus récentes aux plus anciennes, pour
// repérer un problème avant qu'on le signale. Chaque image peut être masquée, réaffichée ou
// supprimée (US-1.4), avec un motif écrit au journal.
export function RecentUploadsPage() {
  const { t } = useTranslation();
  const fromId: string = useId();
  const toId: string = useId();
  const statusId: string = useId();
  // L'auteur cherché n'est appliqué qu'à l'envoi du formulaire : une requête par recherche
  const [authorDraft, setAuthorDraft] = useState<string>('');
  const [author, setAuthor] = useState<string | undefined>(undefined);
  const [fromDay, setFromDay] = useState<string>('');
  const [toDay, setToDay] = useState<string>('');
  const [status, setStatus] = useState<ListedImageStatus | ''>('');
  const filters: RecentUploadsFilters = {
    author,
    createdAfter: fromDay === '' ? undefined : startOfDay(fromDay),
    createdBefore: toDay === '' ? undefined : startOfNextDay(toDay),
    status: status === '' ? undefined : status,
  };
  const isFiltered: boolean =
    author !== undefined || fromDay !== '' || toDay !== '' || status !== '';
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useRecentUploads(filters);
  const uploads: RecentUpload[] = data?.pages.flatMap((page) => page.images) ?? [];

  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const moderateMutation = useModerateImage();

  function applyAuthor(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const searched: string = authorDraft.trim();
    setAuthor(searched === '' ? undefined : searched);
  }

  function openDialog(upload: RecentUpload, action: ImageModerationAction) {
    setPending({ upload, action });
    dialogRef.current?.showModal();
  }

  async function moderate(reason: string): Promise<boolean> {
    if (pending === null) return false;
    try {
      await moderateMutation.mutateAsync({
        imageId: pending.upload.id,
        action: pending.action,
        reason,
      });
    } catch {
      return false; // l'erreur est affichée depuis moderateMutation.error
    }
    return true;
  }

  function closeDialog() {
    moderateMutation.reset();
    setPending(null);
  }

  const action: ImageModerationAction = pending?.action ?? 'hide';

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.uploads.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.uploads.intro')}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <form onSubmit={applyAuthor} className="flex flex-wrap items-end gap-3">
          <TextField
            label={t('moderation.uploads.author')}
            name="author"
            placeholder={t('moderation.uploads.authorPlaceholder')}
            value={authorDraft}
            onChange={(event) => setAuthorDraft(event.target.value)}
          />
          <Button type="submit" variant="outline">
            {t('moderation.uploads.search')}
          </Button>
        </form>
        <div className="flex flex-col gap-2">
          <Label htmlFor={fromId}>{t('moderation.uploads.from')}</Label>
          <Input
            id={fromId}
            type="date"
            value={fromDay}
            max={toDay === '' ? undefined : toDay}
            onChange={(event) => setFromDay(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={toId}>{t('moderation.uploads.to')}</Label>
          <Input
            id={toId}
            type="date"
            value={toDay}
            min={fromDay === '' ? undefined : fromDay}
            onChange={(event) => setToDay(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={statusId}>{t('moderation.uploads.status')}</Label>
          <NativeSelect
            id={statusId}
            value={status}
            onChange={(event) => setStatus(event.target.value as ListedImageStatus | '')}
          >
            <option value="">{t('moderation.uploads.allStatuses')}</option>
            <option value="visible">{t('moderation.uploads.visible')}</option>
            <option value="hidden">{t('moderation.uploads.hidden')}</option>
          </NativeSelect>
        </div>
      </div>

      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && uploads.length === 0 && (
        <EmptyState
          message={
            isFiltered ? t('moderation.uploads.emptyFiltered') : t('moderation.uploads.empty')
          }
        />
      )}
      {uploads.length > 0 && (
        <ul className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {uploads.map((upload: RecentUpload) => (
            <UploadCard key={upload.id} upload={upload} onAction={openDialog} />
          ))}
        </ul>
      )}
      {hasNextPage && (
        <Button
          type="button"
          variant="outline"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          {isFetchingNextPage ? t('common.loading') : t('moderation.uploads.more')}
        </Button>
      )}

      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t(`moderation.reasonDialog.${action}.title`)}
        description={t(`moderation.reasonDialog.${action}.description`)}
        submitLabel={t(`moderation.reasonDialog.${action}.submit`)}
        submittingLabel={t(`moderation.reasonDialog.${action}.submitting`)}
        destructive={action === 'delete'}
        isPending={moderateMutation.isPending}
        error={moderateMutation.isError ? translateError(t, moderateMutation.error) : null}
        onSubmit={moderate}
        onClose={closeDialog}
      />
    </div>
  );
}
