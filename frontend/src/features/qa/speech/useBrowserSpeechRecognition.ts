import { useCallback, useEffect, useRef, useState } from 'react';
import {
  appendTranscript,
  getSpeechRecognitionConstructor,
  speechRecognitionErrorMessage,
  type BrowserSpeechRecognition,
} from './browserSpeech';

interface UseBrowserSpeechRecognitionOptions {
  enabled: boolean;
  value: string;
  onChange: (value: string) => void;
  onError: (message: string) => void;
}

export function useBrowserSpeechRecognition(options: UseBrowserSpeechRecognitionOptions) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const baseValueRef = useRef('');
  const supported = Boolean(getSpeechRecognitionConstructor());

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    if (!options.enabled || listening) return;
    const Recognition = getSpeechRecognitionConstructor();
    if (!Recognition) {
      options.onError('当前浏览器不支持语音输入，请使用最新版 Chrome 或 Edge，或改用文字输入。');
      return;
    }

    const recognition = new Recognition();
    baseValueRef.current = options.value;
    recognition.lang = 'zh-CN';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => {
      setListening(false);
      if (recognitionRef.current === recognition) recognitionRef.current = null;
    };
    recognition.onerror = (event) => {
      setListening(false);
      if (event.error !== 'aborted') options.onError(speechRecognitionErrorMessage(event.error));
    };
    recognition.onresult = (event) => {
      let transcript = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result?.isFinal) transcript += result[0]?.transcript ?? '';
      }
      options.onChange(appendTranscript(baseValueRef.current, transcript));
    };
    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setListening(false);
      options.onError('语音输入启动失败，请检查麦克风权限后重试。');
    }
  }, [listening, options]);

  useEffect(() => () => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
  }, []);

  return { supported, listening, start, stop };
}
