import * as Sentry from '@sentry/react';

import { type ClientConfig, getClientConfig } from '../api/clientConfig';
import {
  SENTRY_BREADCRUMB_URL_KEYS,
  SENTRY_CONSOLE_INTEGRATION_NAME,
} from '../constants/monitoring';

export type SentryIntegration = ReturnType<typeof Sentry.getDefaultIntegrations>[number];

const NO_PERSONAL_DATA: Sentry.BrowserOptions['dataCollection'] = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
};

function withoutFragment(url: string): string {
  const fragmentStart: number = url.indexOf('#');
  return fragmentStart === -1 ? url : url.slice(0, fragmentStart);
}

export function removeUrlFragment(event: Sentry.ErrorEvent): Sentry.ErrorEvent {
  if (event.request?.url) {
    event.request.url = withoutFragment(event.request.url);
  }
  return event;
}

export function removeBreadcrumbUrlFragments(breadcrumb: Sentry.Breadcrumb): Sentry.Breadcrumb {
  const data: Record<string, unknown> | undefined = breadcrumb.data;
  if (data === undefined) {
    return breadcrumb;
  }
  for (const key of SENTRY_BREADCRUMB_URL_KEYS) {
    const value: unknown = data[key];
    if (typeof value === 'string') {
      data[key] = withoutFragment(value);
    }
  }
  return breadcrumb;
}

export function withoutConsoleBreadcrumbs(
  defaultIntegrations: SentryIntegration[],
): SentryIntegration[] {
  return defaultIntegrations.filter(
    (integration: SentryIntegration) => integration.name !== SENTRY_CONSOLE_INTEGRATION_NAME,
  );
}

export function buildSentryOptions(config: ClientConfig): Sentry.BrowserOptions | null {
  if (!config.sentry_dsn) {
    return null;
  }
  return {
    dsn: config.sentry_dsn,
    environment: config.environment,
    release: config.release,
    dataCollection: NO_PERSONAL_DATA,
    integrations: withoutConsoleBreadcrumbs,
    beforeSend: removeUrlFragment,
    beforeBreadcrumb: removeBreadcrumbUrlFragments,
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
