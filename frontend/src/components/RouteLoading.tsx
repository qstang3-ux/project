import { Spin } from 'antd';

export function RouteLoading() {
  return <div className="async-state" role="status"><Spin size="large" /><span>加载页面...</span></div>;
}
