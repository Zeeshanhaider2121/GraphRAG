import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import HomePage from "../pages/HomePage";
import ChatPage from "../pages/ChatPage";
import UploadPage from "../pages/UploadPage";
import DocumentsPage from "../pages/DocumentsPage";
import SettingsPage from "../pages/SettingsPage";
import LoginPage from "../pages/LoginPage";
import SignupPage from "../pages/SignupPage";

function NotFoundPage() {
  return (
    <section className="mx-auto flex max-w-3xl flex-col items-start gap-5 px-4 py-20 sm:px-6 lg:px-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">404</p>
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">Page not found</h1>
      <p className="max-w-lg text-muted">
        This page does not exist in the current app routes. Use navigation or return to the
        homepage.
      </p>
      <Link
        to="/"
        className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-5 text-sm font-semibold text-white"
      >
        Go to Home
      </Link>
    </section>
  );
}

function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
