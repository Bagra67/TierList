import { type UseMutationResult, useMutation } from '@tanstack/react-query';

import { apiClient, throwIfError } from './client';
import type { components } from './schema';

export type ReportReason = components['schemas']['ReportReason'];
export type ReportTargetKind = components['schemas']['ReportTargetKind'];

export interface ContentReport {
  targetKind: ReportTargetKind;
  targetId: string;
  reason: ReportReason;
  details: string;
}

export function useCreateReport(): UseMutationResult<void, Error, ContentReport> {
  return useMutation({
    mutationFn: async ({ targetKind, targetId, reason, details }: ContentReport): Promise<void> => {
      throwIfError(
        await apiClient.POST('/reports', {
          body: { target_kind: targetKind, target_id: targetId, reason, details },
        }),
      );
    },
  });
}
