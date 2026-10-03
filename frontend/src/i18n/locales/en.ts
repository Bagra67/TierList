import type { Translation } from './fr';

export const en: Translation = {
  common: {
    loading: 'Loading…',
    backendUnreachable: 'Cannot reach the backend: is it running?',
    language: 'Language',
    theme: 'Theme',
  },
  theme: {
    system: 'System',
    light: 'Light',
    dark: 'Dark',
  },
  auth: {
    email: 'Email',
    password: 'Password',
    displayName: 'Display name',
    continueWithGoogle: 'Continue with Google',
    signedInAs: 'Signed in as {{name}}',
    logout: 'Sign out',
    login: {
      title: 'Sign in',
      submit: 'Sign in',
      submitting: 'Signing in…',
      noAccount: 'No account yet?',
      registerLink: 'Create an account',
    },
    register: {
      title: 'Create an account',
      submit: 'Create my account',
      submitting: 'Creating…',
      hasAccount: 'Already have an account?',
      loginLink: 'Sign in',
    },
  },
  account: {
    delete: {
      open: 'Delete my account',
      title: 'Delete my account',
      warning: 'This cannot be undone: your account and all its data will be erased.',
      googleLinked: 'Your account is linked to Google: nothing to enter.',
      signInAgainWithGoogle: 'Sign in again with Google',
      cancel: 'Cancel',
      submit: 'Delete permanently',
      submitting: 'Deleting…',
    },
  },
  errors: {
    unknown: 'Something went wrong, please try again.',
    api: {
      internal_error: 'Internal server error, please try again.',
      validation_error: 'Some fields are invalid.',
      http_error: 'The request failed.',
      database_unavailable: 'Database unavailable.',
      not_authenticated: 'Authentication required.',
      email_already_registered: 'This email is already registered',
      invalid_credentials: 'Incorrect email or password',
      session_expired: 'Session expired, please sign in again.',
      incorrect_password: 'Incorrect password',
      reauthentication_required: 'Sign in again with Google to confirm the deletion',
    },
    field: {
      invalid: 'Invalid value.',
      missing: 'This field is required.',
      string_too_short: 'At least {{min_length}} characters.',
      string_too_long: 'At most {{max_length}} characters.',
      value_error: 'Invalid value.',
      password_too_short: 'The password must be at least {{min_length}} characters long',
    },
    google: {
      google_cancelled: 'Google sign-in cancelled.',
      google_email_not_verified:
        'Your Google address is not verified: it cannot be used to sign in.',
      google_unavailable: 'Google sign-in is not available at the moment.',
      google_failed: 'Google sign-in failed, please try again.',
    },
  },
};
