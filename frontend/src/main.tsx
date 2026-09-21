import '@ant-design/v5-patch-for-react-19';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { enableMocking } from './mocks/enableMocking';
import { App } from './App';
import './styles/global.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 20_000, retry: 1, refetchOnWindowFocus: false },
    mutations: { retry: 0 },
  },
});

await enableMocking();

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Root element is missing.');

createRoot(rootElement).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#2F54EB',
          colorPrimaryHover: '#4167E8',
          colorPrimaryActive: '#2446B8',
          colorSuccess: '#16A394',
          colorWarning: '#D97706',
          colorError: '#D9367E',
          colorText: '#374151',
          colorTextHeading: '#111827',
          colorBorder: '#E5E7EB',
          borderRadius: 8,
          controlHeight: 44,
          fontSize: 16,
          fontFamily: "Inter, 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif",
        },
        components: {
          Layout: { bodyBg: '#F4F6FA', siderBg: '#FFFFFF', headerBg: '#FFFFFF' },
          Card: { borderRadiusLG: 8 },
          Modal: { borderRadiusLG: 8 },
          Button: {
            controlHeight: 40,
            controlHeightSM: 32,
            borderRadius: 6,
            borderRadiusSM: 6,
            paddingInline: 16,
            paddingInlineSM: 10,
            contentFontSize: 14,
            contentFontSizeSM: 13,
            fontWeight: 600,
            primaryShadow: 'none',
            defaultShadow: 'none',
            dangerShadow: 'none',
          },
        },
      }}
    >
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
);
