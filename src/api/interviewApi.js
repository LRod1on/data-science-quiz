const BASE_URL = process.env.REACT_APP_BACKEND_URL ?? 'http://localhost:8000';

const TIMEOUT_MS = 35000;

async function apiFetch(path, body) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Запрос превысил время ожидания (35 сек)');
    }
    throw new Error(`Сеть недоступна: ${err.message}`);
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Ошибка сервера ${response.status}: ${text}`);
  }

  return response.json();
}

export async function startInterview(sessionId, topic) {
  return apiFetch('/start', { session_id: sessionId, topic });
}

export async function evaluateAnswer(sessionId, text) {
  return apiFetch('/evaluate', { session_id: sessionId, text });
}

export async function skipQuestion(sessionId) {
  return apiFetch('/skip', { session_id: sessionId });
}

export async function finishInterview(sessionId) {
  return apiFetch('/finish', { session_id: sessionId });
}
