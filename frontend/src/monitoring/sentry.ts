import * as Sentry from '@sentry/react';

import { type ClientConfig, getClientConfig } from '../api/clientConfig';
import {
  CLIENT_CONFIG_ELEMENT_ID,
  SENTRY_BREADCRUMB_URL_KEYS,
  SENTRY_CONSOLE_INTEGRATION_NAME,
  SENTRY_FILTERED,
  SENTRY_SECRET_PATH_SEGMENT,
  SENTRY_URL_QUERY_OR_FRAGMENT,
} from '../constants/monitoring';

export type SentryIntegration = ReturnType<typeof Sentry.getDefaultIntegrations>[number];

const NO_PERSONAL_DATA: Sentry.BrowserOptions['dataCollection'] = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
};

export function scrubUrl(url: string): string {
  return url
    .replace(SENTRY_URL_QUERY_OR_FRAGMENT, '')
    .replace(SENTRY_SECRET_PATH_SEGMENT, `$1${SENTRY_FILTERED}`);
}

export function scrubEventUrl(event: Sentry.ErrorEvent): Sentry.ErrorEvent {
  if (event.request?.url) {
    event.request.url = scrubUrl(event.request.url);
  }
  return event;
}

export function scrubBreadcrumbUrls(breadcrumb: Sentry.Breadcrumb): Sentry.Breadcrumb {
  const data: Record<string, unknown> | undefined = breadcrumb.data;
  if (data === undefined) {
    return breadcrumb;
  }
  for (const key of SENTRY_BREADCRUMB_URL_KEYS) {
    const value: unknown = data[key];
    if (typeof value === 'string') {
      data[key] = scrubUrl(value);
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
    beforeSend: scrubEventUrl,
    beforeBreadcrumb: scrubBreadcrumbUrls,
  };
}

function isClientConfig(value: unknown): value is ClientConfig {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const config = value as Record<string, unknown>;
  return (
    (typeof config.sentry_dsn === 'string' || config.sentry_dsn === null) &&
    typeof config.environment === 'string' &&
    typeof config.release === 'string'
  );
}

export function readInjectedClientConfig(): ClientConfig | null {
  const configJson: string | null | undefined =
    document.getElementById(CLIENT_CONFIG_ELEMENT_ID)?.textContent;
  if (!configJson) {
    return null;
  }
  try {
    const config: unknown = JSON.parse(configJson);
    return isClientConfig(config) ? config : null;
  } catch {
    return null;
  }
}

export async function initMonitoring(): Promise<boolean> {
  const config: ClientConfig = readInjectedClientConfig() ?? (await getClientConfig());
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
