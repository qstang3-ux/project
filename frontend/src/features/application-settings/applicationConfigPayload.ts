import type { ApplicationConfig, ApplicationConfigUpdate } from '../../api/types';

export function buildApplicationConfigUpdate(
  current: ApplicationConfig,
  draft: Partial<ApplicationConfigUpdate>,
): ApplicationConfigUpdate {
  return {
    greetingEnabled: draft.greetingEnabled ?? current.greetingEnabled,
    greetingText: draft.greetingText ?? current.greetingText,
    recommendedQuestions: draft.recommendedQuestions ?? current.recommendedQuestions,
    followUpEnabled: draft.followUpEnabled ?? current.followUpEnabled,
    frequentQuestionsEnabled: draft.frequentQuestionsEnabled ?? current.frequentQuestionsEnabled,
    frequentQuestionThreshold: draft.frequentQuestionThreshold ?? current.frequentQuestionThreshold,
    modelQaEnabled: draft.modelQaEnabled ?? current.modelQaEnabled,
    ttsEnabled: draft.ttsEnabled ?? current.ttsEnabled,
    sttEnabled: draft.sttEnabled ?? current.sttEnabled,
    version: draft.version ?? current.version,
  };
}
