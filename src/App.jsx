import React from 'react';
import { createAssistant, createSmartappDebugger } from '@salutejs/client';

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

const initializeAssistant = (getState) => {
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
  } else {
    return createAssistant({ getState });
  }
};

export class App extends React.Component {
  constructor(props) {
    super(props);
    console.log('constructor');

    this.sessionId = crypto.randomUUID();

    this.state = {
      status: 'welcome',       // 'welcome' | 'interview' | 'results'
      currentTopic: null,      // 'python' | 'classical_ml' | 'deep_learning' | 'nlp_cv'
      questionIndex: 0,        // 0-based
      questionText: '',
      answerBuffer: '',        // accumulated user fragments until FINISH_ANSWER
      isLoading: false,
      radarScores: {
        python: null,
        classical_ml: null,
        deep_learning: null,
        nlp_cv: null,
      },
      lastError: null,
    };

    this.assistant = initializeAssistant(() => this.getStateForAssistant());

    this.assistant.on('data', (event) => {
      console.log('assistant.on(data)', event);
      if (event.type === 'character') {
        console.log(`assistant.on(data): character: "${event?.character?.id}"`);
      } else if (event.type === 'insets' || event.type === 'dynamic_insets') {
        const bottom = event?.insets?.bottom ?? 0;
        document.documentElement.style.setProperty('--bottom-inset', `${bottom}px`);
      } else {
        const { action } = event;
        this.dispatchAssistantAction(action);
      }
    });

    this.assistant.on('start', (event) => {
      console.log('assistant.on(start)', event, this.assistant.getInitialData());
    });

    this.assistant.on('command', (event) => {
      console.log('assistant.on(command)', event);
    });

    this.assistant.on('error', (event) => {
      console.log('assistant.on(error)', event);
    });

    this.assistant.on('tts', (event) => {
      console.log('assistant.on(tts)', event);
    });
  }

  componentDidMount() {
    console.log('componentDidMount');
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
    console.log('dispatchAssistantAction', action);
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
        return this.handleEndInterview();
      case 'SHOW_RESULTS':
        return this.handleShowResults();
      default:
        console.warn('Unknown action type:', action.type);
    }
  }

  _speakText(text) {
    if (!text) return;
    if (process.env.NODE_ENV === 'development') {
      window.speechSynthesis?.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = 'ru-RU';
      window.speechSynthesis?.speak(utt);
      return;
    }
    try {
      const unsubscribe = this.assistant.sendData(
        { action: { action_id: 'SPEAK' }, eventData: { text } },
        (data) => {
          console.log('sendData SPEAK ack:', data);
          if (typeof unsubscribe === 'function') unsubscribe();
        }
      );
    } catch (err) {
      console.warn('_speakText sendData error:', err);
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
      this._speakText(feedback);
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
      this._speakText(feedback);
      return;
    }

    if (action === 'CONTINUE') {
      // LLM asked a clarifying question — feedback IS the clarifying question
      this.setState({
        questionText: feedback,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      });
      this._speakText(feedback);
      return;
    }

    // ERROR or unknown action — keep the buffer so the user can retry "готово"
    this.setState({ isLoading: false, lastError: feedback || 'Ошибка сервера' });
    this._speakText(feedback);
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
      this._speakText(data.pronounce_text);
    } catch (err) {
      this.setState({ status: 'welcome', isLoading: false, lastError: err.message });
    }
  }

  handleUserAnswer(text) {
    if (this.state.status !== 'interview' || this.state.isLoading) return;
    // Guard against the createSmartappDebugger initPhrase arriving late and being
    // misrouted to USER_ANSWER. Launch phrases start with "запусти/открой/вруби".
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
      this._speakText('Я не услышал ответ. Скажите его и затем «готово».');
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
    if (this.state.isLoading) return;
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

  handleShowResults() {
    this.setState({ status: 'results' });
  }

  render() {
    console.log('render');
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
