import * as Sentry from '@sentry/react';

const FAKE_DSN: string = 'https://public-key@sentry.example.invalid/1';

export interface CapturedSentryEvents {
  events: Sentry.ErrorEvent[];
  stop: () => Promise<void>;
}

export function captureSentryEvents(): CapturedSentryEvents {
  const events: Sentry.ErrorEvent[] = [];
  Sentry.init({
    dsn: FAKE_DSN,
    defaultIntegrations: false,
    beforeSend: (event: Sentry.ErrorEvent) => {
      events.push(event);
      return null;
    },
  });
  return {
    events,
    stop: async () => {
      await Sentry.close();
    },
  };
}
