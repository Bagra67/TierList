import * as Sentry from '@sentry/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ClientConfig } from '../api/clientConfig';
import { captureSentryEvents, FAKE_DSN } from '../test/sentryEvents';
import { stubBackend } from '../test/stubBackend';
import {
  buildSentryOptions,
  initMonitoring,
  removeBreadcrumbUrlFragments,
  removeUrlFragment,
  reportError,
  type SentryIntegration,
  withoutConsoleBreadcrumbs,
} from './sentry';

const disabledConfig: ClientConfig = { sentry_dsn: null, environment: 'local', release: 'dev' };

describe('buildSentryOptions', () => {
  it('starts nothing without a DSN', () => {
    expect(buildSentryOptions(disabledConfig)).toBeNull();
  });

  it('sends the environment and the release, without any personal data', () => {
    const options: Sentry.BrowserOptions | null = buildSentryOptions({
      sentry_dsn: FAKE_DSN,
      environment: 'production',
      release: 'v1.2.3',
    });

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
      beforeSend: removeUrlFragment,
      beforeBreadcrumb: removeBreadcrumbUrlFragments,
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

describe('URL fragments', () => {
  it('removes the guest token of the fragment from the event URL', () => {
    const event: Sentry.ErrorEvent = {
      type: undefined,
      request: { url: 'https://tierlist.test/r/K7P2QX#guest=s3cr3t' },
    };

    expect(removeUrlFragment(event).request?.url).toBe('https://tierlist.test/r/K7P2QX');
  });

  it('removes the fragment from the navigation and request breadcrumbs', () => {
    const breadcrumb: Sentry.Breadcrumb = {
      category: 'navigation',
      data: { from: '/r/K7P2QX#guest=s3cr3t', to: '/r/K7P2QX', status_code: 500 },
    };

    expect(removeBreadcrumbUrlFragments(breadcrumb).data).toEqual({
      from: '/r/K7P2QX',
      to: '/r/K7P2QX',
      status_code: 500,
    });
  });

  it('leaves a breadcrumb without data unchanged', () => {
    const breadcrumb: Sentry.Breadcrumb = { category: 'ui.click', message: 'button' };

    expect(removeBreadcrumbUrlFragments(breadcrumb)).toEqual({
      category: 'ui.click',
      message: 'button',
    });
  });
});

describe('initMonitoring', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('does not start Sentry when the backend sends no DSN', async () => {
    stubBackend({ 'GET /client-config': () => Response.json(disabledConfig) });

    await expect(initMonitoring()).resolves.toBe(false);
    expect(Sentry.isEnabled()).toBe(false);
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
