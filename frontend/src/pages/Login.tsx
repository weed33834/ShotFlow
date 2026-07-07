// 登录页
import { App, Button, Card, Form, Input, Typography } from "antd";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function Login() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const [form] = Form.useForm();

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const onFinish = async (values: { username: string; password: string }) => {
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    } catch (e) {
      message.error((e as Error & { friendlyMessage?: string }).friendlyMessage || (e as Error).message || "登录失败");
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0a1929 0%, #1a2a4a 100%)",
      }}
    >
      <Card style={{ width: 380, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}>
        <Typography.Title level={3} style={{ textAlign: "center", marginBottom: 8 }}>
          ShotFlow
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: "center", marginBottom: 24 }}>
          AIGC 视频工业化流水线管理后台
        </Typography.Paragraph>
        <Form form={form} onFinish={onFinish} layout="vertical" size="large">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input placeholder="请输入用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="请输入密码" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form>
        <Typography.Paragraph style={{ textAlign: "center", marginTop: 16, fontSize: 12, color: "#999" }}>
          首次部署请联系管理员获取初始凭据
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
