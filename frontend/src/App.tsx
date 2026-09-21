import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { RouteLoading } from './components/RouteLoading';
import { AppShell } from './layouts/AppShell';

const QuestionPage = lazy(() => import('./pages/QuestionPage').then((module) => ({ default: module.QuestionPage })));
const ApplicationSettingsPage = lazy(() => import('./pages/ApplicationSettingsPage').then((module) => ({ default: module.ApplicationSettingsPage })));
const FeedbackPage = lazy(() => import('./pages/FeedbackPage').then((module) => ({ default: module.FeedbackPage })));
const QaLogsPage = lazy(() => import('./pages/QaLogsPage').then((module) => ({ default: module.QaLogsPage })));

function LazyRoute({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteLoading />}>{children}</Suspense>;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/qa" replace />} />
          <Route path="qa" element={<LazyRoute><QuestionPage /></LazyRoute>} />
          <Route path="settings/application" element={<LazyRoute><ApplicationSettingsPage /></LazyRoute>} />
          <Route path="settings/models" element={<Navigate to="/settings/application" replace />} />
          <Route path="feedback" element={<LazyRoute><FeedbackPage /></LazyRoute>} />
          <Route path="qa/logs" element={<LazyRoute><QaLogsPage /></LazyRoute>} />
          <Route path="*" element={<Navigate to="/qa" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
