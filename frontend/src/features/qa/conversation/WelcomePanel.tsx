import { BulbOutlined, RobotOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import type { ApplicationConfig } from '../../../api/types';

export function WelcomePanel({ config, onSelect }: { config: ApplicationConfig; onSelect: (question: string) => void }) {
  return (
    <section className="welcome-panel">
      <span className="welcome-icon"><RobotOutlined /></span>
      <h1>你好，我是经管之星</h1>
      {config.greetingEnabled ? <p>{config.greetingText}</p> : null}
      {config.recommendedQuestions.length ? <div className="recommendations"><span><BulbOutlined /> 你可以这样问</span>{config.recommendedQuestions.map((question) => <Button className="suggestion-button" key={question} onClick={() => onSelect(question)}>{question}</Button>)}</div> : null}
    </section>
  );
}
