import { Navigate, Route, Routes } from 'react-router';

import { RedirectIfSignedIn } from './auth/RedirectIfSignedIn';
import { RequireAuth } from './auth/RequireAuth';
import { RequireSuperAdmin } from './auth/RequireSuperAdmin';
import { Layout } from './components/Layout';
import { ModerationLayout } from './components/ModerationLayout';
import { ROUTES } from './constants/routes';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { HistoryPage } from './pages/HistoryPage';
import { HomePage } from './pages/HomePage';
import { LegalNoticePage } from './pages/LegalNoticePage';
import { LoginPage } from './pages/LoginPage';
import { ModerationAccountPage } from './pages/ModerationAccountPage';
import { ModerationAccountsPage } from './pages/ModerationAccountsPage';
import { ModerationLogPage } from './pages/ModerationLogPage';
import { ModerationReportsPage } from './pages/ModerationReportsPage';
import { ModerationTemplatePage } from './pages/ModerationTemplatePage';
import { RecentUploadsPage } from './pages/RecentUploadsPage';
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
        <Route path={ROUTES.HOME} element={<HomePage />} />
        <Route element={<RequireAuth />}>
          <Route path={ROUTES.TEMPLATES} element={<TemplatesPage />} />
          <Route path={ROUTES.TEMPLATE_EDITOR} element={<TemplateEditorPage />} />
          <Route path={ROUTES.HISTORY} element={<HistoryPage />} />
          <Route element={<RequireSuperAdmin />}>
            <Route element={<ModerationLayout />}>
              <Route
                path={ROUTES.MODERATION}
                element={<Navigate to={ROUTES.MODERATION_REPORTS} replace />}
              />
              <Route path={ROUTES.MODERATION_REPORTS} element={<ModerationReportsPage />} />
              <Route path={ROUTES.MODERATION_UPLOADS} element={<RecentUploadsPage />} />
              <Route path={ROUTES.MODERATION_ACCOUNTS} element={<ModerationAccountsPage />} />
              <Route path={ROUTES.MODERATION_ACCOUNT} element={<ModerationAccountPage />} />
              <Route path={ROUTES.MODERATION_TEMPLATE} element={<ModerationTemplatePage />} />
              <Route path={ROUTES.MODERATION_LOG} element={<ModerationLogPage />} />
            </Route>
          </Route>
        </Route>
        <Route path={ROUTES.ROOM} element={<RoomPage />} />
        <Route path={ROUTES.RESULTS} element={<ResultsPage />} />
        <Route path={ROUTES.PRIVACY} element={<PrivacyPolicyPage />} />
        <Route path={ROUTES.TERMS} element={<TermsPage />} />
        <Route path={ROUTES.LEGAL_NOTICE} element={<LegalNoticePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
