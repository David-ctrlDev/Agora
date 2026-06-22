import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import AgentPage from "./pages/AgentPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import AreasPage from "./pages/AreasPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotificationsPage from "./pages/NotificationsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import SecurityPage from "./pages/SecurityPage";
import TasksPage from "./pages/TasksPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/inicio" replace />} />
          <Route path="/inicio" element={<HomePage />} />
          <Route path="/areas" element={<AreasPage />} />
          <Route path="/proyectos" element={<ProjectsPage />} />
          <Route path="/proyectos/:id" element={<ProjectDetailPage />} />
          <Route path="/tareas" element={<TasksPage />} />
          <Route path="/analitica" element={<AnalyticsPage />} />
          <Route path="/agente" element={<AgentPage />} />
          <Route path="/notificaciones" element={<NotificationsPage />} />
          <Route path="/seguridad" element={<SecurityPage />} />
          <Route path="*" element={<Navigate to="/inicio" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
