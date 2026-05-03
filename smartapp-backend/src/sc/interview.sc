theme: /

    state: НачатьПитон
        q!: (начни|начнём|давай|хочу|запусти|выбери|проверь меня) [~интервью] [по] (питон|python|пайтон|питону|пайтону)
        q!: (питон|python|пайтон)
        script:
            log('interview: НачатьПитон')
            startInterview("python", $context)
        a: Начинаем интервью по Python.

    state: НачатьClassicalML
        q!: (начни|начнём|давай|хочу|запусти|выбери|проверь меня) [~интервью] [по] (классический ml|classical ml|классическое мл|классический мл|классическое машинное обучение)
        q!: (классический ml|classical ml)
        script:
            log('interview: НачатьClassicalML')
            startInterview("classical_ml", $context)
        a: Начинаем интервью по Classical ML.

    state: НачатьDeepLearning
        q!: (начни|начнём|давай|хочу|запусти|выбери|проверь меня) [~интервью] [по] (deep learning|дип лёрнинг|глубокое обучение|нейросети|нейронные сети)
        q!: (deep learning|дип лёрнинг|глубокое обучение)
        script:
            log('interview: НачатьDeepLearning')
            startInterview("deep_learning", $context)
        a: Начинаем интервью по Deep Learning.

    state: НачатьNLPCV
        q!: (начни|начнём|давай|хочу|запусти|выбери|проверь меня) [~интервью] [по] (nlp|нлп|обработка текста|обработка естественного языка|компьютерное зрение|computer vision|nlp и cv|нлп и cv)
        q!: (nlp|нлп|обработка текста|computer vision)
        script:
            log('interview: НачатьNLPCV')
            startInterview("nlp_cv", $context)
        a: Начинаем интервью по NLP и Computer Vision.

    state: СледующийВопрос
        q!: (~следующий ~вопрос|дальше|пропусти|пропустить|пропускаю|следующее|вперёд)
        script:
            log('interview: СледующийВопрос')
            nextQuestion($context)
        a: Хорошо, следующий вопрос.

    state: Сдаюсь
        q!: (сдаюсь|пас|не знаю|сдаться|капитулирую)
        script:
            log('interview: Сдаюсь')
            giveUp($context)
        a: Понятно, идём дальше.

    state: ЗакончилОтвет
        q!: (готово|это всё|ответил|ответила|закончил|закончила|закончил ответ|конец ответа|ответ окончен|это весь ответ|больше нечего сказать|больше нечего добавить|на этом всё)
        script:
            log('interview: ЗакончилОтвет')
            finishAnswer($context)
        a: Принял.

    state: ДайПодумать
        q!: (дай подумать|дайте подумать|надо подумать|подожди|подождите|погоди|погодите|секундочку)
        script:
            log('interview: ДайПодумать')
        a: Хорошо, не спешу.

    state: КонецИнтервью
        q!: (закончим|закончить|хватит|стоп|конец|завершить|выход|выйти)
        script:
            log('interview: КонецИнтервью')
            endInterview($context)
        a: Завершаю интервью.

    state: ПоказатьРезультаты
        q!: (покажи результаты|показать результаты|результаты|итоги|мои результаты|покажи итоги)
        script:
            log('interview: ПоказатьРезультаты')
            showResults($context)

    state: ОтветПользователя
        q!: $AnyText::anyText
        script:
            log('interview: ОтветПользователя: ' + $parseTree._anyText)
            userAnswer($parseTree._anyText, $context)

    state: Озвучить
        event!: SPEAK
        script:
            log('interview: Озвучить: context: ' + JSON.stringify($context))
            var eventData = $context && $context.request && $context.request.data && $context.request.data.eventData || {}
            log('interview: Озвучить: eventData: ' + JSON.stringify(eventData))
            $reactions.answer({
                "value": eventData.text
            })
