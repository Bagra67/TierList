import '@testing-library/jest-dom/vitest';

import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import i18n from '../i18n';
import { FakeWebSocket } from './fakeWebSocket';
import { installMatchMedia, resetSystemTheme } from './matchMedia';

installMatchMedia();

// Attente maximale des findBy… et waitFor (1 s par défaut) : une machine chargée, comme un runner
// de CI, peut dépasser 1 s alors que la page se comporte bien. Un test qui réussit n'attend pas
// plus longtemps : il repart dès que l'élément apparaît. Reste sous la limite d'un test de
// Vitest (5 s), pour qu'un échec montre l'élément introuvable plutôt qu'un dépassement de délai.
configure({ asyncUtilTimeout: 3000 });

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
