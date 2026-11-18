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
import { PagedList } from './PagedList';
import { EmptyState } from './EmptyState';
import { ModerationReasonDialog } from './ModerationReasonDialog';
import { UploadCard } from './UploadCard';

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
  const query = useRecentUploads(filters);
  const uploads: RecentUpload[] = query.data?.pages.flatMap((page) => page.images) ?? [];

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
      <PagedList
        query={query}
        itemCount={uploads.length}
        empty={<EmptyState message={emptyMessage} />}
        moreLabel={t('moderation.uploads.more')}
      >
        <ul className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {uploads.map((upload: RecentUpload) => (
            <UploadCard key={upload.id} upload={upload} onAction={openDialog} />
          ))}
        </ul>
      </PagedList>

      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t(`moderation.reasonDialog.${action}.title`)}
        description={t(`moderation.reasonDialog.${action}.description`)}
        submitLabel={t(`moderation.reasonDialog.${action}.submit`)}
        submittingLabel={t(`moderation.reasonDialog.${action}.submitting`)}
        destructive={action === 'delete'}
        isPending={moderateMutation.isPending}
        translatedFailureMessage={
          moderateMutation.isError ? translateError(t, moderateMutation.error) : null
        }
        onSubmit={moderate}
        onClose={closeDialog}
      />
    </>
  );
}
