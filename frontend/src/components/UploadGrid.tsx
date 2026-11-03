import { type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  type ImageModerationAction,
  type RecentUpload,
  type RecentUploadsFilters,
  useModerateImage,
  useRecentUploads,
} from '../api/moderation';
import { translateError } from '../errors/apiError';
import { EmptyState } from './EmptyState';
import { ErrorMessage } from './ErrorMessage';
import { LoadingSkeleton } from './LoadingSkeleton';
import { ModerationReasonDialog } from './ModerationReasonDialog';
import { UploadCard } from './UploadCard';
import { Button } from './ui/button';

interface UploadGridProps {
  filters: RecentUploadsFilters;
  emptyMessage: string;
}

interface PendingAction {
  upload: RecentUpload;
  action: ImageModerationAction;
}

export function UploadGrid({ filters, emptyMessage }: UploadGridProps) {
  const { t } = useTranslation();
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useRecentUploads(filters);
  const uploads: RecentUpload[] = data?.pages.flatMap((page) => page.images) ?? [];

  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const moderateMutation = useModerateImage();

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
      return false;
    }
    return true;
  }

  function closeDialog() {
    moderateMutation.reset();
    setPending(null);
  }

  const action: ImageModerationAction = pending?.action ?? 'hide';

  return (
    <>
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && uploads.length === 0 && <EmptyState message={emptyMessage} />}
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
    </>
  );
}
