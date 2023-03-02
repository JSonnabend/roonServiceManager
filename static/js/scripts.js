$(function() {
    var empty = {
        options: [],
        args: []
    };
    var commands = ['restart', 'status', 'zones &#91;zone_name|zone_number&#93;', 'list &#91;zones&#93;', 'log', 'ping', 'settings', 'cls', 'help'];



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
            this.echo('available commands are\n\t[[b;white;]' + commands.join('\n\t') + ']')
         }
       },
      function(line, term) {
        this.echo($.get('/terminal', {line: line}))
      }],
      {
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