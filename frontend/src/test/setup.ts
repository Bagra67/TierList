import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Sans `globals: true`, Testing Library ne démonte pas les composants automatiquement entre deux tests
afterEach(() => {
  cleanup();
});

// jsdom gère l'attribut open de <dialog> mais pas showModal() ni close() : comportement minimal.
// Le piège du focus et la touche Échap, assurés par le navigateur, ne sont donc pas testables ici.
HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
  this.open = true;
};
HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
  this.open = false;
  this.dispatchEvent(new Event('close'));
};
