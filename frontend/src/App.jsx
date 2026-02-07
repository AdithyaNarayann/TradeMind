import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { SessionProvider } from './context/SessionContext';
import { I18nProvider } from './context/I18nContext';
import LanguageModal from './components/LanguageModal';
import TranslationLoadingOverlay from './components/TranslationLoadingOverlay';
import Landing from './pages/Landing';
import ReporterHome from './pages/ReporterHome';
import Report from './pages/Report';
import SilentReport from './pages/SilentReport';
import WalletDashboard from './pages/WalletDashboard';
import Authority from './pages/Authority';
import JuryDashboard from './pages/JuryDashboard';
import ReputationPage from './pages/ReputationPage';

function App() {
  return (
    <I18nProvider>
      <BrowserRouter>
      <SessionProvider>
          <LanguageModal />
        <TranslationLoadingOverlay />
        <Routes>
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
          </Routes>
      </SessionProvider>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;

