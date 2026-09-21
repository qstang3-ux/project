import { StarFilled, StarOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Button, Tooltip } from 'antd';
import { api } from '../../../api/client';
import { getErrorMessage } from '../../../api/errorMessages';
import { queryKeys } from '../../../api/queryKeys';

export function FavoriteQuestionButton({ question, sourceMessageId }: { question: string; sourceMessageId: string }) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const favorites = useQuery({ queryKey: queryKeys.favorites, queryFn: api.listFavorites });
  const favorite = favorites.data?.find((item) => item.sourceMessageId === sourceMessageId || item.question === question);
  const mutation = useMutation({
    mutationFn: () => favorite ? api.removeFavorite(favorite.id) : api.addFavorite({ question, sourceMessageId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.favorites });
      void message.success(favorite ? '已取消收藏' : '已收藏到快捷提问');
    },
    onError: (error) => void message.error(getErrorMessage(error)),
  });
  const label = favorite ? '取消收藏问题' : '收藏问题';
  return <Tooltip title={label}><Button className="message-inline-action" type="text" size="small" icon={favorite ? <StarFilled /> : <StarOutlined />} aria-label={label} loading={mutation.isPending} onClick={() => mutation.mutate()} /></Tooltip>;
}
