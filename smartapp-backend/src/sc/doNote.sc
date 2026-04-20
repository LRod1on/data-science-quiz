theme: /

    state: ВыполнениеЭлемента
        q!: [я] (выполни|выполнил|сделал)
            $AnyText::anyText
            
        script:
            log('doNote: context: ' + JSON.stringify($context))
            var item_id = get_id_by_selected_item(get_request($context));
            doneNote(item_id,$context);
            
        random: 
            a: Молодец!
            a: Красавичк!
            a: Супер!
        