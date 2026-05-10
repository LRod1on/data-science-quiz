import { initial, chooseTopic, chooseLength, pickAnswer, markUnknown, nextQuestion, finishTopic, restart, resetAll } from './quizEngine';
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

function feedbackAt(idx, correctCount = idx) {
  const s = startedQuiz();
  return {
    ...s,
    status: 'feedback',
    questionIdx: idx,
    selectedOption: 0,
    correctCount,
  };
}

describe('quizEngine.nextQuestion', () => {
  test('переводит из feedback в quiz и инкрементит индекс', () => {
    // Банк python — 1 вопрос, поэтому используем classical_ml (тоже 1),
    // но тест на промежуточный шаг: принудительно ставим questionPlan из 2 элементов
    const s = startedQuiz();
    // Имитируем план из 2 вопросов чтобы проверить промежуточный переход
    const twoQuestions = [s.questionPlan[0], s.questionPlan[0]];
    const inFeedback = { ...s, questionPlan: twoQuestions, status: 'feedback', questionIdx: 0, selectedOption: 0 };
    const after = nextQuestion(inFeedback);
    expect(after.status).toBe('quiz');
    expect(after.questionIdx).toBe(1);
    expect(after.selectedOption).toBeNull();
    expect(after.dontKnow).toBe(false);
  });

  test('после последнего вопроса идёт в results и пишет долю в радар', () => {
    const s = startedQuiz();
    const last = s.questionPlan.length - 1;
    const inFeedback = { ...s, status: 'feedback', questionIdx: last, correctCount: last + 1 };
    const after = nextQuestion(inFeedback);
    expect(after.status).toBe('results');
    expect(after.radarScores.python).toBeCloseTo(1);
  });

  test('игнорируется вне feedback', () => {
    const base = startedQuiz();
    expect(nextQuestion(base)).toBe(base);
  });
});

describe('quizEngine.finishTopic', () => {
  test('из quiz: пишет долю по уже отвеченным и идёт в results', () => {
    const s = startedQuiz();
    expect(s.questionPlan.length).toBeGreaterThanOrEqual(1);
    const mid = { ...s, questionIdx: 1, correctCount: 1 };
    const after = finishTopic(mid);
    expect(after.status).toBe('results');
    expect(after.radarScores.python).toBeCloseTo(1);
  });

  test('из feedback: текущий вопрос засчитан, доля по questionIdx+1', () => {
    const inFb = { ...startedQuiz(), status: 'feedback', questionIdx: 0, correctCount: 1 };
    const after = finishTopic(inFb);
    expect(after.status).toBe('results');
    expect(after.radarScores.python).toBeCloseTo(1);
  });

  test('если ничего не отвечено — радар null (тема не считается пройденной)', () => {
    const s = startedQuiz();
    const after = finishTopic(s);
    expect(after.radarScores.python).toBeNull();
    expect(after.status).toBe('results');
  });

  test('игнорируется вне quiz/feedback', () => {
    const base = { ...initial(), status: 'results' };
    expect(finishTopic(base)).toBe(base);
  });
});

describe('quizEngine.restart', () => {
  test('из results возвращает на welcome, сохраняя радар', () => {
    const radar = { python: 0.6, classical_ml: null, deep_learning: null, nlp_cv: null };
    const base = { ...initial(), status: 'results', radarScores: radar };
    const after = restart(base);
    expect(after.status).toBe('welcome');
    expect(after.currentTopic).toBeNull();
    expect(after.questionPlan).toEqual([]);
    expect(after.radarScores).toEqual(radar);
  });

  test('игнорируется вне results', () => {
    const base = { ...initial(), status: 'quiz' };
    expect(restart(base)).toBe(base);
  });
});

describe('quizEngine.resetAll', () => {
  test('обнуляет радар и кладёт на welcome', () => {
    const radar = { python: 0.6, classical_ml: 0.4, deep_learning: null, nlp_cv: null };
    const base = { ...initial(), status: 'results', radarScores: radar };
    const after = resetAll(base);
    expect(after.status).toBe('welcome');
    expect(after.radarScores).toEqual({
      python: null,
      classical_ml: null,
      deep_learning: null,
      nlp_cv: null,
    });
  });
});
