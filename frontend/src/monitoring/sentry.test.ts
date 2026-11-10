import * as Sentry from '@sentry/react';
import { afterEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import type { ClientConfig } from '../api/clientConfig';
import { CLIENT_CONFIG_ELEMENT_ID } from '../constants/monitoring';
import { captureSentryEvents, FAKE_DSN } from '../test/sentryEvents';
import { type BackendMock, calledRoutes, stubBackend } from '../test/stubBackend';
import {
  buildSentryOptions,
  initMonitoring,
  readInjectedClientConfig,
  reportError,
  scrubBreadcrumbUrls,
  scrubEventUrl,
  scrubUrl,
  type SentryIntegration,
  withoutConsoleBreadcrumbs,
} from './sentry';

const disabledConfig: ClientConfig = { sentry_dsn: null, environment: 'local', release: 'dev' };
const enabledConfig: ClientConfig = {
  sentry_dsn: FAKE_DSN,
  environment: 'production',
  release: 'v1.2.3',
};

function injectClientConfig(configJson: string): void {
  const element: HTMLScriptElement = document.createElement('script');
  element.type = 'application/json';
  element.id = CLIENT_CONFIG_ELEMENT_ID;
  element.textContent = configJson;
  document.head.append(element);
  onTestFinished(() => element.remove());
}

describe('buildSentryOptions', () => {
  it('starts nothing without a DSN', () => {
    expect(buildSentryOptions(disabledConfig)).toBeNull();
  });

  it('sends the environment and the release, without any personal data', () => {
    const options: Sentry.BrowserOptions | null = buildSentryOptions(enabledConfig);

    expect(options).toMatchObject({
      dsn: FAKE_DSN,
      environment: 'production',
      release: 'v1.2.3',
      dataCollection: {
        userInfo: false,
        cookies: false,
        httpHeaders: false,
        httpBodies: [],
        urlQueryParams: false,
      },
      beforeSend: scrubEventUrl,
      beforeBreadcrumb: scrubBreadcrumbUrls,
    });
    expect(options?.integrations).toBe(withoutConsoleBreadcrumbs);
  });

  it('keeps the default integrations except the console breadcrumbs', () => {
    const integrationNames: string[] = withoutConsoleBreadcrumbs(
      Sentry.getDefaultIntegrations({}),
    ).map((integration: SentryIntegration) => integration.name);

    expect(integrationNames).toContain('Breadcrumbs');
    expect(integrationNames).toContain('GlobalHandlers');
    expect(integrationNames).not.toContain('Console');
  });
});

describe('URL scrubbing', () => {
  it.each([
    ['https://tierlist.test/results/s3cr3t', 'https://tierlist.test/results/[Filtered]'],
    ['https://tierlist.test/r/K7P2QX#guest=s3cr3t', 'https://tierlist.test/r/[Filtered]'],
    [
      'https://tierlist.test/api/rooms/K7P2QX/join?x=1',
      'https://tierlist.test/api/rooms/[Filtered]/join',
    ],
    ['/reset-password?token=s3cr3t', '/reset-password'],
    ['/templates/42', '/templates/42'],
  ])('turns %s into %s', (url: string, scrubbed: string) => {
    expect(scrubUrl(url)).toBe(scrubbed);
  });

  it('scrubs the event URL', () => {
    const event: Sentry.ErrorEvent = {
      type: undefined,
      request: { url: 'https://tierlist.test/r/K7P2QX#guest=s3cr3t' },
    };

    expect(scrubEventUrl(event).request?.url).toBe('https://tierlist.test/r/[Filtered]');
  });

  it('scrubs the navigation and request breadcrumbs', () => {
    const breadcrumb: Sentry.Breadcrumb = {
      category: 'navigation',
      data: {
        from: '/r/K7P2QX#guest=s3cr3t',
        to: '/results/s3cr3t',
        url: 'https://tierlist.test/api/results/s3cr3t',
        status_code: 500,
      },
    };

    expect(scrubBreadcrumbUrls(breadcrumb).data).toEqual({
      from: '/r/[Filtered]',
      to: '/results/[Filtered]',
      url: 'https://tierlist.test/api/results/[Filtered]',
      status_code: 500,
    });
  });

  it('leaves a breadcrumb without data unchanged', () => {
    const breadcrumb: Sentry.Breadcrumb = { category: 'ui.click', message: 'button' };

    expect(scrubBreadcrumbUrls(breadcrumb)).toEqual({
      category: 'ui.click',
      message: 'button',
    });
  });
});

describe('readInjectedClientConfig', () => {
  it('reads the config the backend wrote into the page', () => {
    injectClientConfig(JSON.stringify(enabledConfig));

    expect(readInjectedClientConfig()).toEqual(enabledConfig);
  });

  it.each([
    ['no element', null],
    ['invalid JSON', '{'],
    ['an incomplete config', '{"sentry_dsn": null}'],
  ])('returns null with %s', (_case: string, configJson: string | null) => {
    if (configJson !== null) {
      injectClientConfig(configJson);
    }

    expect(readInjectedClientConfig()).toBeNull();
  });
});

describe('initMonitoring', () => {
  afterEach(async () => {
    vi.unstubAllGlobals();
    await Sentry.close();
  });

  it('does not start Sentry when the backend sends no DSN', async () => {
    stubBackend({ 'GET /client-config': () => Response.json(disabledConfig) });

    await expect(initMonitoring()).resolves.toBe(false);
    expect(Sentry.isEnabled()).toBe(false);
  });

  it('starts Sentry at once from the config written into the page, without a request', async () => {
    const backend: BackendMock = stubBackend({});
    injectClientConfig(JSON.stringify(enabledConfig));

    const started: Promise<boolean> = initMonitoring();

    expect(Sentry.getClient()?.getOptions().dsn).toBe(FAKE_DSN);
    await expect(started).resolves.toBe(true);
    expect(calledRoutes(backend)).toEqual([]);
  });
});

describe('reportError', () => {
  it('does nothing while Sentry is not started', () => {
    expect(() => reportError(new Error('ignored'))).not.toThrow();
  });

  it('sends the error with the React component stack', async () => {
    const events: Sentry.ErrorEvent[] = captureSentryEvents();

    reportError(new Error('render failed'), '\n    at Broken');

    await vi.waitFor(() => expect(events).toHaveLength(1));
    expect(events[0].exception?.values?.[0].value).toBe('render failed');
    expect(events[0].contexts?.react).toEqual({ componentStack: '\n    at Broken' });
  });
});
