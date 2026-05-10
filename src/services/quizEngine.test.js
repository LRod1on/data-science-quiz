import { initial, chooseTopic } from './quizEngine';

describe('quizEngine.initial', () => {
  test('возвращает welcome-стейт с пустым радаром', () => {
    const s = initial();
    expect(s.status).toBe('welcome');
    expect(s.currentTopic).toBeNull();
    expect(s.questionPlan).toEqual([]);
    expect(s.questionIdx).toBe(0);
    expect(s.selectedOption).toBeNull();
    expect(s.dontKnow).toBe(false);
    expect(s.correctCount).toBe(0);
    expect(s.radarScores).toEqual({
      python: null,
      classical_ml: null,
      deep_learning: null,
      nlp_cv: null,
    });
  });
});

describe('quizEngine.chooseTopic', () => {
  test('переводит из welcome в length-pick и запоминает тему', () => {
    const s = chooseTopic(initial(), 'python');
    expect(s.status).toBe('length-pick');
    expect(s.currentTopic).toBe('python');
  });

  test('игнорируется в любом статусе кроме welcome', () => {
    const base = { ...initial(), status: 'quiz', currentTopic: 'python' };
    expect(chooseTopic(base, 'classical_ml')).toBe(base);
  });
});
