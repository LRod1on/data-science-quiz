theme: /

    state: УдалениеЭлемента
        q!: (~удалить|удали)
            $AnyText::anyText
        
        script:
            log('deleteNote: context: ' + JSON.stringify($context))
            var item_id = get_id_by_selected_item(get_request($context));
            deleteNote(item_id,$context);
        
        a: Удаляю