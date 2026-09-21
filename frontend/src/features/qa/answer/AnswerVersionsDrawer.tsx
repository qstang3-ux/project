import { useQuery } from '@tanstack/react-query';
import { Descriptions, Drawer, Empty, Segmented, Skeleton, Tag } from 'antd';
import { useState } from 'react';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function AnswerVersionsDrawer({ messageId, open, onClose }: { messageId: string; open: boolean; onClose: () => void }) {
  const [selectedVersion, setSelectedVersion] = useState<number>();
  const versionsQuery = useQuery({ queryKey: queryKeys.answerVersions(messageId), queryFn: () => api.listAnswerVersions(messageId), enabled: open });
  const versions = versionsQuery.data ?? [];
  const version = versions.find((item) => item.versionNo === selectedVersion) ?? versions.find((item) => item.isCurrent) ?? versions.at(-1);

  return <Drawer title="回答版本" width={680} open={open} onClose={onClose}>
    {versionsQuery.isLoading ? <Skeleton active paragraph={{ rows: 8 }} /> : null}
    {versionsQuery.isError ? <Empty description="回答版本加载失败" /> : null}
    {versions.length ? <>
      <Segmented block value={version?.versionNo} options={versions.map((item) => ({ label: `版本 ${String(item.versionNo)}`, value: item.versionNo }))} onChange={setSelectedVersion} />
      {version ? <div className="answer-version-detail">
        <Descriptions size="small" column={1} items={[
          { key: 'current', label: '版本状态', children: version.isCurrent ? <Tag color="processing">当前版本</Tag> : <Tag>历史版本</Tag> },
          { key: 'model', label: '模型', children: version.modelName ?? '--' },
          { key: 'duration', label: '耗时', children: version.durationMs === null || version.durationMs === undefined ? '--' : `${(version.durationMs / 1000).toFixed(1)}s` },
          { key: 'created', label: '生成时间', children: new Date(version.createdAt).toLocaleString('zh-CN') },
          { key: 'chart', label: '图表类型', children: version.chart?.type ?? 'none' },
        ]} />
        <section><h3>回答</h3><div className="answer-version-text">{version.answer || '该版本没有回答正文。'}</div></section>
        {version.sql ? <section><h3>SQL</h3><pre className="mono answer-version-sql">{version.sql}</pre></section> : null}
      </div> : null}
    </> : null}
  </Drawer>;
}
