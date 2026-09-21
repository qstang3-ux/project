import { BarChartOutlined, DownloadOutlined, LineChartOutlined, PieChartOutlined } from '@ant-design/icons';
import { Alert, Button, Statistic, Tooltip } from 'antd';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { DataZoomComponent, GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { ChartSpec, ResultSet } from '../../../api/types';
import { chartPngFilename } from './chartExport';
import { buildChartOption } from './chartOption';
import { buildChartViewOptions, type SwitchableChartType } from './chartViewOptions';

echarts.use([BarChart, LineChart, PieChart, DataZoomComponent, GridComponent, LegendComponent, TitleComponent, TooltipComponent, CanvasRenderer]);

interface ResultChartProps {
  chart: ChartSpec;
  result: ResultSet;
  highlightedRowIndex?: number | null;
  onHighlightRow?: (index: number | null) => void;
}

export function ResultChart({ chart, result, highlightedRowIndex = null, onHighlightRow }: ResultChartProps) {
  const chartRef = useRef<ReactEChartsCore>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const views = useMemo(() => buildChartViewOptions(chart, result), [chart, result]);
  const preferredType = chart.type === 'bar' || chart.type === 'line' || chart.type === 'pie' ? chart.type : views.find((view) => view.enabled)?.type ?? 'bar';
  const [activeType, setActiveType] = useState<SwitchableChartType>(preferredType);
  useEffect(() => setActiveType(preferredType), [preferredType, chart.title, chart.xField, chart.nameField]);
  const activeView = views.find((view) => view.type === activeType && view.enabled) ?? views.find((view) => view.enabled);
  const activeChart = activeView?.chart ?? chart;
  useEffect(() => {
    const instance = chartRef.current?.getEchartsInstance();
    if (!instance) return;
    instance.dispatchAction({ type: 'downplay', seriesIndex: 'all' });
    if (highlightedRowIndex === null) {
      instance.dispatchAction({ type: 'hideTip' });
      return;
    }
    instance.dispatchAction({ type: 'highlight', dataIndex: highlightedRowIndex });
    instance.dispatchAction({ type: 'showTip', dataIndex: highlightedRowIndex, seriesIndex: 0 });
  }, [activeChart.type, highlightedRowIndex]);
  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === 'undefined') return;
    const resizeChart = () => {
      const instance = chartRef.current?.getEchartsInstance();
      if (instance && container.clientWidth > 0) instance.resize({ width: container.clientWidth });
    };
    const observer = new ResizeObserver(resizeChart);
    observer.observe(container);
    resizeChart();
    return () => observer.disconnect();
  }, [activeChart.type]);
  if (chart.type === 'none' || result.rowCount === 0) return null;
  if (chart.type === 'metric') {
    const field = chart.valueField ?? result.columns.find((column) => column.dataType === 'decimal' || column.dataType === 'integer')?.key;
    const value = field ? result.rows[0]?.[field] : undefined;
    return <section className="metric-panel"><Statistic title={chart.title ?? '核心指标'} value={typeof value === 'number' || typeof value === 'string' ? value : '--'} suffix={chart.unit ?? undefined} /></section>;
  }

  const option = buildChartOption(activeChart, result);
  if (!option) return <Alert type="warning" showIcon message="图表配置不可用" description="已保留结果表格，可继续查看数据。" />;
  const exportPng = () => {
    const url = chartRef.current?.getEchartsInstance().getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
    if (!url) return;
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = chartPngFilename(activeChart.title);
    anchor.click();
  };
  return <section className="chart-section">
    <div className="chart-view-heading">
      <span>当前以{chartTypeLabel(activeChart.type)}展示，切换视图不会重新查询</span>
      <div className="chart-section-toolbar">
        <div className="chart-view-switch" role="group" aria-label="切换图表类型">
          {views.map((view) => <Tooltip key={view.type} title={view.enabled ? chartTypeLabel(view.type) : view.reason}>
            <span><Button type={activeChart.type === view.type ? 'primary' : 'text'} size="small" disabled={!view.enabled} icon={chartTypeIcon(view.type)} aria-label={`切换为${chartTypeLabel(view.type)}`} aria-pressed={activeChart.type === view.type} onClick={() => setActiveType(view.type)} /></span>
          </Tooltip>)}
        </div>
        <Tooltip title="导出图表 PNG"><Button type="text" size="small" icon={<DownloadOutlined />} aria-label="导出图表 PNG" onClick={exportPng} /></Tooltip>
      </div>
    </div>
    <div className="chart-canvas" ref={containerRef}>
      <ReactEChartsCore
        ref={chartRef}
        echarts={echarts}
        option={option}
        style={{ width: '100%', height: 340 }}
        notMerge
        lazyUpdate
        onEvents={{
          mouseover: (params: { dataIndex?: number }) => onHighlightRow?.(params.dataIndex ?? null),
          mouseout: () => onHighlightRow?.(null),
        }}
      />
    </div>
  </section>;
}

function chartTypeLabel(type: ChartSpec['type']): string {
  return { bar: '柱状图', line: '折线图', pie: '饼图', metric: '指标卡', none: '表格' }[type];
}

function chartTypeIcon(type: SwitchableChartType) {
  return { bar: <BarChartOutlined />, line: <LineChartOutlined />, pie: <PieChartOutlined /> }[type];
}
