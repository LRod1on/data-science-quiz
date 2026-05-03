import React from 'react';
import styled, { keyframes, css } from 'styled-components';
import { TOPICS } from '../constants/topics';

const TOPIC_LABELS = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]));

const Wrapper = styled.div`
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 48px;
  padding-bottom: calc(48px + var(--bottom-inset, 0px));
  box-sizing: border-box;
`;

const TopRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Badge = styled.div`
  font-size: 24px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
`;

const LoadingHint = styled.div`
  font-size: 20px;
  color: rgba(255, 255, 255, 0.4);
`;

const QuestionArea = styled.div`
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
  overflow-y: auto;
`;

const QuestionText = styled.p`
  font-size: 28px;
  line-height: 1.55;
  color: #fff;
  text-align: center;
  max-width: 820px;
  margin: 0;
`;

const PlaceholderText = styled.p`
  font-size: 28px;
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
  margin: 0;
`;

const AnswerBuffer = styled.div`
  margin-top: 24px;
  padding: 16px 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 22px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
  max-width: 820px;
  max-height: 280px;
  overflow-y: auto;
  text-align: left;
`;

const Hint = styled.div`
  font-size: 20px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  max-width: 820px;
`;

const Bottom = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
`;

const pulse = keyframes`
  0%, 100% { transform: scale(1); opacity: 1; }
  50%       { transform: scale(1.25); opacity: 0.6; }
`;

const MicDot = styled.div`
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: ${(props) => (props.$active ? '#fff' : 'rgba(255, 255, 255, 0.2)')};
  ${(props) =>
    props.$active &&
    css`
      animation: ${pulse} 1.5s ease-in-out infinite;
    `}
`;

const Buttons = styled.div`
  display: flex;
  gap: 24px;
`;

const Button = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 16px;
  color: #fff;
  font-size: 24px;
  padding: 16px 32px;
  min-width: 300px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.18);
  }

  &:disabled {
    opacity: 0.35;
    cursor: default;
  }
`;

const ErrorBanner = styled.div`
  background: rgba(220, 60, 60, 0.2);
  border: 1px solid rgba(220, 60, 60, 0.5);
  border-radius: 12px;
  color: #fff;
  font-size: 20px;
  padding: 12px 24px;
  text-align: center;
  max-width: 820px;
`;

export function InterviewView({
  topic,
  questionIndex,
  questionText,
  answerBuffer,
  isLoading,
  isListening,
  lastError,
  onSubmit,
  onNext,
  onFinish,
}) {
  const hasBuffer = Boolean(answerBuffer && answerBuffer.trim());
  return (
    <Wrapper>
      <TopRow>
        <Badge>
          {TOPIC_LABELS[topic]} &bull; {questionIndex} / 5
        </Badge>
        {isLoading && <LoadingHint>думаю...</LoadingHint>}
      </TopRow>

      <QuestionArea>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          {questionText
            ? <QuestionText>{questionText}</QuestionText>
            : <PlaceholderText>Загружаю вопрос...</PlaceholderText>
          }
          {hasBuffer && <AnswerBuffer>{answerBuffer}</AnswerBuffer>}
        </div>
      </QuestionArea>

      <Bottom>
        {lastError && <ErrorBanner>{lastError}</ErrorBanner>}
        <Hint>
          {hasBuffer
            ? 'Скажите «готово», когда закончите ответ. Можно добавить ещё.'
            : 'Отвечайте по частям. Скажите «дай подумать», если нужна пауза, и «готово» — когда закончите.'}
        </Hint>
        <MicDot $active={isListening} />
        <Buttons>
          <Button onClick={onSubmit} disabled={isLoading || !hasBuffer}>
            Готово
          </Button>
          <Button onClick={onNext} disabled={isLoading}>
            Следующий
          </Button>
          <Button onClick={onFinish} disabled={isLoading}>
            Закончить интервью
          </Button>
        </Buttons>
      </Bottom>
    </Wrapper>
  );
}
