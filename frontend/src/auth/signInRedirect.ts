import type { Location } from 'react-router';

import { ROUTES } from '../constants/routes';

interface SignInRedirectState {
  from?: string;
}

export function signInRedirectState(location: Location): SignInRedirectState {
  return { from: `${location.pathname}${location.search}${location.hash}` };
}

export function pathAfterSignIn(location: Location): string {
  return (location.state as SignInRedirectState | null)?.from ?? ROUTES.HOME;
}
