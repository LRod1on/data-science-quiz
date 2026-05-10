import { initial, chooseTopic, chooseLength, pickAnswer, markUnknown } from './quizEngine';
import { QUESTIONS } from '../data/questions';

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

describe('quizEngine.chooseLength', () => {
  function deterministicRandom(values) {
    let i = 0;
    return () => values[i++ % values.length];
  }

  test('переводит из length-pick в quiz и берёт N вопросов', () => {
    const base = { ...initial(), status: 'length-pick', currentTopic: 'python' };
    const s = chooseLength(base, 5, deterministicRandom([0]));
    expect(s.status).toBe('quiz');
    expect(s.questionPlan).toHaveLength(Math.min(5, QUESTIONS.python.length));
    expect(s.questionIdx).toBe(0);
    expect(s.correctCount).toBe(0);
    expect(s.selectedOption).toBeNull();
    expect(s.dontKnow).toBe(false);
  });

  test('length="all" берёт весь банк темы', () => {
    const base = { ...initial(), status: 'length-pick', currentTopic: 'python' };
    const s = chooseLength(base, 'all', deterministicRandom([0]));
    expect(s.questionPlan).toHaveLength(QUESTIONS.python.length);
  });

  test('если в банке меньше N — берёт всё что есть', () => {
    const base = { ...initial(), status: 'length-pick', currentTopic: 'python' };
    const s = chooseLength(base, 1000, deterministicRandom([0]));
    expect(s.questionPlan).toHaveLength(QUESTIONS.python.length);
  });

  test('игнорируется в любом статусе кроме length-pick', () => {
    const base = { ...initial(), status: 'quiz', currentTopic: 'python' };
    expect(chooseLength(base, 5, Math.random)).toBe(base);
  });

  test('сохраняет уникальность id в плане', () => {
    const base = { ...initial(), status: 'length-pick', currentTopic: 'python' };
    const s = chooseLength(base, 'all', deterministicRandom([0]));
    const ids = s.questionPlan.map((q) => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

function startedQuiz(topic = 'python') {
  const s0 = initial();
  const s1 = chooseTopic(s0, topic);
  return chooseLength(s1, 'all', () => 0);
}

describe('quizEngine.pickAnswer', () => {
  test('правильный ответ увеличивает correctCount и переводит в feedback', () => {
    const s = startedQuiz();
    const correctIdx = s.questionPlan[0].correct;
    const after = pickAnswer(s, correctIdx);
    expect(after.status).toBe('feedback');
    expect(after.selectedOption).toBe(correctIdx);
    expect(after.dontKnow).toBe(false);
    expect(after.correctCount).toBe(1);
  });

  test('неправильный ответ не увеличивает correctCount', () => {
    const s = startedQuiz();
    const wrongIdx = (s.questionPlan[0].correct + 1) % 4;
    const after = pickAnswer(s, wrongIdx);
    expect(after.status).toBe('feedback');
    expect(after.selectedOption).toBe(wrongIdx);
    expect(after.correctCount).toBe(0);
  });

  test('игнорируется вне статуса quiz', () => {
    const base = startedQuiz();
    const inFeedback = pickAnswer(base, base.questionPlan[0].correct);
    expect(pickAnswer(inFeedback, 0)).toBe(inFeedback);
  });
});

describe('quizEngine.markUnknown', () => {
  test('переводит в feedback с dontKnow=true и не увеличивает correctCount', () => {
    const s = startedQuiz();
    const after = markUnknown(s);
    expect(after.status).toBe('feedback');
    expect(after.dontKnow).toBe(true);
    expect(after.selectedOption).toBeNull();
    expect(after.correctCount).toBe(0);
  });

  test('игнорируется вне статуса quiz', () => {
    const base = { ...initial(), status: 'feedback' };
    expect(markUnknown(base)).toBe(base);
  });
});
