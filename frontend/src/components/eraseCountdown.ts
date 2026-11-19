import type { TFunction } from 'i18next';

import { DELETED_TEMPLATE_URGENT_DAYS } from '../constants/moderation';

const DAY_MS: number = 24 * 60 * 60 * 1000;

export function daysUntilErase(eraseAt: string, now: Date = new Date()): number {
  return Math.max(0, Math.ceil((new Date(eraseAt).getTime() - now.getTime()) / DAY_MS));
}

export function isEraseUrgent(eraseAt: string): boolean {
  return daysUntilErase(eraseAt) <= DELETED_TEMPLATE_URGENT_DAYS;
}

export function eraseCountdown(t: TFunction, eraseAt: string): string {
  const days: number = daysUntilErase(eraseAt);
  return days === 0
    ? t('moderation.deletedTemplates.eraseTonight')
    : t('moderation.deletedTemplates.eraseIn', { count: days });
}
