import React from 'react';
import styled from 'styled-components';

const Wrapper = styled.div`
  min-height: calc(100vh - var(--bottom-inset, 0px));
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
  max-width: 720px;
  width: 100%;
`;

const Card = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  transition: background 0.15s, border-color 0.15s;

  &:hover,
  &:focus {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.4);
    outline: none;
  }
`;

const LENGTHS = [
  { value: 5,     label: '5 вопросов' },
  { value: 10,    label: '10 вопросов' },
  { value: 20,    label: '20 вопросов' },
  { value: 'all', label: 'Весь банк' },
];

export function LengthPickView({ onPick }) {
  return (
    <Wrapper>
      <Title>Сколько вопросов?</Title>
      <Subtitle>Скажи число или выбери карточку</Subtitle>
      <Grid>
        {LENGTHS.map((l) => (
          <Card key={String(l.value)} onClick={() => onPick(l.value)}>
            {l.label}
          </Card>
        ))}
      </Grid>
    </Wrapper>
  );
}
