import { Card } from 'antd';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { FeedbackDetailDrawer } from './FeedbackDetailDrawer';
import { FeedbackFilterForm } from './FeedbackFilterForm';
import { FeedbackProcessDialog } from './FeedbackProcessDialog';
import { FeedbackTable } from './FeedbackTable';
import { useFeedbackReview } from './useFeedbackReview';

export function FeedbackReview() {
  const review = useFeedbackReview();
  return (
    <div className="page-shell settings-page feedback-page">
      <div className="page-heading"><h1>回复校对</h1><p>筛选用户反馈，核对问题、SQL、结果和回答，并记录处理结论。</p></div>
      <Card><FeedbackFilterForm form={review.filterForm} onSubmit={review.applyFilters} onReset={review.resetFilters} /></Card>
      <Card>
        {review.listError ? <ErrorState title="反馈列表加载失败" error={review.listError} onRetry={() => void review.retryList()} /> : null}
        {!review.listError && !review.listLoading && (review.list?.items.length ?? 0) === 0 ? (
          <EmptyState title="暂无符合条件的反馈" description="调整筛选条件，或等待用户从回答卡片提交数据校对。" />
        ) : (
          <FeedbackTable items={review.list?.items ?? []} loading={review.listLoading} page={review.page} pageSize={review.pageSize} total={review.list?.page.total ?? 0} onPageChange={review.changePage} onView={review.selectFeedback} />
        )}
      </Card>
      <FeedbackDetailDrawer open={Boolean(review.selectedId)} detail={review.detail} loading={review.detailLoading} error={review.detailError} onClose={review.closeDetail} onRetry={() => void review.retryDetail()} onProcess={review.openProcess} />
      <FeedbackProcessDialog open={review.processOpen} form={review.updateForm} saving={review.processing} onCancel={review.closeProcess} onSave={review.saveProcess} />
    </div>
  );
}
