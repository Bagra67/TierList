import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useCurrentUser } from '../api/auth';
import { EmailVerificationBanner } from '../components/EmailVerificationBanner';
import { ErrorMessage } from '../components/ErrorMessage';
import { HomeBoard } from '../components/home/HomeBoard';
import { HomeSteps } from '../components/home/HomeSteps';
import { RecentGames } from '../components/home/RecentGames';
import { RecentTemplates } from '../components/home/RecentTemplates';
import { JoinRoomForm } from '../components/JoinRoomForm';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';
import { Button } from '../components/ui/button';
import { textLinkClassName } from '../components/ui/text-link';
import { ROUTES } from '../constants/routes';

// Page d'accueil, publique : le visiteur y voit ce qu'est une partie, peut rejoindre une salle
// avec son code (en invité) ou créer un compte ; le joueur connecté y rejoint une salle, ou en
// ouvre une avec un de ses modèles récents, et retrouve ses dernières parties
export function HomePage() {
  const { data: user, isPending, isError } = useCurrentUser();
  const { t } = useTranslation();

  if (isPending) {
    return (
      <PageContainer width="app">
        <LoadingSkeleton shape="list" />
      </PageContainer>
    );
  }
  if (isError) {
    return (
      <PageContainer width="app">
        <ErrorMessage>{t('common.backendUnreachable')}</ErrorMessage>
      </PageContainer>
    );
  }

  return (
    <PageContainer width="app" className="flex flex-col gap-14">
      {user !== null && <EmailVerificationBanner user={user} />}
      <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:gap-16">
        <div className="flex flex-col items-start gap-6">
          <h1 className="text-5xl leading-[0.95] font-black tracking-tight text-balance font-stretch-125% sm:text-6xl">
            {user === null
              ? t('home.visitor.title')
              : t('home.signedIn.title', { name: user.display_name })}
          </h1>
          <p className="max-w-xl text-lg text-muted-foreground">
            {user === null ? t('home.visitor.intro') : t('home.signedIn.intro')}
          </p>
          <JoinRoomForm className="max-w-md" />
          {user === null && (
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
              <Button asChild size="lg">
                <Link to={ROUTES.REGISTER}>{t('home.visitor.register')}</Link>
              </Button>
              <Link to={ROUTES.LOGIN} className={textLinkClassName}>
                {t('home.visitor.signIn')}
              </Link>
            </div>
          )}
        </div>
        <HomeBoard />
      </section>
      {user === null ? (
        <HomeSteps />
      ) : (
        <div className="grid gap-10 md:grid-cols-2">
          <RecentTemplates />
          <RecentGames />
        </div>
      )}
    </PageContainer>
  );
}
