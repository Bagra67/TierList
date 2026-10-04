import type { Location } from 'react-router';

import { ROUTES } from '../constants/routes';

// État de navigation vers /login : la page privée demandée, pour y revenir après la connexion
interface SignInRedirectState {
  from?: string;
}

export function signInRedirectState(location: Location): SignInRedirectState {
  // Chemin complet : la query string (ex. ?confirm=…) doit survivre à la connexion
  return { from: `${location.pathname}${location.search}${location.hash}` };
}

export function pathAfterSignIn(location: Location): string {
  return (location.state as SignInRedirectState | null)?.from ?? ROUTES.HOME;
}
