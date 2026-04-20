theme: /

    state: ДобавлениеЭлемента
        q!: (~добавить|~установить|запиши|поставь|закинь|~напомнить) 
            [~напоминание|~заметка|~задание|~задача]
            $AnyText::anyText
            
        random:
            a: Добавлено!
            a: Записано!
            
        script:
            log('addNote: context: ' + JSON.stringify($context))
            addNote($parseTree._anyText, $context);
            addSuggestions(["Добавь 'купить машину'"], $context);