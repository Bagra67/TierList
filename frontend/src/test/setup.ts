import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach } from 'vitest';

import { LANGUAGE_STORAGE_KEY } from '../constants/i18n';
import { DARK_CLASS, THEME_STORAGE_KEY } from '../constants/theme';
import i18n from '../i18n';
import { installMatchMedia, resetSystemTheme } from './matchMedia';

// Avant tout import de src/theme, qui appelle matchMedia dès son chargement
installMatchMedia();

// Les tests vérifient les textes français : chaque test démarre en français, quelle que soit
// la langue de jsdom, et sans choix de langue mémorisé par un test précédent.
beforeEach(async () => {
  await i18n.changeLanguage('fr');
});

// Sans `globals: true`, Testing Library ne démonte pas les composants automatiquement entre deux tests
afterEach(() => {
  cleanup();
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
