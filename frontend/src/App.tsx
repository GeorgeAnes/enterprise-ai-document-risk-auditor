import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuditProvider } from "./context/AuditContext";
import RiskCommandShell from "./components/RiskCommandShell";
import ScanScreen from "./screens/ScanScreen";
import ThreatOverviewScreen from "./screens/ThreatOverviewScreen";
import FindingDeepDiveScreen from "./screens/FindingDeepDiveScreen";

function App() {
  return (
    <BrowserRouter>
      <AuditProvider>
        <RiskCommandShell>
          <Routes>
            <Route path="/" element={<Navigate to="/scan" replace />} />
            <Route path="/scan" element={<ScanScreen />} />
            <Route path="/overview" element={<ThreatOverviewScreen />} />
            <Route path="/findings/:claimId" element={<FindingDeepDiveScreen />} />
            <Route path="*" element={<Navigate to="/scan" replace />} />
          </Routes>
        </RiskCommandShell>
      </AuditProvider>
    </BrowserRouter>
  );
}

export default App;
