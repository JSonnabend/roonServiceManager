$(function() {
    $('#terminal').terminal(function(command, term) {
        return $.get('/terminal', {command: command});
    }, {
        greetings: 'RoonServiceManager Terminal'
    });
});