theme: /

    # --- выбор темы ---

    state: ТемаPython
        q!: (выбери|давай|хочу|начни|запусти|проверь меня) [~квиз|~тему] [по] (питон|python|пайтон|питону|пайтону)
        q!: (питон|python|пайтон)
        q!: (первый|первая|номер один|вариант один|1) [~тему|~тема]
        script:
            log('quiz: ТемаPython')
            chooseTopic("python", $context)

    state: ТемаClassicalML
        q!: (выбери|давай|хочу|начни|запусти|проверь меня) [~квиз|~тему] [по] (классический ml|classical ml|классическое мл|классический мл|классическое машинное обучение)
        q!: (классический ml|classical ml|классический мл)
        q!: (второй|вторая|номер два|вариант два|2) [~тему|~тема]
        script:
            log('quiz: ТемаClassicalML')
            chooseTopic("classical_ml", $context)

    state: ТемаDeepLearning
        q!: (выбери|давай|хочу|начни|запусти|проверь меня) [~квиз|~тему] [по] (deep learning|дип лёрнинг|глубокое обучение|нейросети|нейронные сети)
        q!: (deep learning|дип лёрнинг|глубокое обучение)
        q!: (третий|третья|номер три|вариант три|3) [~тему|~тема]
        script:
            log('quiz: ТемаDeepLearning')
            chooseTopic("deep_learning", $context)

    state: ТемаNLPCV
        q!: (выбери|давай|хочу|начни|запусти|проверь меня) [~квиз|~тему] [по] (nlp|нлп|обработка текста|обработка естественного языка|компьютерное зрение|computer vision|nlp и cv|нлп и cv)
        q!: (nlp|нлп|обработка текста|computer vision)
        q!: (четвёртый|четвёртая|номер четыре|вариант четыре|4) [~тему|~тема]
        script:
            log('quiz: ТемаNLPCV')
            chooseTopic("nlp_cv", $context)

    # --- выбор длины ---

    state: Длина5
        q!: (пять|5) [~вопросов|~вопроса]
        q!: (короткий|коротко) [~квиз]
        script:
            log('quiz: Длина5')
            chooseLength(5, $context)

    state: Длина10
        q!: (десять|10) [~вопросов]
        script:
            log('quiz: Длина10')
            chooseLength(10, $context)

    state: Длина20
        q!: (двадцать|20) [~вопросов]
        q!: (длинный|длинно) [~квиз]
        script:
            log('quiz: Длина20')
            chooseLength(20, $context)

    state: ДлинаВесьБанк
        q!: (весь банк|все вопросы|целиком|максимум|все)
        script:
            log('quiz: ДлинаВесьБанк')
            chooseLength("all", $context)

    # --- выбор варианта ответа ---

    state: Вариант1
        q!: (первый|первая|первое|номер один|вариант один|вариант первый|1) [~ответ]
        script:
            log('quiz: Вариант1')
            pickOption(0, $context)

    state: Вариант2
        q!: (второй|вторая|второе|номер два|вариант два|вариант второй|2) [~ответ]
        script:
            log('quiz: Вариант2')
            pickOption(1, $context)

    state: Вариант3
        q!: (третий|третья|третье|номер три|вариант три|вариант третий|3) [~ответ]
        script:
            log('quiz: Вариант3')
            pickOption(2, $context)

    state: Вариант4
        q!: (четвёртый|четвёртая|четвёртое|номер четыре|вариант четыре|вариант четвёртый|4) [~ответ]
        script:
            log('quiz: Вариант4')
            pickOption(3, $context)

    # --- управление прохождением ---

    state: НеЗнаю
        q!: (не знаю|понятия не имею|без понятия|пропусти|пропустить|пас)
        script:
            log('quiz: НеЗнаю')
            dontKnow($context)

    state: СледующийВопрос
        q!: (~следующий ~вопрос|дальше|продолжай|продолжим|вперёд)
        script:
            log('quiz: СледующийВопрос')
            nextQuestion($context)

    state: ЗакончитьКвиз
        q!: (закончи|закончим|закончить|хватит|стоп|конец|завершить|выход|выйти|остановим)
        script:
            log('quiz: ЗакончитьКвиз')
            finishQuiz($context)

    state: ЕщёТему
        q!: (ещё одну тему|пройти ещё тему|ещё тему|давай ещё|следующая тема|новая тема)
        q!: (начать заново|заново|сначала|по новой)
        script:
            log('quiz: ЕщёТему')
            startAgain($context)

    # --- TTS-озвучка от фронта ---

    state: Озвучить
        event!: SPEAK
        script:
            log('quiz: Озвучить: context: ' + JSON.stringify($context))
            var eventData = $context && $context.request && $context.request.data && $context.request.data.eventData || {}
            log('quiz: Озвучить: eventData: ' + JSON.stringify(eventData))
            $reactions.answer({
                "value": eventData.text
            })
