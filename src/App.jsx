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
