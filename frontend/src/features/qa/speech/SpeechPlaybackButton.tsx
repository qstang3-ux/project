import { PauseCircleOutlined, SoundOutlined } from '@ant-design/icons';
import { App, Button, Tooltip } from 'antd';
import { useEffect, useRef, useState } from 'react';

interface SpeechPlaybackButtonProps {
  text: string;
  enabled: boolean;
}

export function SpeechPlaybackButton({ text, enabled }: SpeechPlaybackButtonProps) {
  const { message } = App.useApp();
  const [speaking, setSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const synthesis = typeof window === 'undefined' ? undefined : window.speechSynthesis;
  const supported = typeof SpeechSynthesisUtterance !== 'undefined' && typeof synthesis?.speak === 'function';

  useEffect(() => () => {
    if (utteranceRef.current) window.speechSynthesis.cancel();
  }, []);

  if (!enabled || !text.trim()) return null;

  const toggle = () => {
    if (!supported) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      utteranceRef.current = null;
      setSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = 1;
    const chineseVoice = window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase().startsWith('zh'));
    if (chineseVoice) utterance.voice = chineseVoice;
    utterance.onend = () => {
      utteranceRef.current = null;
      setSpeaking(false);
    };
    utterance.onerror = (event) => {
      utteranceRef.current = null;
      setSpeaking(false);
      if (event.error === 'canceled' || event.error === 'interrupted') return;
      void message.error('语音播放失败，请检查系统音频设置。');
    };
    utteranceRef.current = utterance;
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const label = supported ? (speaking ? '停止朗读' : '朗读回答') : '当前浏览器不支持语音播放';
  return (
    <Tooltip title={label}>
      <span>
        <Button
          className={`answer-action icon-button icon-button-quiet speech-playback-button${speaking ? ' is-speaking' : ''}`}
          type="text"
          size="small"
          aria-label={label}
          aria-pressed={speaking}
          icon={speaking ? <PauseCircleOutlined /> : <SoundOutlined />}
          disabled={!supported}
          onClick={toggle}
        />
      </span>
    </Tooltip>
  );
}
