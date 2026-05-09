import React from 'react';

import './App.css';
import { ErrorBoundary } from './components/ErrorBoundary';
import { WelcomeView } from './views/WelcomeView';
import { InterviewView } from './views/InterviewView';
import { ResultView } from './views/ResultView';
import {
  startInterview,
  evaluateAnswer,
  skipQuestion,
  finishInterview,
} from './api/interviewApi';
import { createAssistantInstance, speak } from './services/assistant';

export class App extends React.Component {
  constructor(props) {
    super(props);

    this.sessionId = crypto.randomUUID();

    this.state = {
      status: 'welcome',       // 'welcome' | 'interview' | 'results'
      currentTopic: null,      // ключ темы из constants/topics или null на welcome
      questionIndex: 0,        // 1..5 во время интервью, 0 на welcome
      questionText: '',
      answerBuffer: '',        // фрагменты речи, склеенные пробелами; чистится при FINISH_ANSWER
      isLoading: false,
      radarScores: {
        python: null,
        classical_ml: null,
        deep_learning: null,
        nlp_cv: null,
      },
      lastError: null,
    };

    this.assistant = createAssistantInstance(() => this.getStateForAssistant());

    this.assistant.on('data', (event) => {
      if (event.type === 'character' || event.type === 'tts') {
        return;
      }
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
    if (this.state.status === 'welcome') {
      return {
        item_selector: {
          items: [
            { number: 1, id: 'python',        title: 'Python' },
            { number: 2, id: 'classical_ml',  title: 'Classical ML' },
            { number: 3, id: 'deep_learning', title: 'Deep Learning' },
            { number: 4, id: 'nlp_cv',        title: 'NLP и Computer Vision' },
          ],
          ignored_words: ['начни', 'давай', 'выбери', 'запусти', 'проверь', 'интервью', 'по', 'тему'],
        },
      };
    }
    return { item_selector: { items: [] } };
  }

  dispatchAssistantAction(action) {
    if (!action) return;
    switch (action.type) {
      case 'START_INTERVIEW':
        return this.handleStartInterview(action.topic);
      case 'USER_ANSWER':
        return this.handleUserAnswer(action.text);
      case 'FINISH_ANSWER':
        return this.handleFinishAnswer();
      case 'NEXT_QUESTION':
      case 'GIVE_UP':
        return this.handleNextQuestion();
      case 'END_INTERVIEW':
        return this.handleEndOrFinish();
      case 'SHOW_RESULTS':
        return this.handleShowResults();
      default:
        console.warn('Unknown action type:', action.type);
    }
  }

  _handleEvaluateResponse(data) {
    const { action, feedback, next_question: nextQ, question_index, final_scores } = data;

    if (action === 'TOPIC_COMPLETE') {
      this.setState((prev) => ({
        status: 'results',
        isLoading: false,
        lastError: null,
        answerBuffer: '',
        radarScores: {
          ...prev.radarScores,
          [prev.currentTopic]: final_scores?.[prev.currentTopic] ?? null,
        },
      }));
      speak(this.assistant, feedback);
      return;
    }

    if (action === 'NEXT_QUESTION') {
      this.setState({
        questionText: nextQ,
        questionIndex: question_index,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      });
      speak(this.assistant, feedback);
      return;
    }

    if (action === 'CONTINUE') {
      // LLM попросила уточнить — feedback и есть текст уточняющего вопроса.
      this.setState({
        questionText: feedback,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      });
      speak(this.assistant, feedback);
      return;
    }

    // ERROR или неизвестный action — буфер не чистим, чтобы пользователь
    // мог повторить «готово» с тем же ответом.
    this.setState({ isLoading: false, lastError: feedback || 'Ошибка сервера' });
    speak(this.assistant, feedback);
  }

  async handleStartInterview(topic) {
    if (this.state.isLoading || this.state.status !== 'welcome') return;
    this.setState({
      status: 'interview',
      currentTopic: topic,
      questionIndex: 1,
      questionText: '',
      answerBuffer: '',
      isLoading: true,
      lastError: null,
    });
    try {
      const data = await startInterview(this.sessionId, topic);
      this.setState({ questionText: data.question, isLoading: false });
      speak(this.assistant, data.pronounce_text);
    } catch (err) {
      this.setState({ status: 'welcome', isLoading: false, lastError: err.message });
    }
  }

  handleUserAnswer(text) {
    if (this.state.status !== 'interview' || this.state.isLoading) return;
    // Защита: initPhrase из createSmartappDebugger иногда прилетает с задержкой
    // и попадает в USER_ANSWER. Команды запуска начинаются с «запусти/открой/вруби» —
    // фильтруем их, чтобы они не попали в буфер ответа.
    if (/^(запусти|открой|вруби)\s/i.test(text)) return;
    const fragment = (text || '').trim();
    if (!fragment) return;
    this.setState((prev) => ({
      answerBuffer: prev.answerBuffer ? `${prev.answerBuffer} ${fragment}` : fragment,
      lastError: null,
    }));
  }

  async handleFinishAnswer() {
    if (this.state.status !== 'interview' || this.state.isLoading) return;
    const buffered = this.state.answerBuffer.trim();
    if (!buffered) {
      speak(this.assistant, 'Я не услышал ответ. Скажите его и затем «готово».');
      return;
    }
    this.setState({ isLoading: true, lastError: null });
    try {
      const data = await evaluateAnswer(this.sessionId, buffered);
      this._handleEvaluateResponse(data);
    } catch (err) {
      this.setState({ isLoading: false, lastError: err.message });
    }
  }

  async handleNextQuestion() {
    if (this.state.isLoading) return;
    this.setState({ isLoading: true, lastError: null, answerBuffer: '' });
    try {
      const data = await skipQuestion(this.sessionId);
      this._handleEvaluateResponse(data);
    } catch (err) {
      this.setState({ isLoading: false, lastError: err.message });
    }
  }

  async handleFinishInterview() {
    if (this.state.status !== 'interview' || this.state.isLoading) return;
    this.setState({ isLoading: true, lastError: null, answerBuffer: '' });
    try {
      const data = await finishInterview(this.sessionId);
      this._handleEvaluateResponse(data);
    } catch (err) {
      this.setState({ isLoading: false, lastError: err.message });
    }
  }

  handleEndInterview() {
    this.setState({
      status: 'welcome',
      currentTopic: null,
      questionIndex: 0,
      questionText: '',
      answerBuffer: '',
      isLoading: false,
      lastError: null,
    });
  }

  handleEndOrFinish() {
    if (this.state.status === 'interview') return this.handleFinishInterview();
    if (this.state.status === 'results') return this.handleEndInterview();
  }

  handleShowResults() {
    if (this.state.status === 'interview') return this.handleFinishInterview();
  }

  render() {
    const {
      status,
      currentTopic,
      questionIndex,
      questionText,
      answerBuffer,
      isLoading,
      radarScores,
      lastError,
    } = this.state;

    const isListening = status === 'interview' && !isLoading;

    return (
      <ErrorBoundary>
        {status === 'welcome' && (
          <WelcomeView onSelectTopic={(topic) => this.handleStartInterview(topic)} />
        )}
        {status === 'interview' && (
          <InterviewView
            topic={currentTopic}
            questionIndex={questionIndex}
            questionText={questionText}
            answerBuffer={answerBuffer}
            isLoading={isLoading}
            isListening={isListening}
            lastError={lastError}
            onSubmit={() => this.handleFinishAnswer()}
            onNext={() => this.handleNextQuestion()}
            onFinish={() => this.handleFinishInterview()}
          />
        )}
        {status === 'results' && (
          <ResultView
            scores={radarScores}
            onRestart={() => this.handleEndInterview()}
          />
        )}
      </ErrorBoundary>
    );
  }
}
