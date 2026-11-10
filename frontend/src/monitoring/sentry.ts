import * as Sentry from '@sentry/react';

import { type ClientConfig, getClientConfig } from '../api/clientConfig';

const NO_PERSONAL_DATA: Sentry.BrowserOptions['dataCollection'] = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
};

export function buildSentryOptions(config: ClientConfig): Sentry.BrowserOptions | null {
  if (!config.sentry_dsn) {
    return null;
  }
  return {
    dsn: config.sentry_dsn,
    environment: config.environment,
    release: config.release,
    dataCollection: NO_PERSONAL_DATA,
  };
}

export async function initMonitoring(): Promise<boolean> {
  const config: ClientConfig = await getClientConfig();
  const options: Sentry.BrowserOptions | null = buildSentryOptions(config);
  if (options === null) {
    return false;
  }
  Sentry.init(options);
  return true;
}

export function reportError(error: unknown, componentStack?: string): void {
  Sentry.captureException(error, componentStack ? { contexts: { react: { componentStack } } } : {});
}
