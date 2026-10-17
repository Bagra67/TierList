import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { useCurrentUser, useLogout } from '../api/auth';
import { ROUTES } from '../constants/routes';
import { Button } from './ui/button';

// « Se déconnecter » dans l'en-tête, accessible depuis toutes les pages une fois connecté
export function LogoutButton() {
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();
  const navigate = useNavigate();
  const { t } = useTranslation();

  if (!user) return null;

  async function handleLogout() {
    // Même si le backend est injoignable, l'interface repasse en mode déconnecté (useLogout)
    await logoutMutation.mutateAsync().catch(() => undefined);
    await navigate(ROUTES.LOGIN, { replace: true });
  }

  return (
    <Button
      type="button"
      variant="outline"
      onClick={handleLogout}
      disabled={logoutMutation.isPending}
    >
      {t('auth.logout')}
    </Button>
  );
}
