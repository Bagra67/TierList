import { Navigate, Route, Routes } from 'react-router';

import { RequireAuth } from './auth/RequireAuth';
import { Layout } from './components/Layout';
import { ROUTES } from './constants/routes';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path={ROUTES.LOGIN} element={<LoginPage />} />
        <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
        <Route path={ROUTES.VERIFY_EMAIL} element={<VerifyEmailPage />} />
        <Route element={<RequireAuth />}>
          <Route path={ROUTES.HOME} element={<HomePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
    </Routes>
  );
}
