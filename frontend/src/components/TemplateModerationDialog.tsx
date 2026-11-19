import { type ReactNode, type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  isDestructiveTemplateAction,
  type TemplateModerationAction,
  useModerateTemplate,
} from '../api/moderation';
import { translateError } from '../errors/apiError';
import { ModerationReasonDialog } from './ModerationReasonDialog';

interface PendingTemplateModeration {
  templateId: string;
  templateName: string;
  action: TemplateModerationAction;
}

export interface TemplateModerationDialog {
  open: (templateId: string, templateName: string, action: TemplateModerationAction) => void;
  dialog: ReactNode;
}

export function useTemplateModerationDialog(
  onModerated?: (action: TemplateModerationAction) => void,
): TemplateModerationDialog {
  const { t } = useTranslation();
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState<PendingTemplateModeration | null>(null);
  const moderateMutation = useModerateTemplate();
  const action: TemplateModerationAction = pending?.action ?? 'hide';

  function open(templateId: string, templateName: string, chosenAction: TemplateModerationAction) {
    setPending({ templateId, templateName, action: chosenAction });
    dialogRef.current?.showModal();
  }

  async function moderate(reason: string): Promise<boolean> {
    if (pending === null) return false;
    try {
      await moderateMutation.mutateAsync({
        templateId: pending.templateId,
        action: pending.action,
        reason,
      });
    } catch {
      return false;
    }
    onModerated?.(pending.action);
    return true;
  }

  const dialog: ReactNode = (
    <ModerationReasonDialog
      dialogRef={dialogRef}
      title={t(`moderation.templateDialog.${action}.title`, { name: pending?.templateName ?? '' })}
      description={t(`moderation.templateDialog.${action}.description`)}
      submitLabel={t(`moderation.templateDialog.${action}.submit`)}
      submittingLabel={t(`moderation.templateDialog.${action}.submitting`)}
      destructive={isDestructiveTemplateAction(action)}
      isPending={moderateMutation.isPending}
      translatedFailureMessage={
        moderateMutation.isError ? translateError(t, moderateMutation.error) : null
      }
      onSubmit={moderate}
      onClose={() => {
        moderateMutation.reset();
        setPending(null);
      }}
    />
  );
  return { open, dialog };
}
