# План рефакторинга «интервью → квиз без бэкенда»

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести приложение с голосового LLM-интервью на офлайн-квиз с
multiple choice (4 варианта на вопрос), убрать бэкенд целиком, сохранить
голосовое управление и радар-чарт результатов.

**Architecture:** Весь стейт и логика квиза живут во фронте: чистый модуль
`quizEngine` хранит правила переходов и подсчёта, `App.jsx` оркестрирует
ассистента и view-компоненты. Банк вопросов — статический JS-модуль,
бандлится в основной chunk. Бэкенд (`backend/`) удаляется.

**Tech Stack:** React 18 (CRA, class-компонент App), @salutejs/client,
styled-components, chart.js + react-chartjs-2, jest (через react-scripts).

**Спека:** `docs/superpowers/specs/2026-05-10-quiz-refactor-design.md`

---

## Файловая раскладка

**Создаётся:**
- `src/data/questions.js` — банк MCQ по темам.
- `src/data/questions.test.js` — структурная валидация банка.
- `src/services/quizEngine.js` — чистые функции state-машины.
- `src/services/quizEngine.test.js` — unit-тесты engine.
- `src/views/LengthPickView.jsx` — экран выбора длины.
- `src/views/QuizView.jsx` — экран вопроса и фидбека (заменяет InterviewView).

**Изменяется:**
- `src/App.jsx` — снимаем зависимость от бэка, переходим на quizEngine.
- `src/views/ResultView.jsx` — добавляется кнопка «Пройти ещё тему», шкала
  радара переключается с 0..10 на проценты.
- `smartapp-backend/src/sc/interview.sc` и `smartapp-backend/src/js/*.js` —
  переписываются под новые intent-ы.
- `CLAUDE.md`, `README.md` — актуализируются.

**Удаляется:**
- Папка `backend/` целиком.
- Папка `src/api/`.
- `src/services/evaluationDispatch.js`.
- `src/views/InterviewView.jsx`.
- Из корневого `.env.sample` — `REACT_APP_BACKEND_URL`.

---

### Task 1: Создать каркас банка вопросов

**Files:**
- Create: `src/data/questions.js`

- [ ] **Step 1: Создать файл с экспортом QUESTIONS и одним примером на каждую тему**

Создать `src/data/questions.js` с содержимым:

```js
// Банк вопросов квиза. Структура одного элемента:
// { id, text, options[4], correct (0..3), explanation }.
// Текст и варианты — plain text, без markdown/HTML, чтобы корректно прочёл TTS.

export const QUESTIONS = {
  python: [
    {
      id: 'py-gil-001',
      text: 'Что такое GIL в CPython?',
      options: [
        'Глобальная блокировка интерпретатора, не дающая нескольким потокам одновременно исполнять байт-код',
        'Сборщик мусора нового поколения',
        'Механизм оптимизации импортов',
        'Внутренний JIT-компилятор',
      ],
      correct: 0,
      explanation: 'GIL сериализует исполнение байт-кода между потоками, поэтому CPU-bound задачи не ускоряются от threading — нужен multiprocessing.',
    },
  ],
  classical_ml: [
    {
      id: 'ml-bias-variance-001',
      text: 'Что характерно для модели с высоким смещением (high bias)?',
      options: [
        'Большой gap между train и validation качеством',
        'Низкое качество и на train, и на validation',
        'Очень разные предсказания при небольшом изменении данных',
        'Идеальное запоминание обучающей выборки',
      ],
      correct: 1,
      explanation: 'Высокое смещение — это недообучение: модель слишком проста, и ей плохо как на train, так и на val.',
    },
  ],
  deep_learning: [
    {
      id: 'dl-batchnorm-001',
      text: 'Зачем в нейросети применяют batch normalization?',
      options: [
        'Чтобы уменьшить число параметров модели',
        'Чтобы выходы нелинейностей оставались в стабильном диапазоне и обучение шло быстрее',
        'Чтобы заменить функцию активации',
        'Чтобы избавиться от bias-членов в слоях',
      ],
      correct: 1,
      explanation: 'BN нормирует активации внутри батча, стабилизирует распределение входов следующего слоя и позволяет использовать большие learning rate.',
    },
  ],
  nlp_cv: [
    {
      id: 'nlpcv-bert-gpt-001',
      text: 'В чём ключевая архитектурная разница между BERT и GPT?',
      options: [
        'BERT — encoder-only с двунаправленным вниманием, GPT — decoder-only с causal-маской',
        'BERT работает только с английским, GPT — мультиязычный',
        'BERT использует RNN, GPT — трансформер',
        'У BERT больше параметров, чем у GPT',
      ],
      correct: 0,
      explanation: 'BERT обучается masked language modeling и видит контекст с обеих сторон. GPT генерирует слева направо и может смотреть только на предыдущие токены.',
    },
  ],
};
```

Это заглушка для прогонки тестов и фронта. Полное наполнение — отдельный
контент-этап после задач 1–11 (см. задачу 12-альт ниже).

- [ ] **Step 2: Коммит**

```bash
git add src/data/questions.js
git commit -m "feat(quiz): добавить каркас банка MCQ-вопросов

Структура банка: QUESTIONS[topic] = массив { id, text, options[4],
correct, explanation }. Пока по одному вопросу на тему — заглушка
для разработки и тестов."
```

---

### Task 2: Тесты валидации банка вопросов

**Files:**
- Create: `src/data/questions.test.js`

- [ ] **Step 1: Написать тесты валидации**

Создать `src/data/questions.test.js`:

```js
import { QUESTIONS } from './questions';

const TOPICS = ['python', 'classical_ml', 'deep_learning', 'nlp_cv'];

describe('банк вопросов', () => {
  test('содержит все четыре темы', () => {
    for (const topic of TOPICS) {
      expect(QUESTIONS[topic]).toBeDefined();
      expect(Array.isArray(QUESTIONS[topic])).toBe(true);
      expect(QUESTIONS[topic].length).toBeGreaterThan(0);
    }
  });

  test.each(TOPICS)('%s: каждый вопрос валиден', (topic) => {
    for (const q of QUESTIONS[topic]) {
      expect(typeof q.id).toBe('string');
      expect(q.id.length).toBeGreaterThan(0);
      expect(typeof q.text).toBe('string');
      expect(q.text.trim().length).toBeGreaterThan(0);
      expect(Array.isArray(q.options)).toBe(true);
      expect(q.options).toHaveLength(4);
      for (const opt of q.options) {
        expect(typeof opt).toBe('string');
        expect(opt.trim().length).toBeGreaterThan(0);
      }
      expect(Number.isInteger(q.correct)).toBe(true);
      expect(q.correct).toBeGreaterThanOrEqual(0);
      expect(q.correct).toBeLessThanOrEqual(3);
      expect(typeof q.explanation).toBe('string');
      expect(q.explanation.trim().length).toBeGreaterThan(0);
    }
  });

  test.each(TOPICS)('%s: id уникальны внутри темы', (topic) => {
    const ids = QUESTIONS[topic].map((q) => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
```

- [ ] **Step 2: Запустить тесты**

Команда:
```bash
yarn test --watchAll=false src/data/questions.test.js
```
Ожидаемо: PASS на текущем каркасе банка (по 1 валидному вопросу на тему).

- [ ] **Step 3: Коммит**

```bash
git add src/data/questions.test.js
git commit -m "test(quiz): валидация структуры банка вопросов

Проверяем: все четыре темы есть, options длиной 4, correct в диапазоне
0..3, id уникальны в пределах темы, все строковые поля непустые."
```

---

### Task 3: quizEngine — initial + chooseTopic (TDD)

**Files:**
- Create: `src/services/quizEngine.js`
- Create: `src/services/quizEngine.test.js`

- [ ] **Step 1: Написать тесты на `initial()` и `chooseTopic()`**

Создать `src/services/quizEngine.test.js`:

```js
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
```

- [ ] **Step 2: Запустить — должны падать (модуля нет)**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: FAIL — `Cannot find module './quizEngine'`.

- [ ] **Step 3: Реализовать `initial` и `chooseTopic`**

Создать `src/services/quizEngine.js`:

```js
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
```

- [ ] **Step 4: Прогнать тесты — должны пройти**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: PASS (3 теста).

- [ ] **Step 5: Коммит**

```bash
git add src/services/quizEngine.js src/services/quizEngine.test.js
git commit -m "feat(quiz): добавить quizEngine с initial и chooseTopic

Чистая state-машина квиза без зависимости от React и ассистента.
Первые два перехода: создание начального стейта и выбор темы."
```

---

### Task 4: quizEngine — chooseLength с инжектируемым random (TDD)

**Files:**
- Modify: `src/services/quizEngine.js`
- Modify: `src/services/quizEngine.test.js`

- [ ] **Step 1: Дописать тесты на `chooseLength()`**

Добавить в `src/services/quizEngine.test.js` после блока `chooseTopic`:

```js
import { chooseLength } from './quizEngine';
import { QUESTIONS } from '../data/questions';

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
```

- [ ] **Step 2: Запустить — должны падать**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: FAIL — `chooseLength is not a function`.

- [ ] **Step 3: Реализовать `chooseLength`**

Добавить в `src/services/quizEngine.js`:

```js
import { QUESTIONS } from '../data/questions';

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
```

- [ ] **Step 4: Прогон тестов**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: PASS.

- [ ] **Step 5: Коммит**

```bash
git add src/services/quizEngine.js src/services/quizEngine.test.js
git commit -m "feat(quiz): chooseLength с детерминируемым сэмплингом

Fisher-Yates с инжектируемым источником случайности — тесты могут
проверять стабильное поведение. Поддержаны числовые длины и 'all',
а также случай 'в банке меньше, чем запросили'."
```

---

### Task 5: quizEngine — pickAnswer и markUnknown (TDD)

**Files:**
- Modify: `src/services/quizEngine.js`
- Modify: `src/services/quizEngine.test.js`

- [ ] **Step 1: Дописать тесты**

Добавить в `src/services/quizEngine.test.js`:

```js
import { pickAnswer, markUnknown } from './quizEngine';

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
```

- [ ] **Step 2: Запуск — fail**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: FAIL.

- [ ] **Step 3: Реализовать функции**

Добавить в `src/services/quizEngine.js`:

```js
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
```

- [ ] **Step 4: Прогон**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```
Ожидаемо: PASS.

- [ ] **Step 5: Коммит**

```bash
git add src/services/quizEngine.js src/services/quizEngine.test.js
git commit -m "feat(quiz): pickAnswer и markUnknown с переходом в feedback

pickAnswer считает правильный/неправильный ответ. markUnknown — отдельный
переход для голосовой команды «не знаю»: не накручивает счётчик, выставляет
флаг dontKnow для подсветки на экране фидбека."
```

---

### Task 6: quizEngine — nextQuestion и finishTopic (TDD)

**Files:**
- Modify: `src/services/quizEngine.js`
- Modify: `src/services/quizEngine.test.js`

- [ ] **Step 1: Тесты**

Добавить в `src/services/quizEngine.test.js`:

```js
import { nextQuestion, finishTopic } from './quizEngine';

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
    const s = feedbackAt(0);
    const after = nextQuestion(s);
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
    const total = s.questionPlan.length;
    const mid = { ...s, questionIdx: 2, correctCount: 1 };
    const after = finishTopic(mid);
    expect(after.status).toBe('results');
    // 2 отвеченных вопроса (idx 0 и 1), 1 правильный → 0.5
    expect(after.radarScores.python).toBeCloseTo(1 / 2);
    expect(total).toBeGreaterThan(2);
  });

  test('из feedback: текущий вопрос засчитан, доля по questionIdx+1', () => {
    const inFb = { ...startedQuiz(), status: 'feedback', questionIdx: 1, correctCount: 2 };
    const after = finishTopic(inFb);
    expect(after.status).toBe('results');
    expect(after.radarScores.python).toBeCloseTo(2 / 2);
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
```

- [ ] **Step 2: Прогон — fail**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```

- [ ] **Step 3: Реализация**

Добавить в `src/services/quizEngine.js`:

```js
export function nextQuestion(state) {
  if (state.status !== 'feedback') return state;
  const nextIdx = state.questionIdx + 1;
  if (nextIdx >= state.questionPlan.length) {
    const total = state.questionPlan.length;
    return {
      ...state,
      status: 'results',
      radarScores: {
        ...state.radarScores,
        [state.currentTopic]: total > 0 ? state.correctCount / total : null,
      },
    };
  }
  return {
    ...state,
    status: 'quiz',
    questionIdx: nextIdx,
    selectedOption: null,
    dontKnow: false,
  };
}

export function finishTopic(state) {
  if (state.status !== 'quiz' && state.status !== 'feedback') return state;
  // На статусе quiz уже отвечены вопросы 0..questionIdx-1.
  // На статусе feedback текущий тоже зачтён, поэтому questionIdx+1.
  const answered = state.status === 'feedback'
    ? state.questionIdx + 1
    : state.questionIdx;
  const score = answered > 0 ? state.correctCount / answered : null;
  return {
    ...state,
    status: 'results',
    radarScores: {
      ...state.radarScores,
      [state.currentTopic]: score,
    },
  };
}
```

- [ ] **Step 4: Прогон — pass**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```

- [ ] **Step 5: Коммит**

```bash
git add src/services/quizEngine.js src/services/quizEngine.test.js
git commit -m "feat(quiz): nextQuestion и finishTopic с обновлением радара

nextQuestion после последнего вопроса финализирует тему. finishTopic —
досрочный финиш: считает долю по уже отвеченным и кладёт в радар.
Если до досрочного выхода вопросов не было — оставляем null."
```

---

### Task 7: quizEngine — restart и resetAll (TDD)

**Files:**
- Modify: `src/services/quizEngine.js`
- Modify: `src/services/quizEngine.test.js`

- [ ] **Step 1: Тесты**

Добавить:

```js
import { restart, resetAll } from './quizEngine';

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
```

- [ ] **Step 2: Прогон — fail**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```

- [ ] **Step 3: Реализация**

Добавить в `src/services/quizEngine.js`:

```js
export function restart(state) {
  if (state.status !== 'results') return state;
  return {
    ...initial(),
    radarScores: state.radarScores,
  };
}

export function resetAll() {
  return initial();
}
```

- [ ] **Step 4: Прогон — pass**

```bash
yarn test --watchAll=false src/services/quizEngine.test.js
```

- [ ] **Step 5: Коммит**

```bash
git add src/services/quizEngine.js src/services/quizEngine.test.js
git commit -m "feat(quiz): restart (с сохранением радара) и resetAll

restart — из results на welcome, накопленные баллы по темам остаются.
resetAll — полный сброс к initial-стейту."
```

---

### Task 8: View выбора длины

**Files:**
- Create: `src/views/LengthPickView.jsx`

- [ ] **Step 1: Создать компонент**

`src/views/LengthPickView.jsx`:

```jsx
import React from 'react';
import styled from 'styled-components';

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
```

- [ ] **Step 2: Коммит**

```bash
git add src/views/LengthPickView.jsx
git commit -m "feat(quiz): экран выбора длины прохождения

Четыре варианта: 5, 10, 20 вопросов и весь банк темы. Структура
карточек повторяет WelcomeView — голосом и кликом."
```

---

### Task 9: View вопроса и фидбека

**Files:**
- Create: `src/views/QuizView.jsx`

- [ ] **Step 1: Создать компонент**

`src/views/QuizView.jsx`:

```jsx
import React from 'react';
import styled, { css } from 'styled-components';
import { TOPICS } from '../constants/topics';

const TOPIC_LABELS = Object.fromEntries(TOPICS.map((t) => [t.key, t.label]));

const Wrapper = styled.div`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 48px;
  padding-bottom: calc(48px + var(--bottom-inset, 0px));
  box-sizing: border-box;
`;

const TopRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
`;

const Badge = styled.div`
  font-size: 24px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
`;

const QuestionText = styled.h2`
  font-size: 30px;
  line-height: 1.5;
  color: #fff;
  margin: 0 0 32px;
  text-align: center;
`;

const OptionsGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
`;

const Option = styled.button`
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 255, 255, 0.15);
  border-radius: 18px;
  padding: 22px 24px;
  text-align: left;
  font-size: 22px;
  line-height: 1.45;
  color: #fff;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

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
  width: 32px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.55);
`;

const Explanation = styled.div`
  margin: 32px auto 0;
  max-width: 960px;
  padding: 20px 24px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 22px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
`;

const ExplanationLead = styled.div`
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
  color: ${(p) => (p.$correct ? '#7fdc9c' : '#ff8a8a')};
`;

const Buttons = styled.div`
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 36px;
`;

const Button = styled.button`
  background: rgba(255, 255, 255, 0.1);
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 16px;
  color: #fff;
  font-size: 22px;
  padding: 14px 28px;
  min-width: 220px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255, 255, 255, 0.18); }
`;

export function QuizView({
  topic,
  questionIdx,
  totalQuestions,
  question,
  status,            // 'quiz' | 'feedback'
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

      {showFeedback && (
        <Explanation>
          <ExplanationLead $correct={isCorrect}>
            {dontKnow ? 'Правильный ответ' : isCorrect ? 'Правильно' : 'Неверно'}
          </ExplanationLead>
          {question.explanation}
        </Explanation>
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
```

- [ ] **Step 2: Коммит**

```bash
git add src/views/QuizView.jsx
git commit -m "feat(quiz): экран вопроса и фидбека MCQ

Один компонент рисует обе фазы — quiz и feedback. На фидбеке
правильный вариант подсвечивается зелёным, ошибочный выбор —
красным, под вариантами появляется текстовое объяснение."
```

---

### Task 10: Обновить ResultView

**Files:**
- Modify: `src/views/ResultView.jsx`

- [ ] **Step 1: Поменять шкалу с 0..10 на проценты и добавить кнопки**

Открыть `src/views/ResultView.jsx`. Заменить блок `CHART_OPTIONS`:

```js
const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
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
```

Заменить вычисление `chartData.datasets[0].data` на:

```js
data: TOPICS.map((t) => (scores[t.key] != null ? Math.round(scores[t.key] * 100) : 0)),
```

Заменить `ScoreValue`-вывод:

```jsx
<ScoreValue>
  {played ? `${Math.round(scores[t.key] * 100)} %` : '— %'}
</ScoreValue>
```

Заменить блок c `RestartButton` на пару кнопок:

```jsx
import styled from 'styled-components';
// ... существующие стили остаются ...

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
```

Сигнатура компонента и низ JSX:

```jsx
export function ResultView({ scores, onMoreTopic, onResetAll }) {
  // ... существующее ...
  return (
    <Wrapper>
      {/* ... Title / Chart / ScoreGrid / Hint ... */}
      <ButtonsRow>
        <ActionButton onClick={onMoreTopic}>Пройти ещё тему</ActionButton>
        <ActionButton onClick={onResetAll}>Начать заново</ActionButton>
      </ButtonsRow>
    </Wrapper>
  );
}
```

Старые `RestartButton` styled-component и проп `onRestart` — удалить.

- [ ] **Step 2: Коммит**

```bash
git add src/views/ResultView.jsx
git commit -m "refactor(result): шкала радара в процентах и две кнопки

Радар теперь 0..100 (доля правильных), значения по темам показываются
в процентах. Добавлена кнопка «Пройти ещё тему» — возврат на welcome
с сохранением радара. «Начать заново» — полный сброс."
```

---

### Task 11: Переписать App.jsx

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: Заменить содержимое App.jsx**

Целиком заменить `src/App.jsx`:

```jsx
import React from 'react';

import './App.css';
import { ErrorBoundary } from './components/ErrorBoundary';
import { WelcomeView } from './views/WelcomeView';
import { LengthPickView } from './views/LengthPickView';
import { QuizView } from './views/QuizView';
import { ResultView } from './views/ResultView';
import { createAssistantInstance, speak } from './services/assistant';
import {
  initial,
  chooseTopic,
  chooseLength,
  pickAnswer,
  markUnknown,
  nextQuestion,
  finishTopic,
  restart,
  resetAll,
} from './services/quizEngine';

const TOPIC_VOICE_LABELS = {
  python: 'Python',
  classical_ml: 'Классический ML',
  deep_learning: 'Deep Learning',
  nlp_cv: 'NLP и Computer Vision',
};

export class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = initial();
    this.assistant = createAssistantInstance(() => this.getStateForAssistant());

    this.assistant.on('data', (event) => {
      if (event.type === 'character' || event.type === 'tts') return;
      if (event.type === 'insets' || event.type === 'dynamic_insets') {
        const bottom = event?.insets?.bottom ?? 0;
        document.documentElement.style.setProperty('--bottom-inset', `${bottom}px`);
        return;
      }
      this.dispatchAssistantAction(event.action);
    });

    this.assistant.on('error', (event) => {
      console.warn('assistant error:', event);
    });
  }

  getStateForAssistant() {
    const { status, questionPlan, questionIdx } = this.state;
    if (status === 'welcome') {
      return {
        item_selector: {
          items: [
            { number: 1, id: 'python',        title: 'Python' },
            { number: 2, id: 'classical_ml',  title: 'Classical ML' },
            { number: 3, id: 'deep_learning', title: 'Deep Learning' },
            { number: 4, id: 'nlp_cv',        title: 'NLP и Computer Vision' },
          ],
          ignored_words: ['начни', 'давай', 'выбери', 'запусти', 'тему', 'квиз'],
        },
      };
    }
    if (status === 'length-pick') {
      return {
        item_selector: {
          items: [
            { number: 1, id: '5',   title: '5 вопросов' },
            { number: 2, id: '10',  title: '10 вопросов' },
            { number: 3, id: '20',  title: '20 вопросов' },
            { number: 4, id: 'all', title: 'весь банк' },
          ],
          ignored_words: ['давай', 'хочу', 'возьми', 'вопросов'],
        },
      };
    }
    if (status === 'quiz') {
      const q = questionPlan[questionIdx];
      if (!q) return { item_selector: { items: [] } };
      return {
        item_selector: {
          items: q.options.map((text, idx) => ({
            number: idx + 1,
            id: String(idx),
            title: text,
          })),
          ignored_words: ['вариант', 'ответ', 'номер'],
        },
      };
    }
    return { item_selector: { items: [] } };
  }

  dispatchAssistantAction(action) {
    if (!action) return;
    switch (action.type) {
      case 'CHOOSE_TOPIC':
        return this.applyChooseTopic(action.topic);
      case 'CHOOSE_LENGTH':
        return this.applyChooseLength(action.length);
      case 'PICK_OPTION':
        return this.applyPickOption(action.optionIndex);
      case 'DONT_KNOW':
        return this.applyDontKnow();
      case 'NEXT_QUESTION':
        return this.applyNextQuestion();
      case 'FINISH_QUIZ':
        return this.applyFinishQuiz();
      case 'START_AGAIN':
        return this.applyStartAgain();
      default:
        console.warn('Unknown action type:', action.type);
    }
  }

  applyChooseTopic = (topic) => {
    this.setState((s) => chooseTopic(s, topic));
    speak(this.assistant, `Тема: ${TOPIC_VOICE_LABELS[topic] || topic}. Сколько вопросов пройти?`);
  };

  applyChooseLength = (length) => {
    const parsed = length === 'all' ? 'all' : Number(length);
    this.setState(
      (s) => chooseLength(s, parsed),
      () => this.speakCurrentQuestion(),
    );
  };

  applyPickOption = (optionIndex) => {
    const idx = Number(optionIndex);
    if (!Number.isInteger(idx) || idx < 0 || idx > 3) return;
    this.setState(
      (s) => pickAnswer(s, idx),
      () => this.speakFeedback(),
    );
  };

  applyDontKnow = () => {
    this.setState(
      (s) => markUnknown(s),
      () => this.speakFeedback(),
    );
  };

  applyNextQuestion = () => {
    this.setState(
      (s) => nextQuestion(s),
      () => {
        if (this.state.status === 'quiz') this.speakCurrentQuestion();
        else if (this.state.status === 'results') this.speakResults();
      },
    );
  };

  applyFinishQuiz = () => {
    this.setState(
      (s) => finishTopic(s),
      () => this.speakResults(),
    );
  };

  applyStartAgain = () => {
    this.setState((s) => restart(s));
  };

  applyResetAll = () => {
    this.setState(() => resetAll());
  };

  speakCurrentQuestion() {
    const { questionPlan, questionIdx } = this.state;
    const q = questionPlan[questionIdx];
    if (!q) return;
    const optionsSpeech = q.options
      .map((opt, i) => `Вариант ${i + 1}: ${opt}.`)
      .join(' ');
    speak(this.assistant, `${q.text} ${optionsSpeech}`);
  }

  speakFeedback() {
    const { questionPlan, questionIdx, selectedOption, dontKnow } = this.state;
    const q = questionPlan[questionIdx];
    if (!q) return;
    const isCorrect = !dontKnow && selectedOption === q.correct;
    const lead = dontKnow
      ? 'Правильный ответ:'
      : isCorrect
        ? 'Верно.'
        : 'Неверно.';
    speak(this.assistant, `${lead} ${q.explanation}`);
  }

  speakResults() {
    speak(this.assistant, 'Вот результаты. Скажи «пройти ещё тему» или «начать заново».');
  }

  render() {
    const {
      status,
      currentTopic,
      questionPlan,
      questionIdx,
      selectedOption,
      dontKnow,
      radarScores,
    } = this.state;

    return (
      <ErrorBoundary>
        {status === 'welcome' && (
          <WelcomeView onSelectTopic={this.applyChooseTopic} />
        )}
        {status === 'length-pick' && (
          <LengthPickView onPick={this.applyChooseLength} />
        )}
        {(status === 'quiz' || status === 'feedback') && (
          <QuizView
            topic={currentTopic}
            questionIdx={questionIdx}
            totalQuestions={questionPlan.length}
            question={questionPlan[questionIdx]}
            status={status}
            selectedOption={selectedOption}
            dontKnow={dontKnow}
            onPick={(idx) => this.applyPickOption(idx)}
            onDontKnow={this.applyDontKnow}
            onNext={this.applyNextQuestion}
            onFinish={this.applyFinishQuiz}
          />
        )}
        {status === 'results' && (
          <ResultView
            scores={radarScores}
            onMoreTopic={this.applyStartAgain}
            onResetAll={this.applyResetAll}
          />
        )}
      </ErrorBoundary>
    );
  }
}
```

- [ ] **Step 2: Запустить тесты — проверить что не сломалось**

```bash
yarn test --watchAll=false
```
Ожидаемо: все unit-тесты PASS.

- [ ] **Step 3: Запустить dev-сборку, проверить что компилируется**

```bash
yarn build
```
Ожидаемо: успешный билд (warnings про неиспользуемые файлы из api/ можно игнорировать — удалятся в Task 12).

- [ ] **Step 4: Коммит**

```bash
git add src/App.jsx
git commit -m "refactor(app): переключить App.jsx на quizEngine

App теперь оркестрирует ассистента и quizEngine: каждый action
из .sc мапится на функцию engine, после setState озвучиваем
вопрос/фидбек/итог. Зависимости от backend нет."
```

---

### Task 12: Удалить backend и обвязку

**Files:**
- Delete: папка `backend/`
- Delete: папка `src/api/`
- Delete: `src/services/evaluationDispatch.js`
- Delete: `src/views/InterviewView.jsx`
- Modify: `.env.sample` (корневой)

- [ ] **Step 1: Удалить файлы и папки**

```bash
git rm -r backend/
git rm -r src/api/
git rm src/services/evaluationDispatch.js
git rm src/views/InterviewView.jsx
```

- [ ] **Step 2: Убрать REACT_APP_BACKEND_URL из .env.sample**

Открыть корневой `.env.sample` и удалить строку, где упомянут
`REACT_APP_BACKEND_URL`. Остальные переменные оставить.

- [ ] **Step 3: Прогнать сборку и тесты**

```bash
yarn build
yarn test --watchAll=false
```
Ожидаемо: build PASS, все unit-тесты PASS, никаких висящих импортов.

- [ ] **Step 4: Коммит**

```bash
git add .env.sample
git commit -m "refactor: удалить backend и обвязку HTTP-клиента

backend/ уезжает целиком — приложение теперь полностью клиентское.
Удалены src/api/, evaluationDispatch.js и InterviewView (заменён
QuizView). Переменная REACT_APP_BACKEND_URL убрана из .env.sample."
```

---

### Task 13: Переписать .sc-сценарии под новые intent-ы

**Files:**
- Modify: `smartapp-backend/src/sc/interview.sc`
- Modify: `smartapp-backend/src/js/actions.js`
- Modify: `smartapp-backend/src/js/getters.js`
- Modify: `smartapp-backend/src/js/reply.js`
- Modify: `smartapp-backend/src/entryPoint.sc` (если содержит ссылки на удалённые узлы)
- Update: `scenario-new.zip` в корне (пересобрать архив для загрузки в SmartApp Studio)

- [ ] **Step 1: Прочитать текущие .sc и js, понять структуру**

```bash
cat smartapp-backend/src/sc/interview.sc smartapp-backend/src/entryPoint.sc smartapp-backend/src/js/*.js
```

- [ ] **Step 2: Переписать сценарии под новые actions**

Изменения:
- Удалить узлы для интентов `START_INTERVIEW`, `USER_ANSWER`, `FINISH_ANSWER`,
  `GIVE_UP`, `END_INTERVIEW`, `SHOW_RESULTS`.
- Добавить узлы для `CHOOSE_TOPIC`, `CHOOSE_LENGTH`, `PICK_OPTION`, `DONT_KNOW`,
  `NEXT_QUESTION`, `FINISH_QUIZ`, `START_AGAIN`.
- `CHOOSE_TOPIC` принимает темы как item_selector items (как сейчас START_INTERVIEW).
- `CHOOSE_LENGTH` — числа 1..4 (через item_selector) и алиасы «весь банк»,
  «все вопросы», «целиком».
- `PICK_OPTION` — обработка номеров 1..4 на стадии quiz, выдаёт `optionIndex` 0..3.
- `DONT_KNOW` — фразы «не знаю», «понятия не имею», «дальше без ответа», «пропусти».
- `NEXT_QUESTION` — фразы «дальше», «следующий», «продолжай».
- `FINISH_QUIZ` — фразы «закончить», «хватит», «остановим».
- `START_AGAIN` — фразы «ещё одну тему», «давай ещё», «начать заново».

Узел `Озвучить` (action `SPEAK`) и его JS-обёртку — оставить без изменений.

Конкретные правки точечно по файлам сценариев. Подсказка по структуре есть
в README или в самих файлах. Шаблон для нового узла — копия существующего
`START_INTERVIEW`-узла со сменой `actionId` и формулировок.

- [ ] **Step 3: Пересобрать архив**

```bash
cd smartapp-backend
zip -r ../scenario-new.zip src
cd ..
```

- [ ] **Step 4: Коммит**

```bash
git add smartapp-backend/ scenario-new.zip
git commit -m "refactor(smartapp): сценарии под квиз-формат

Старые intent-ы интервью (USER_ANSWER, FINISH_ANSWER, GIVE_UP,
SHOW_RESULTS) удалены. Добавлены новые: CHOOSE_TOPIC,
CHOOSE_LENGTH, PICK_OPTION, DONT_KNOW, NEXT_QUESTION,
FINISH_QUIZ, START_AGAIN. Архив scenario-new.zip пересобран."
```

---

### Task 14: Обновить CLAUDE.md и README.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: CLAUDE.md**

Внести изменения в `/Users/maksimkuznetsov/WebstormProjects/todo-canvas-app/CLAUDE.md`:

1. Раздел **Project Goal** — переформулировать: «Голосовой квиз по DS-темам
   как SmartApp в экосистеме Сбера. Пользователь голосом или кнопкой выбирает
   тему, длину прохождения и один из четырёх вариантов ответа на каждый
   вопрос. В конце — радар-чарт с долей правильных по темам».
2. Раздел **Stack** — удалить блок про Backend (Python/FastAPI/GigaChat).
   Оставить только фронт.
3. Раздел **Commands** — оставить только yarn-команды; ruff/uvicorn убрать.
4. Раздел **Environment Setup** — убрать упоминания `backend/.env`,
   `GIGACHAT_AUTH_KEY`, `CORS_ORIGINS`, `REACT_APP_BACKEND_URL`.
5. Раздел **External Integrations / Архитектура** — убрать упоминания FastAPI
   и GigaChat. Список actions переписать под новые: `CHOOSE_TOPIC`,
   `CHOOSE_LENGTH`, `PICK_OPTION`, `DONT_KNOW`, `NEXT_QUESTION`,
   `FINISH_QUIZ`, `START_AGAIN`. Действие `SPEAK` оставить.
6. Раздел **Architecture / Data flow** — переписать под новый поток:
   `App` владеет state из `quizEngine`, `getStateForAssistant` динамичен,
   `dispatchAssistantAction` мапит action на функцию engine. Удалить
   упоминания `evaluationDispatch`, `sessionId`, `answerBuffer`.
7. Раздел **Component tree** — заменить `InterviewView` на `LengthPickView`
   и `QuizView`.
8. Раздел **Бэкенд-эндпоинты** — удалить целиком.
9. Раздел **Conventions**:
   - Удалить `session_id`-конвенцию.
   - Удалить `not commit backend/.env`.
   - Добавить: «Банк вопросов — `src/data/questions.js`. Структура одного
     вопроса описана в jsdoc вверху файла. Перед коммитом банка прогнать
     `yarn test src/data/questions.test.js`».
   - Добавить: «Логика квиза — чистый модуль `src/services/quizEngine.js`,
     любое изменение поведения сопровождается тестом».

- [ ] **Step 2: README.md**

Внести изменения в `/Users/maksimkuznetsov/WebstormProjects/todo-canvas-app/README.md`:
1. Описать новый формат (квиз MCQ).
2. Удалить секции про backend/uvicorn/.env-бэка.
3. Обновить раздел структуры папок.
4. Раздел про .env оставить только корневой.

- [ ] **Step 3: Удалить устаревший backend/README.md**

Уже удалён в Task 12 вместе с папкой — этот шаг просто проверка.

```bash
ls backend 2>&1
```
Ожидаемо: `ls: backend: No such file or directory`.

- [ ] **Step 4: Коммит**

```bash
git add CLAUDE.md README.md
git commit -m "docs: актуализировать CLAUDE.md и README.md под квиз

Убраны блоки про FastAPI/GigaChat/backend/.env; описаны новые
actions, quizEngine и формат банка вопросов. Структура папок
синхронизирована с фактическим состоянием."
```

---

### Task 15: Финальный ручной dev-прогон

**Files:** только запуск.

Этот таск — не код, а проверка, что всё собирается и работает.

- [ ] **Step 1: Запустить dev-сервер**

```bash
yarn start
```
Ожидаемо: страница на localhost:3000, в правом нижнем углу панель ассистента
(если в `.env` прописаны `REACT_APP_TOKEN` и `REACT_APP_SMARTAPP`).

- [ ] **Step 2: Прогнать сценарий голосом**

В панели ассистента или встроенным микрофоном:
1. «Запусти Python» → перевод на length-pick.
2. «Пять вопросов» → старт квиза, видим первый вопрос с 4 вариантами.
3. «Первый» → подсветка правильного/неправильного, голос с объяснением.
4. «Дальше» → следующий вопрос. Повторить пару раз.
5. «Не знаю» на одном из вопросов — фидбек должен показать правильный.
6. «Закончить» — переход на results.
7. На results — «Пройти ещё тему» возвращает на welcome, радар по Python остаётся.

- [ ] **Step 3: Прогнать кликами в development-окружении**

Без голоса (web-speech иногда не отвечает в dev) — тот же сценарий через
клики по карточкам и кнопкам.

- [ ] **Step 4: Если что-то сломано — фиксить, иначе финальный коммит**

Если фиксов нет — просто проверить состояние:
```bash
git status
```
Ожидаемо: clean working tree.

---

## Notes

**Контент-этап (вне плана).** После задач 1–15 банк вопросов наполняется
полностью: ~35 MCQ на тему. Это отдельный коммит (или серия коммитов вида
`content(quiz): добавить вопросы по python`) — не часть рефакторинга кода.
Каждый блок проходит `yarn test src/data/questions.test.js` перед коммитом.

**`.env` пользователя.** Корневой `.env` не коммитится; пользователю нужно
самому удалить из него `REACT_APP_BACKEND_URL`, если он там был. В `.env.sample`
эта переменная уже отсутствует после Task 12.
