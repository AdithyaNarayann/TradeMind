import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { I18nProvider } from './context/I18nContext';
import LanguageModal from './components/LanguageModal';
import TranslationLoadingOverlay from './components/TranslationLoadingOverlay';
import Login from './pages/Login';
import Register from './pages/Register';
import Landing from './pages/Landing';
import ReporterHome from './pages/ReporterHome';
import Report from './pages/Report';
import SilentReport from './pages/SilentReport';
import WalletDashboard from './pages/WalletDashboard';
import Authority from './pages/Authority';
import JuryDashboard from './pages/JuryDashboard';
import ReputationPage from './pages/ReputationPage';
import ProductCatalog from './pages/ProductCatalog';
import ApiAccess from './pages/ApiAccess';
import EmailSettings from './pages/EmailSettings';
import Chat from './test-chat/src/Chat';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <I18nProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <SessionProvider>
          <LanguageModal />
          <TranslationLoadingOverlay />
          <Routes>
            {/* Login - Entry Point */}
            <Route path="/login" element={<Login />} />

            {/* Register */}
            <Route path="/register" element={<Register />} />

            {/* Landing */}
            <Route path="/" element={<Landing />} />

            {/* Reporter Routes */}
            <Route path="/reporter" element={<ReporterHome />} />
            <Route path="/reporter/report" element={<Report />} />
            <Route path="/reporter/silent" element={<SilentReport />} />
            <Route path="/r/:sessionId" element={<Report />} />
            <Route path="/report/:sessionId" element={<Report />} />

            {/* Wallet */}
            <Route path="/wallet" element={<WalletDashboard />} />

            {/* Authority */}
            <Route path="/authority" element={<Authority />} />

            {/* Jury */}
            <Route path="/jury" element={<JuryDashboard />} />

            {/* Reputation */}
            <Route path="/reputation" element={<ReputationPage />} />

            {/* Products (requires login) */}
            <Route path="/products" element={<ProtectedRoute><ProductCatalog /></ProtectedRoute>} />

            {/* API Access (requires login) */}
            <Route path="/api-access" element={<ProtectedRoute><ApiAccess /></ProtectedRoute>} />

            {/* Email Settings (requires login) */}
            <Route path="/email-settings" element={<ProtectedRoute><EmailSettings /></ProtectedRoute>} />

            {/* Chat / Negotiation Demo */}
            <Route path="/chat" element={<Chat />} />
          </Routes>
        </SessionProvider>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;

