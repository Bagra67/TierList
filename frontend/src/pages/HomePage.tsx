import { useNavigate } from 'react-router';

import { useCurrentUser, useLogout } from '../api/auth';
import { useHello } from '../api/hello';

export function HomePage() {
  const { data: hello, isPending, isError } = useHello();
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();
  const navigate = useNavigate();

  async function handleLogout() {
    await logoutMutation.mutateAsync().catch(() => undefined);
    await navigate('/login', { replace: true });
  }

  return (
    <main>
      {user && (
        <p>
          Connecté en tant que {user.display_name}{' '}
          <button type="button" onClick={handleLogout} disabled={logoutMutation.isPending}>
            Se déconnecter
          </button>
        </p>
      )}
      {isPending && <p>Chargement…</p>}
      {isError && <p role="alert">Impossible de joindre le backend : est-il lancé ?</p>}
      {hello && <h1>{hello.message}</h1>}
    </main>
  );
}
