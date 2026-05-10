import React from 'react';
import styled, { css } from 'styled-components';
import { TOPICS } from '../constants/topics';

const TOPIC_LABELS = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]));

const Wrapper = styled.div`
  min-height: 100vh;
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
  margin-bottom: 32px;
`;

const Badge = styled.div`
  font-size: 24px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
`;

const QuestionText = styled.h2`
  font-size: 30px;
  line-height: 1.5;
  color: #fff;
  margin: 0 0 32px;
  text-align: center;
`;

const OptionsGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
`;

const Option = styled.button`
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 18px;
  padding: 22px 24px;
  text-align: left;
  font-size: 22px;
  line-height: 1.45;
  color: #fff;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:hover:not(:disabled),
  &:focus:not(:disabled) {
    background: rgba(255, 255, 255, 0.16);
    border-color: rgba(255, 255, 255, 0.4);
    outline: none;
  }

  &:disabled { cursor: default; }

  ${(p) => p.$correct && css`
    background: rgba(60, 200, 100, 0.25);
    border-color: rgba(60, 200, 100, 0.85);
  `}
  ${(p) => p.$wrong && css`
    background: rgba(220, 60, 60, 0.25);
    border-color: rgba(220, 60, 60, 0.85);
  `}
`;

const OptionNumber = styled.span`
  display: inline-block;
  width: 32px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.55);
`;

const Explanation = styled.div`
  margin: 32px auto 0;
  max-width: 960px;
  padding: 20px 24px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 22px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
`;

const ExplanationLead = styled.div`
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
  color: ${(p) => (p.$correct ? '#7fdc9c' : '#ff8a8a')};
`;

const Buttons = styled.div`
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 36px;
`;

const Button = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 16px;
  color: #fff;
  font-size: 22px;
  padding: 14px 28px;
  min-width: 220px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.18); }
`;

export function QuizView({
  topic,
  questionIdx,
  totalQuestions,
  question,
  status,
  selectedOption,
  dontKnow,
  onPick,
  onDontKnow,
  onNext,
  onFinish,
}) {
  const showFeedback = status === 'feedback';
  const isCorrect = showFeedback && !dontKnow && selectedOption === question.correct;

  return (
    <Wrapper>
      <TopRow>
        <Badge>
          {TOPIC_LABELS[topic]} &bull; {questionIdx + 1} / {totalQuestions}
        </Badge>
      </TopRow>

      <QuestionText>{question.text}</QuestionText>

      <OptionsGrid>
        {question.options.map((opt, idx) => {
          const isSelected = selectedOption === idx;
          const isCorrectOpt = idx === question.correct;
          return (
            <Option
              key={idx}
              disabled={showFeedback}
              $correct={showFeedback && isCorrectOpt}
              $wrong={showFeedback && isSelected && !isCorrectOpt}
              onClick={() => onPick(idx)}
            >
              <OptionNumber>{idx + 1}.</OptionNumber>
              {opt}
            </Option>
          );
        })}
      </OptionsGrid>

      {showFeedback && (
        <Explanation>
          <ExplanationLead $correct={isCorrect}>
            {dontKnow ? 'Правильный ответ' : isCorrect ? 'Правильно' : 'Неверно'}
          </ExplanationLead>
          {question.explanation}
        </Explanation>
      )}

      <Buttons>
        {!showFeedback && (
          <Button onClick={onDontKnow}>Не знаю</Button>
        )}
        {showFeedback && (
          <Button onClick={onNext}>Дальше</Button>
        )}
        <Button onClick={onFinish}>Закончить</Button>
      </Buttons>
    </Wrapper>
  );
}
