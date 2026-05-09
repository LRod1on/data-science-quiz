// Тонкая обёртка над @salutejs/client — единственная точка соприкосновения
// с экосистемой Сбера. Вынесена из App.jsx, чтобы компонент не знал
// про различия dev/prod и про детали SPEAK-action.

import { createAssistant, createSmartappDebugger } from '@salutejs/client';

/**
 * Создать инстанс ассистента.
 * В development подключается createSmartappDebugger (нужны REACT_APP_TOKEN и
 * REACT_APP_SMARTAPP). В production — createAssistant, который уже работает
 * в окружении SberBox/Салют.
 *
 * @param {() => object} getState — возвращает item_selector для голосовых команд.
 * @returns ассистент @salutejs/client.
 */
export function createAssistantInstance(getState) {
  if (process.env.NODE_ENV === 'development') {
    return createSmartappDebugger({
      token: process.env.REACT_APP_TOKEN ?? '',
      initPhrase: `Запусти ${process.env.REACT_APP_SMARTAPP}`,
      getState,
      nativePanel: {
        defaultText: 'начни интервью по питону',
        screenshotMode: false,
        tabIndex: -1,
      },
    });
  }
  return createAssistant({ getState });
}

/**
 * Озвучить текст. В проде — через TTS Салюта (action SPEAK обрабатывается
 * в .sc-сценарии). В dev — через Web Speech API, потому что в режиме
 * createSmartappDebugger TTS прода недоступно.
 *
 * @param {object} assistant — инстанс из createAssistantInstance.
 * @param {string} text
 */
export function speak(assistant, text) {
  if (!text) return;

  if (process.env.NODE_ENV === 'development') {
    window.speechSynthesis?.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ru-RU';
    window.speechSynthesis?.speak(utterance);
    return;
  }

  try {
    const unsubscribe = assistant.sendData(
      { action: { action_id: 'SPEAK' }, eventData: { text } },
      () => {
        if (typeof unsubscribe === 'function') unsubscribe();
      }
    );
  } catch (err) {
    console.warn('assistant.sendData(SPEAK) failed:', err);
  }
}
