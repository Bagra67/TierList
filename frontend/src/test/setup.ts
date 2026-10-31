import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

import { setAccessToken } from '../api/client';
import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import i18n from '../i18n';
import { FakeWebSocket } from './fakeWebSocket';
import { installMatchMedia, resetSystemTheme } from './matchMedia';

// Avant tout import de src/theme, qui appelle matchMedia dès son chargement
installMatchMedia();

// Les tests vérifient les textes français : chaque test démarre en français, quelle que soit
// la langue de jsdom, et sans choix de langue mémorisé par un test précédent.
beforeEach(async () => {
  await i18n.changeLanguage('fr');
  // Le lobby ouvre le canal temps réel : jamais de vrai WebSocket dans les tests
  FakeWebSocket.instances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
});

// Sans `globals: true`, Testing Library ne démonte pas les composants automatiquement entre deux tests.
// Les fichiers de test ne sont pas isolés (isolate: false, vite.config.ts) : ils partagent les
// modules et jsdom, d'où ce nettoyage commun, qui passe après celui de chaque fichier.
afterEach(async () => {
  cleanup();
  vi.useRealTimers();
  // Laisse finir les réponses déjà reçues (les faux backends répondent tout de suite) avant de
  // vider l'access token : sinon une réponse tardive (refresh) le remettrait pour le test suivant
  await new Promise((resolve) => setTimeout(resolve, 0));
  setAccessToken(null);
  vi.unstubAllGlobals();
  localStorage.removeItem(LANGUAGE_STORAGE_KEY);
  // Chaque test démarre en thème « system », avec un système en clair
  localStorage.removeItem(THEME_STORAGE_KEY);
  document.documentElement.classList.remove(DARK_CLASS);
  resetSystemTheme();
});

// jsdom n'a pas URL.createObjectURL (aperçu local d'une image choisie) : une adresse factice
// suffit, l'image n'est jamais décodée dans les tests
URL.createObjectURL ??= (blob: Blob) => `blob:preview-${blob.size}`;
URL.revokeObjectURL ??= () => undefined;

// jsdom gère l'attribut open de <dialog> mais pas showModal() ni close() : comportement minimal.
// Le piège du focus et la touche Échap, assurés par le navigateur, ne sont donc pas testables ici.
HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
  this.open = true;
};
HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
  this.open = false;
  this.dispatchEvent(new Event('close'));
};
