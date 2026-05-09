// Декодирование ответа /evaluate (а также /skip и /finish — у них тот же формат).
// Чистая функция, чтобы класс App не возил setState внутри switch'а — так
// логика читается линейно и при желании покрывается юнит-тестами без React.

/**
 * @param {import('../api/interviewApi').EvaluateResponse} data
 * @param {string|null} currentTopic — нужен только для записи балла в радар при TOPIC_COMPLETE.
 * @returns {{ stateUpdate: object | ((prev: object) => object), speechText: string }}
 */
export function decodeEvaluateResponse(data, currentTopic) {
  const { action, feedback, next_question: nextQ, question_index, final_scores } = data;

  if (action === 'TOPIC_COMPLETE') {
    return {
      stateUpdate: (prev) => ({
        status: 'results',
        isLoading: false,
        lastError: null,
        answerBuffer: '',
        radarScores: {
          ...prev.radarScores,
          [currentTopic]: final_scores?.[currentTopic] ?? null,
        },
      }),
      speechText: feedback,
    };
  }

  if (action === 'NEXT_QUESTION') {
    return {
      stateUpdate: {
        questionText: nextQ,
        questionIndex: question_index,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      },
      speechText: feedback,
    };
  }

  if (action === 'CONTINUE') {
    // Уточняющий вопрос от LLM: feedback и есть текст уточнения.
    return {
      stateUpdate: {
        questionText: feedback,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      },
      speechText: feedback,
    };
  }

  // ERROR или неизвестный action — буфер не чистим, чтобы пользователь
  // мог повторить «готово» с тем же ответом.
  return {
    stateUpdate: { isLoading: false, lastError: feedback || 'Ошибка сервера' },
    speechText: feedback,
  };
}
