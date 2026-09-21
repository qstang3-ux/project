export interface BrowserSpeechRecognitionAlternative {
  transcript: string;
}

export interface BrowserSpeechRecognitionResult {
  readonly length: number;
  readonly isFinal: boolean;
  [index: number]: BrowserSpeechRecognitionAlternative;
}

export interface BrowserSpeechRecognitionResultList {
  readonly length: number;
  [index: number]: BrowserSpeechRecognitionResult;
}

export interface BrowserSpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: BrowserSpeechRecognitionResultList;
}

export interface BrowserSpeechRecognitionErrorEvent extends Event {
  readonly error: string;
}

export interface BrowserSpeechRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  }
}

export function getSpeechRecognitionConstructor(): BrowserSpeechRecognitionConstructor | undefined {
  if (typeof window === 'undefined') return undefined;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export function appendTranscript(currentValue: string, transcript: string): string {
  const current = currentValue.trimEnd();
  const recognized = transcript.trim();
  if (!recognized) return currentValue;
  return current ? `${current}\n${recognized}` : recognized;
}

export function speechRecognitionErrorMessage(code: string): string {
  const messages: Record<string, string> = {
    'not-allowed': '未获得麦克风权限，请在浏览器设置中允许后重试。',
    'service-not-allowed': '当前浏览器不允许使用语音识别服务。',
    'audio-capture': '没有检测到可用的麦克风。',
    'no-speech': '没有识别到语音，请靠近麦克风后重试。',
    network: '语音识别网络不可用，请稍后重试或改用文字输入。',
    aborted: '语音输入已取消。',
  };
  return messages[code] ?? '语音识别失败，请重试或改用文字输入。';
}
