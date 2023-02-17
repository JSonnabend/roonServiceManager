$(function() {
    var empty = {
        options: [],
        args: []
    };
    var commands = ['restart', 'status', 'zones', 'log', 'settings', 'help', 'echo', 'cls'];



    $('#terminal').terminal([
       {echo: function(line){
            this.echo(line)
         }
       },
       {cls: function(line){
             this.clear()
             this.greetings = 'RoonServiceManager Terminal'
         }
       },
       {help: function(line){
            this.echo('available commands are [[b;white;]' + commands.join(' ') + ']')
         }
       },
      function(line, term) {
        this.echo($.get('/terminal', {line: line}))
      }], {
        greetings: 'RoonServiceManager Terminal',
        autocompleteMenu: true,
        echoCommand: true,
        completion: function(param1, callback) {
            var line = $('.cmd-cursor-line').text()
            var tokens = line.split("\xa0")
            var command = tokens.shift()
            var params = tokens
            callback(commands);
    }
    });
});