import { Navigate, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/common/ErrorBoundary";
import AppLayout from "./components/layout/AppLayout";
import Controls from "./pages/Controls";
import Dashboard from "./pages/Dashboard";
import Help from "./pages/Help";
import MapPage from "./pages/Map";
import Settings from "./pages/Settings";
import Status from "./pages/Status";
import Tools from "./pages/Tools";

export default function App() {
  return (
    <ErrorBoundary>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/status" element={<Status />} />
          <Route path="/controls" element={<Controls />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/help" element={<Help />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppLayout>
    </ErrorBoundary>
  );
}
