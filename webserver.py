from flask import Flask, render_template, request
import json
webserver = Flask(__name__)
roonservicemanager = None

def run(host="0.0.0.0", port="8007"):
    webserver.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    webserver.run(host, port)

@webserver.route("/restart")
def restart():
    roonservicemanager.restart_core_service()
    return "restarting roon server"

@webserver.route("/terminal")
def terminal():
    command = request.args.get('command')
    return f"you sent command {command}"
@webserver.route("/")
def index():
    return render_template("index.html")
    pass


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
