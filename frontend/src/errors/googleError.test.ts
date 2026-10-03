import { describe, expect, it } from 'vitest';

import i18n from '../i18n';
import { translateGoogleError } from './googleError';

describe('translateGoogleError', () => {
  it('translates the Google error code, and treats an unknown code as a failure', async () => {
    await i18n.changeLanguage('en');

    expect(translateGoogleError(i18n.t, 'google_cancelled')).toBe('Google sign-in cancelled.');
    expect(translateGoogleError(i18n.t, 'unknown_code')).toBe(
      'Google sign-in failed, please try again.',
    );
  });
});
