import { Route, Routes } from 'react-router';

import { RedirectIfSignedIn } from './auth/RedirectIfSignedIn';
import { RequireAuth } from './auth/RequireAuth';
import { Layout } from './components/Layout';
import { ROUTES } from './constants/routes';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { HistoryPage } from './pages/HistoryPage';
import { HomePage } from './pages/HomePage';
import { LegalNoticePage } from './pages/LegalNoticePage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { PrivacyPolicyPage } from './pages/PrivacyPolicyPage';
import { RegisterPage } from './pages/RegisterPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { ResultsPage } from './pages/ResultsPage';
import { RoomPage } from './pages/RoomPage';
import { TemplateEditorPage } from './pages/TemplateEditorPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { TermsPage } from './pages/TermsPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route element={<RedirectIfSignedIn />}>
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
        </Route>
        <Route path={ROUTES.VERIFY_EMAIL} element={<VerifyEmailPage />} />
        <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
        <Route path={ROUTES.RESET_PASSWORD} element={<ResetPasswordPage />} />
        {/* Publique : une vitrine pour le visiteur, son accueil pour le joueur connecté */}
        <Route path={ROUTES.HOME} element={<HomePage />} />
        <Route element={<RequireAuth />}>
          <Route path={ROUTES.TEMPLATES} element={<TemplatesPage />} />
          <Route path={ROUTES.TEMPLATE_EDITOR} element={<TemplateEditorPage />} />
          <Route path={ROUTES.HISTORY} element={<HistoryPage />} />
        </Route>
        {/* Ouverte aussi sans compte : le visiteur y entre en invité (RoomPage) */}
        <Route path={ROUTES.ROOM} element={<RoomPage />} />
        {/* Ouverte sans compte : le lien suffit à lire les résultats (US-5.3) */}
        <Route path={ROUTES.RESULTS} element={<ResultsPage />} />
        <Route path={ROUTES.PRIVACY} element={<PrivacyPolicyPage />} />
        <Route path={ROUTES.TERMS} element={<TermsPage />} />
        <Route path={ROUTES.LEGAL_NOTICE} element={<LegalNoticePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
