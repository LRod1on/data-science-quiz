require: slotfilling/slotFilling.sc
  module = sys.zb-common

# Подключение javascript обработчиков
require: js/getters.js
require: js/reply.js
require: js/actions.js

# Подключение сценарных файлов
require: sc/interview.sc


patterns:
    $AnyText = $nonEmptyGarbage

theme: /
    state: Start
        # При запуске приложения с кнопки прилетит сообщение /start.
        q!: $regex</start>
        # При запуске с голоса или через createSmartappDebugger (initPhrase) прилетит
        # «Запусти <имя приложения>». Ловим любой вариант, чтобы не провалиться в Fallback.
        q!: (запусти | открой | вруби) $AnyText
        a: Привет! Это квиз по Data Science. Выбери тему: Python, Classical ML, Deep Learning или NLP и Computer Vision.

    state: Fallback
        event!: noMatch
        script:
            log('entryPoint: Fallback: context: ' + JSON.stringify($context))
        a: Я не понимаю
