function chooseTopic(topic, context) {
    addAction({
        type: "CHOOSE_TOPIC",
        topic: topic
    }, context);
}

function chooseLength(length, context) {
    addAction({
        type: "CHOOSE_LENGTH",
        length: length
    }, context);
}

function pickOption(optionIndex, context) {
    addAction({
        type: "PICK_OPTION",
        optionIndex: optionIndex
    }, context);
}

function dontKnow(context) {
    addAction({
        type: "DONT_KNOW"
    }, context);
}

function nextQuestion(context) {
    addAction({
        type: "NEXT_QUESTION"
    }, context);
}

function finishQuiz(context) {
    addAction({
        type: "FINISH_QUIZ"
    }, context);
}

function startAgain(context) {
    addAction({
        type: "START_AGAIN"
    }, context);
}
