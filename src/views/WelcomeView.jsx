import React from 'react';
import styled from 'styled-components';
import { TOPICS } from '../constants/topics';

const Wrapper = styled.div`
  min-height: calc(100vh - var(--bottom-inset, 0px));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
`;

const Title = styled.h1`
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 12px;
  text-align: center;
`;

const Subtitle = styled.p`
  font-size: 24px;
  color: rgba(255, 255, 255, 0.55);
  margin: 0 0 48px;
  text-align: center;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  max-width: 960px;
  width: 100%;
`;

const Card = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  padding: 36px 32px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:hover,
  &:focus {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.4);
    outline: none;
  }
`;

const CardLabel = styled.div`
  font-size: 30px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 10px;
`;

const CardDesc = styled.div`
  font-size: 20px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.45;
`;

export function WelcomeView({ onSelectTopic }) {
  return (
    <Wrapper>
      <Title>Симулятор технического интервью</Title>
      <Subtitle>Скажи тему голосом или нажми карточку</Subtitle>
      <Grid>
        {TOPICS.map((t) => (
          <Card key={t.key} onClick={() => onSelectTopic(t.key)}>
            <CardLabel>{t.label}</CardLabel>
            <CardDesc>{t.desc}</CardDesc>
          </Card>
        ))}
      </Grid>
    </Wrapper>
  );
}
