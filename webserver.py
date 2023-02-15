from flask import Flask, render_template
import json
webserver = Flask(__name__)
roonservicemanager = None

def run(host="0.0.0.0", port="8007"):
    webserver.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    webserver.run(host, port)

@webserver.route("/restart")
def hello_world():
    return json.dumps({'message': 'hello'})

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
