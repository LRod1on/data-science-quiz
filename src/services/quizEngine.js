// Чистая state-машина квиза. Никаких сайд-эффектов: только функции от state.
// Используется из App.jsx, ассистент и DOM в этот модуль не приходят.

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
