import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';

import { useCurrentUser, useLogout } from '../api/auth';
import { useHello } from '../api/hello';
import { DeleteAccountDialog } from '../components/DeleteAccountDialog';
import { DELETE_ACCOUNT_STEP } from '../constants/auth';
import { CONFIRM_PARAM, ROUTES } from '../constants/routes';

export function HomePage() {
  const { data: hello, isPending, isError } = useHello();
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  // Retour d'une reconnexion Google demandée pour confirmer la suppression du compte
  const resumeDeletion = searchParams.get(CONFIRM_PARAM) === DELETE_ACCOUNT_STEP;

  useEffect(() => {
    // Une fois le dialogue affiché (donc ouvert), on retire le paramètre : un rechargement
    // de la page ne doit pas le rouvrir.
    if (resumeDeletion && user) {
      setSearchParams({}, { replace: true });
    }
  }, [resumeDeletion, user, setSearchParams]);

  async function handleLogout() {
    await logoutMutation.mutateAsync().catch(() => undefined);
    await navigate(ROUTES.LOGIN, { replace: true });
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
      {user && <DeleteAccountDialog user={user} openOnMount={resumeDeletion} />}
    </main>
  );
}
