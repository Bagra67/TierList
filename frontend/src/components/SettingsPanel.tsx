import { useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useSearchParams } from 'react-router';
import { Settings } from 'lucide-react';

import { useCurrentUser } from '../api/auth';
import { DELETE_ACCOUNT_STEP } from '../constants/auth';
import { CONFIRM_PARAM, ROUTES } from '../constants/routes';
import { DeleteAccountDialog } from './DeleteAccountDialog';
import { LanguageSwitcher } from './LanguageSwitcher';
import { ThemeSwitcher } from './ThemeSwitcher';
import { Button } from './ui/button';
import { textLinkClassName } from './ui/text-link';

// Bouton engrenage de l'en-tête et panneau de paramètres qui glisse depuis la droite : thème et
// langue pour tous, suppression du compte une fois connecté. <dialog> natif ouvert avec
// showModal(), comme ModalDialog : le navigateur piège le focus dedans, le ferme avec Échap et
// rend le focus à l'engrenage.
export function SettingsPanel() {
  const panelRef = useRef<HTMLDialogElement>(null);
  const titleId: string = useId();
  const { data: user } = useCurrentUser();
  const { pathname } = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useTranslation();
  // Retour d'une reconnexion Google demandée pour confirmer la suppression du compte
  const resumeDeletion: boolean = searchParams.get(CONFIRM_PARAM) === DELETE_ACCOUNT_STEP;
  const [deletionResumed, setDeletionResumed] = useState<boolean>(false);

  useEffect(() => {
    // Une autre page s'affiche (ex. /login après la suppression du compte) : le panneau se ferme
    panelRef.current?.close();
  }, [pathname]);

  useEffect(() => {
    const panel: HTMLDialogElement | null = panelRef.current;
    if (!resumeDeletion || !user || panel === null) return;
    // Le panneau s'ouvre d'abord : le dialogue de suppression, qu'il contient, ne peut s'ouvrir
    // que dans un parent affiché. Le paramètre est ensuite retiré, pour qu'un rechargement de la
    // page ne rouvre rien.
    if (!panel.open) panel.showModal();
    setDeletionResumed(true);
    setSearchParams({}, { replace: true });
  }, [resumeDeletion, user, setSearchParams]);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={t('settings.open')}
        onClick={() => panelRef.current?.showModal()}
      >
        <Settings aria-hidden="true" className="size-5" />
      </Button>
      <dialog
        ref={panelRef}
        aria-labelledby={titleId}
        className="my-0 mr-0 ml-auto h-dvh max-h-none w-full max-w-sm bg-card p-6 text-sm text-card-foreground shadow-lg ring-1 ring-foreground/10 backdrop:bg-black/50 motion-safe:transition-transform motion-safe:duration-200 motion-safe:starting:open:translate-x-full"
      >
        <div className="flex items-center justify-between gap-4">
          <h2 id={titleId} className="text-lg font-semibold">
            {t('settings.title')}
          </h2>
          <Button type="button" variant="outline" onClick={() => panelRef.current?.close()}>
            {t('settings.close')}
          </Button>
        </div>
        <section className="mt-6 flex flex-col gap-3">
          <h3 className="font-medium">{t('settings.display')}</h3>
          <ThemeSwitcher />
          <LanguageSwitcher />
        </section>
        {user && (
          <section className="mt-6 flex flex-col items-start gap-3">
            <h3 className="font-medium">{t('settings.account')}</h3>
            <DeleteAccountDialog user={user} openOnMount={deletionResumed} />
          </section>
        )}
        <section className="mt-6 flex flex-col items-start gap-3">
          <h3 className="font-medium">{t('settings.about')}</h3>
          <Link to={ROUTES.PRIVACY} className={textLinkClassName}>
            {t('footer.privacy')}
          </Link>
        </section>
      </dialog>
    </>
  );
}
