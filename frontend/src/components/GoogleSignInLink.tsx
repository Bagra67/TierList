import { googleSignInUrl } from '../api/auth';

export function GoogleSignInLink() {
  return <a href={googleSignInUrl()}>Continuer avec Google</a>;
}
