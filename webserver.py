from flask import Flask, render_template, request
import json
import shlex


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
    line = request.args.get('line')
    tokens = shlex.split(line.lower())
    try:
        command = tokens.pop(0)
        match command:
            case "restart":
                result = f"{roonservicemanager.restart_core_service()}"
            case "status":
                result = {'token':roonservicemanager.roon.token,'host':roonservicemanager.roon.host, \
                         'port':roonservicemanager.roon.port,'core_id':roonservicemanager.roon.core_id \
                         ,'core_name':roonservicemanager.roon.core_name \
                         ,'last_ping':roonservicemanager.lastping}
                result = json.dumps(result, indent=4)
            case "zones":
                result = f"{json.dumps(roonservicemanager.roon.zones, indent=4)}"
            case "log":
                result = f"{roonservicemanager.getLog()}"
            case "settings":
                result = f"{json.dumps(roonservicemanager.settings, indent=4)}"
            case _:
                result = f"{{{command}}} not implemented."
    except Exception as exception:
        result = f"error running command line {line}"
    finally:
        return result
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
