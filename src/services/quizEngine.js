// Чистая state-машина квиза. Никаких сайд-эффектов: только функции от state.
// Используется из App.jsx, ассистент и DOM в этот модуль не приходят.

import { QUESTIONS } from '../data/questions';

const EMPTY_RADAR = Object.freeze({
  python: null,
  classical_ml: null,
  deep_learning: null,
  nlp_cv: null,
});

export function initial() {
  return {
    status: 'welcome',
    currentTopic: null,
    questionPlan: [],
    questionIdx: 0,
    selectedOption: null,
    dontKnow: false,
    correctCount: 0,
    radarScores: { ...EMPTY_RADAR },
  };
}

export function chooseTopic(state, topic) {
  if (state.status !== 'welcome') return state;
  return { ...state, status: 'length-pick', currentTopic: topic };
}

// Fisher-Yates на копии массива. random — параметр, чтобы тесты могли инжектить
// детерминированный источник.
function shuffle(items, random) {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function chooseLength(state, length, random = Math.random) {
  if (state.status !== 'length-pick') return state;
  const bank = QUESTIONS[state.currentTopic] ?? [];
  const shuffled = shuffle(bank, random);
  const take = length === 'all' ? shuffled.length : Math.min(length, shuffled.length);
  return {
    ...state,
    status: 'quiz',
    questionPlan: shuffled.slice(0, take),
    questionIdx: 0,
    correctCount: 0,
    selectedOption: null,
    dontKnow: false,
  };
}

export function pickAnswer(state, optionIdx) {
  if (state.status !== 'quiz') return state;
  const current = state.questionPlan[state.questionIdx];
  const isCorrect = optionIdx === current.correct;
  return {
    ...state,
    status: 'feedback',
    selectedOption: optionIdx,
    dontKnow: false,
    correctCount: state.correctCount + (isCorrect ? 1 : 0),
  };
}

export function markUnknown(state) {
  if (state.status !== 'quiz') return state;
  return {
    ...state,
    status: 'feedback',
    selectedOption: null,
    dontKnow: true,
  };
}
