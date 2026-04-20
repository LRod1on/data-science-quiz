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
  padding: 48px;
`;

const Title = styled.h1`
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 40px;
`;

const ChartWrapper = styled.div`
  width: 460px;
  height: 460px;
  margin-bottom: 36px;
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

const Hint = styled.p`
  font-size: 20px;
  color: rgba(255, 255, 255, 0.45);
  text-align: center;
  max-width: 700px;
  margin: 0 0 40px;
  line-height: 1.5;
`;

const RestartButton = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  color: #fff;
  font-size: 26px;
  padding: 18px 56px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: rgba(255, 255, 255, 0.18);
  }
`;

const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  scales: {
    r: {
      min: 0,
      max: 10,
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

export function ResultView({ scores, onRestart }) {
  const playedTopics = TOPICS.filter((t) => scores[t.key] !== null);
  const unplayedTopics = TOPICS.filter((t) => scores[t.key] === null);

  const chartData = {
    labels: TOPICS.map((t) => t.label),
    datasets: [
      {
        label: 'Результат',
        data: TOPICS.map((t) => scores[t.key] ?? 0),
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
                {played ? `${scores[t.key].toFixed(1)} / 10` : '— / 10'}
              </ScoreValue>
            </ScoreRow>
          );
        })}
      </ScoreGrid>

      {unplayedTopics.length > 0 && (
        <Hint>
          Пройдено:{' '}
          {playedTopics.length > 0
            ? playedTopics.map((t) => t.label).join(', ')
            : 'ничего'}
          . Чтобы пройти остальные — скажи &laquo;начни{' '}
          {unplayedTopics[0].label}&raquo;.
        </Hint>
      )}

      <RestartButton onClick={onRestart}>Начать заново</RestartButton>
    </Wrapper>
  );
}
