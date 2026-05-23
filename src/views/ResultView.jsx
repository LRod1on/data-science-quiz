import React from 'react';
import styled from 'styled-components';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
} from 'chart.js';
import { TOPICS } from '../constants/topics';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

const Wrapper = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding:
    calc(48px + var(--top-inset, 0px))
    calc(48px + var(--right-inset, 0px))
    calc(48px + var(--bottom-inset, 0px))
    calc(48px + var(--left-inset, 0px));
  box-sizing: border-box;
`;

const Title = styled.h1`
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 40px;
`;

const ChartWrapper = styled.div`
  width: 480px;
  height: 360px;
  margin-bottom: 28px;
`;

const ScoreGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 64px;
  margin-bottom: 36px;
`;

const ScoreRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  font-size: 22px;
  color: ${(props) => (props.$played ? '#fff' : 'rgba(255, 255, 255, 0.35)')};
`;

const ScoreValue = styled.span`
  font-weight: 600;
`;

const ButtonsRow = styled.div`
  display: flex;
  gap: 24px;
`;

const ActionButton = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  color: #fff;
  font-size: 24px;
  padding: 16px 36px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.18); }
`;

// Конфиг chart.js: радар 0..100, без анимации (на TV-экранах SberBox
// она тормозит), цвета подобраны под тёмную тему приложения.
const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  // Боковой padding, чтобы длинные подписи ('NLP & CV', 'Classical ML')
  // не упирались в края canvas и не обрезались.
  layout: { padding: { left: 32, right: 32 } },
  scales: {
    r: {
      min: 0,
      max: 100,
      ticks: { display: false },
      grid: { color: 'rgba(255, 255, 255, 0.2)' },
      angleLines: { color: 'rgba(255, 255, 255, 0.2)' },
      pointLabels: {
        color: '#fff',
        font: { size: 18 },
      },
    },
  },
  plugins: { legend: { display: false } },
};

export function ResultView({ scores, onMoreTopic, onResetAll }) {

  const chartData = {
    labels: TOPICS.map((t) => t.label),
    datasets: [
      {
        label: 'Результат',
        data: TOPICS.map((t) => (scores[t.key] != null ? Math.round(scores[t.key] * 100) : 0)),
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        borderColor: 'rgba(255, 255, 255, 0.7)',
        pointBackgroundColor: TOPICS.map((t) =>
          scores[t.key] === null ? 'rgba(255,255,255,0.2)' : '#fff'
        ),
        pointRadius: 5,
      },
    ],
  };

  return (
    <Wrapper>
      <Title>Результаты</Title>

      <ChartWrapper>
        <Radar data={chartData} options={CHART_OPTIONS} />
      </ChartWrapper>

      <ScoreGrid>
        {TOPICS.map((t) => {
          const played = scores[t.key] !== null;
          return (
            <ScoreRow key={t.key} $played={played}>
              <span>{t.label}</span>
              <ScoreValue>
                {played ? `${Math.round(scores[t.key] * 100)} %` : '— %'}
              </ScoreValue>
            </ScoreRow>
          );
        })}
      </ScoreGrid>

      <ButtonsRow>
        <ActionButton onClick={onMoreTopic}>Пройти ещё тему</ActionButton>
        <ActionButton onClick={onResetAll}>Начать заново</ActionButton>
      </ButtonsRow>
    </Wrapper>
  );
}
