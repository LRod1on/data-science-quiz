import React from 'react';
import styled, { keyframes, css } from 'styled-components';
import { TOPICS } from '../constants/topics';

const TOPIC_LABELS = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]));

const Wrapper = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 48px;
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 0;
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
  padding: 16px 40px;
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
  isLoading,
  isListening,
  lastError,
  onNext,
  onGiveUp,
}) {
  return (
    <Wrapper>
      <TopRow>
        <Badge>
          {TOPIC_LABELS[topic]} &bull; {questionIndex + 1} / 5
        </Badge>
        {isLoading && <LoadingHint>думаю...</LoadingHint>}
      </TopRow>

      <QuestionArea>
        {questionText
          ? <QuestionText>{questionText}</QuestionText>
          : <PlaceholderText>Загружаю вопрос...</PlaceholderText>
        }
      </QuestionArea>

      <Bottom>
        {lastError && <ErrorBanner>{lastError}</ErrorBanner>}
        <MicDot $active={isListening} />
        <Buttons>
          <Button onClick={onNext} disabled={isLoading}>
            Следующий
          </Button>
          <Button onClick={onGiveUp} disabled={isLoading}>
            Сдаюсь
          </Button>
        </Buttons>
      </Bottom>
    </Wrapper>
  );
}
