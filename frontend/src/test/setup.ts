import '@testing-library/jest-dom/vitest';

import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { alignOnServerClock } from '../api/serverClock';
import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import i18n from '../i18n';
import { FakeWebSocket } from './fakeWebSocket';
import { installMatchMedia, resetSystemTheme } from './matchMedia';

installMatchMedia();

const ASYNC_WAIT_FOR_LOADED_CI_BELOW_VITEST_LIMIT_MS: number = 3000;
configure({ asyncUtilTimeout: ASYNC_WAIT_FOR_LOADED_CI_BELOW_VITEST_LIMIT_MS });

beforeEach(async () => {
  await i18n.changeLanguage('fr');
  FakeWebSocket.instances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
});

function letLateResponsesFinish(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

afterEach(async () => {
  cleanup();
  vi.useRealTimers();
  await letLateResponsesFinish();
  setAccessToken(null);
  alignOnServerClock(new Date().toISOString());
  vi.unstubAllGlobals();
  localStorage.removeItem(LANGUAGE_STORAGE_KEY);
  localStorage.removeItem(THEME_STORAGE_KEY);
  document.documentElement.classList.remove(DARK_CLASS);
  resetSystemTheme();
});

URL.createObjectURL ??= (blob: Blob) => `blob:preview-${blob.size}`;
URL.revokeObjectURL ??= () => undefined;

HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
  this.open = true;
};
HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
  this.open = false;
  this.dispatchEvent(new Event('close'));
};
