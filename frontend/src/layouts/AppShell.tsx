import { useMemo, useState } from 'react';
import { BarChartOutlined, FileSearchOutlined, MenuFoldOutlined, MenuUnfoldOutlined, RobotOutlined, SafetyCertificateOutlined, SettingOutlined } from '@ant-design/icons';
import { Avatar, Button, Grid, Layout, Menu, Tooltip } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const STORAGE_KEY = 'management-star-nav-collapsed';

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const [collapsedPreference, setCollapsedPreference] = useState<boolean | undefined>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === null ? undefined : stored === 'true';
  });
  const compactViewport = screens.xl !== true;
  const collapsed = compactViewport || collapsedPreference === true;
  const items = useMemo(() => [
    { key: '/qa', icon: <RobotOutlined />, label: '智能问数' },
    { key: '/qa/logs', icon: <FileSearchOutlined />, label: '问答日志' },
    { key: '/settings/application', icon: <SettingOutlined />, label: '系统设置' },
    { key: '/feedback', icon: <BarChartOutlined />, label: '回复校对' },
  ], []);

  const toggle = () => {
    const nextValue = !collapsed;
    localStorage.setItem(STORAGE_KEY, String(nextValue));
    setCollapsedPreference(nextValue);
  };

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div className="brand">
          <span className="brand-mark"><BarChartOutlined /></span>
          <span className="brand-copy"><strong>经管之星</strong><small>经营数据智能分析</small></span>
        </div>
        <Tooltip title="管理员">
          <Avatar className="header-avatar" size={32} aria-label="当前用户：管理员">管</Avatar>
        </Tooltip>
      </Header>
      <Layout>
        <Sider width={224} collapsedWidth={60} collapsed={collapsed} className="app-sider">
          {!collapsed ? <div className="nav-caption">工作区</div> : null}
          <Menu mode="inline" selectedKeys={[location.pathname.startsWith('/settings/') ? '/settings/application' : location.pathname]} items={items} onClick={({ key }) => { void navigate(key); }} />
          {!collapsed ? <div className="nav-assurance"><SafetyCertificateOutlined /><span><strong>只读分析模式</strong><small>SQL 经安全规则校验</small></span></div> : null}
          {!compactViewport ? (
            <Tooltip title={collapsed ? '展开导航' : '收起导航'} placement="right">
              <Button className="sider-toggle" type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={toggle} aria-label={collapsed ? '展开导航' : '收起导航'} />
            </Tooltip>
          ) : null}
        </Sider>
        <Content className="app-content"><Outlet /></Content>
      </Layout>
    </Layout>
  );
}
