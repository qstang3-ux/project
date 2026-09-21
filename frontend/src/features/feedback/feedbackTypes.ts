import type { FeedbackReason, FeedbackStatus } from '../../api/types';

export interface FeedbackFilters {
  keyword?: string;
  userId?: string;
  status?: FeedbackStatus;
  reason?: FeedbackReason;
}
