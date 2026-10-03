import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router';

import { useCurrentUser, useLogout } from '../api/auth';
import { useHello } from '../api/hello';
import { DeleteAccountDialog } from '../components/DeleteAccountDialog';
import { Button } from '../components/ui/button';
import { DELETE_ACCOUNT_STEP } from '../constants/auth';
import { CONFIRM_PARAM, ROUTES } from '../constants/routes';

export function HomePage() {
  const { data: hello, isPending, isError } = useHello();
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useTranslation();
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
    <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-4 py-10">
      {user && (
        <div className="flex w-full items-center justify-between gap-4 text-sm">
          <p>{t('auth.signedInAs', { name: user.display_name })}</p>
          <Button
            type="button"
            variant="outline"
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
          >
            {t('auth.logout')}
          </Button>
        </div>
      )}
      {isPending && <p className="text-muted-foreground">{t('common.loading')}</p>}
      {isError && (
        <p role="alert" className="text-destructive">
          {t('common.backendUnreachable')}
        </p>
      )}
      {hello && <h1 className="text-2xl font-semibold">{hello.message}</h1>}
      {user && <DeleteAccountDialog user={user} openOnMount={resumeDeletion} />}
    </main>
  );
}
