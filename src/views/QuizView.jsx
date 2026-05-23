import React from 'react';
import styled, { css } from 'styled-components';
import { TOPICS } from '../constants/topics';

const TOPIC_LABELS = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]));

const Wrapper = styled.div`
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding:
    calc(28px + var(--top-inset, 0px))
    calc(48px + var(--right-inset, 0px))
    calc(28px + var(--bottom-inset, 0px))
    calc(48px + var(--left-inset, 0px));
  box-sizing: border-box;
  overflow: hidden;
`;

const TopRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex: 0 0 auto;
`;

const Badge = styled.div`
  font-size: 22px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
`;

const QuestionText = styled.h2`
  font-size: 24px;
  line-height: 1.35;
  color: #fff;
  margin: 0 0 18px;
  text-align: center;
  // Разрешаем шринк, чтобы длинные вопросы не выпихивали кнопки
  // за пределы 100vh (Wrapper стоит на overflow: hidden).
  flex: 0 1 auto;
  min-height: 0;
  overflow-wrap: anywhere;
`;

const OptionsGrid = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
  flex: 0 0 auto;
`;

const Option = styled.button`
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 14px 18px;
  text-align: left;
  font-size: 20px;
  line-height: 1.35;
  color: #fff;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  // По умолчанию grid-айтемы имеют min-width: auto и распирают колонку
  // под самое длинное слово — из-за этого 2-й и 4-й варианты вылезали
  // за правую границу грида.
  min-width: 0;
  overflow-wrap: anywhere;

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
  width: 28px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.55);
`;

const Explanation = styled.div`
  margin: 16px auto 0;
  max-width: 960px;
  padding: 12px 18px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 18px;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.85);
  flex: 1 1 auto;
  overflow: auto;
`;

const ExplanationLead = styled.div`
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 6px;
  color: ${(p) => (p.$correct ? '#7fdc9c' : '#ff8a8a')};
`;

const Buttons = styled.div`
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 18px;
  flex: 0 0 auto;
`;

const Button = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 14px;
  color: #fff;
  font-size: 20px;
  padding: 10px 24px;
  // Раньше стояло min-width: 200px — при узких safe-area-зонах две
  // кнопки с центрированием уезжали за края (левый край «Не знаю» прятался).
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.18); }
`;

const Spacer = styled.div`
  flex: 1 1 auto;
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

      {showFeedback ? (
        <Explanation>
          <ExplanationLead $correct={isCorrect}>
            {dontKnow ? 'Правильный ответ' : isCorrect ? 'Правильно' : 'Неверно'}
          </ExplanationLead>
          {question.explanation}
        </Explanation>
      ) : (
        <Spacer />
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
