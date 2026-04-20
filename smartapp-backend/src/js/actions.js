function startInterview(topic, context) {
    addAction({
        type: "START_INTERVIEW",
        topic: topic
    }, context);
}

function userAnswer(text, context) {
    addAction({
        type: "USER_ANSWER",
        text: text
    }, context);
}

function nextQuestion(context) {
    addAction({
        type: "NEXT_QUESTION"
    }, context);
}

function giveUp(context) {
    addAction({
        type: "GIVE_UP"
    }, context);
}

function endInterview(context) {
    addAction({
        type: "END_INTERVIEW"
    }, context);
}

function showResults(context) {
    addAction({
        type: "SHOW_RESULTS"
    }, context);
}
