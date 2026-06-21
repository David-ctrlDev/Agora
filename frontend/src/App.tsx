import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import AreasPage from "./pages/AreasPage";
import LoginPage from "./pages/LoginPage";
import PlaceholderPage from "./pages/PlaceholderPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/areas" replace />} />
          <Route path="/areas" element={<AreasPage />} />
          <Route path="/proyectos" element={<PlaceholderPage title="Proyectos" />} />
          <Route path="/tareas" element={<PlaceholderPage title="Tareas" />} />
          <Route path="*" element={<Navigate to="/areas" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
