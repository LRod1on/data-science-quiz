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
