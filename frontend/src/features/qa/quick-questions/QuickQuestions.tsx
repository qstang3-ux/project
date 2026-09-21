import { CloseOutlined, DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Button, Empty, Popover, Skeleton, Tabs, Tooltip } from 'antd';
import { useEffect, useState } from 'react';
import { api } from '../../../api/client';
import { getErrorMessage } from '../../../api/errorMessages';
import { queryKeys } from '../../../api/queryKeys';

interface QuickQuestionsProps {
  frequentEnabled: boolean;
  onSelect: (question: string) => void;
}

export function QuickQuestions({ frequentEnabled, onSelect }: QuickQuestionsProps) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const frequentQuery = useQuery({ queryKey: queryKeys.frequentQuestions, queryFn: () => api.listFrequentQuestions(10), enabled: open && frequentEnabled });
  const favoritesQuery = useQuery({ queryKey: queryKeys.favorites, queryFn: api.listFavorites, enabled: open });
  const removeFavorite = useMutation({
    mutationFn: api.removeFavorite,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.favorites }),
    onError: (error) => void message.error(getErrorMessage(error)),
  });

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [open]);

  const choose = (question: string) => {
    onSelect(question);
    setOpen(false);
  };
  const content = (
    <div className="quick-question-panel">
      <div className="quick-question-heading"><strong><ThunderboltOutlined /> 快捷提问</strong><Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭快捷提问" onClick={() => setOpen(false)} /></div>
      <Tabs size="small" defaultActiveKey={frequentEnabled ? 'frequent' : 'favorites'} items={[
        ...(frequentEnabled ? [{ key: 'frequent', label: '常问', children: frequentQuery.isLoading ? <Skeleton active paragraph={{ rows: 3 }} /> : frequentQuery.data?.length ? <div className="quick-question-list">{frequentQuery.data.map((item) => <button key={item.question} type="button" onClick={() => choose(item.question)}><span>{item.question}</span><small>{item.count} 次</small></button>)}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无常问问题" /> }] : []),
        { key: 'favorites', label: '收藏', children: favoritesQuery.isLoading ? <Skeleton active paragraph={{ rows: 3 }} /> : favoritesQuery.data?.length ? <div className="quick-question-list">{favoritesQuery.data.map((item) => <div className="quick-favorite" key={item.id}><button type="button" onClick={() => choose(item.question)}>{item.question}</button><Tooltip title="取消收藏"><Button type="text" size="small" danger icon={<DeleteOutlined />} aria-label={`取消收藏：${item.question}`} loading={removeFavorite.isPending && removeFavorite.variables === item.id} onClick={() => removeFavorite.mutate(item.id)} /></Tooltip></div>)}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无收藏问题" /> },
      ]} />
    </div>
  );
  return (
    <Popover open={open} onOpenChange={setOpen} trigger="click" placement="topLeft" arrow={false} content={content} classNames={{ root: 'quick-question-popover' }}>
      <Button className="quick-question-trigger" type="text" icon={<ThunderboltOutlined />} aria-label="打开快捷提问">快捷提问</Button>
    </Popover>
  );
}
