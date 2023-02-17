$(function() {
    var empty = {
        options: [],
        args: []
    };
    var commands = ['restart', 'status', 'zones', 'log', 'settings', 'help'];

    $('#terminal').terminal([
       {echo: function(line){
         this.echo(line)
         }
       },
      function(line, term) {
        this.echo($.get('/terminal', {line: line}))
      }], {
        greetings: 'RoonServiceManager Terminal',
        autocompleteMenu: true,
        completion: commands
    });
});