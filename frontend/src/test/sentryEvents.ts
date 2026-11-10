import * as Sentry from '@sentry/react';
import { onTestFinished } from 'vitest';

export const FAKE_DSN: string = 'https://public-key@sentry.example.invalid/1';

export function captureSentryEvents(): Sentry.ErrorEvent[] {
  const events: Sentry.ErrorEvent[] = [];
  Sentry.init({
    dsn: FAKE_DSN,
    defaultIntegrations: false,
    beforeSend: (event: Sentry.ErrorEvent) => {
      events.push(event);
      return null;
    },
  });
  onTestFinished(async () => {
    await Sentry.close();
  });
  return events;
}
