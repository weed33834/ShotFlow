// 应用根组件 — 路由 + AuthProvider + QueryClientProvider + ConfigProvider
import { QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, App as AntdApp, Result, Button } from "antd";
import zhCN from "antd/locale/zh_CN";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { queryClient } from "@/lib/queryClient";
import ProtectedRoute from "@/components/ProtectedRoute";
import MainLayout from "@/layouts/MainLayout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Projects from "@/pages/Projects";
import Shots from "@/pages/Shots";
import Keyframes from "@/pages/Keyframes";
import Queue from "@/pages/Queue";
import Workflows from "@/pages/Workflows";
import WorkflowConfigs from "@/pages/WorkflowConfigs";
import Assets from "@/pages/Assets";
import AudioPage from "@/pages/Audio";
import CaseStudies from "@/pages/CaseStudies";
import QA from "@/pages/QA";

const theme = {
  token: {
    colorPrimary: "#1668dc",
    borderRadius: 6,
  },
};

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <AntdApp>
        <ErrorBoundary>
          <AuthProvider>
            <QueryClientProvider client={queryClient}>
              <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                  element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/projects" element={<Projects />} />
                  <Route path="/shots" element={<Shots />} />
                  <Route path="/keyframes" element={<Keyframes />} />
                  <Route path="/queue" element={<Queue />} />
                  <Route path="/workflows" element={<Workflows />} />
                  <Route path="/workflow-configs" element={<WorkflowConfigs />} />
                  <Route path="/assets" element={<Assets />} />
                  <Route path="/audio" element={<AudioPage />} />
                  <Route path="/qa" element={<QA />} />
                  <Route path="/case-studies" element={<CaseStudies />} />
                  <Route
                    path="*"
                    element={
                      <Result
                        status="404"
                        title="404"
                        subTitle="页面不存在"
                        extra={<Link to="/dashboard"><Button type="primary">回首页</Button></Link>}
                      />
                    }
                  />
                </Route>
                </Routes>
              </BrowserRouter>
            </QueryClientProvider>
          </AuthProvider>
        </ErrorBoundary>
      </AntdApp>
    </ConfigProvider>
  );
}
