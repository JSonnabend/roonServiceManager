from flask import Flask, render_template, request, Response
import json
import shlex, argparse

webserver = Flask(__name__)
roonservicemanager = None
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--indent', type=int, default=4)

def run(host="0.0.0.0", port="18007"):
    webserver.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    webserver.run(host, port)

@webserver.route("/test")
def test():
    result = f"{roonservicemanager.roon.zone_by_name('Saint Zoey')}"
    return Response(response=result, status=200, mimetype="application/json")
    pass

@webserver.route("/restart")
def restart(indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        result = f"{roonservicemanager.restart_core_service()}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/status")
def status(indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        result = {'token': roonservicemanager.roon.token,
                  'host': roonservicemanager.roon.host,
                  'port': roonservicemanager.roon._port,
                  'core_id': roonservicemanager.roon.core_id ,
                  'core_name': roonservicemanager.roon.core_name ,
                  'last_ping': roonservicemanager.lastping}
        result = json.dumps(result, indent=indent)
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/list")
@webserver.route("/list/<list_type>")
def _list(list_type='', indent = 0):
    if list_type == '':
        return "list_type missing"
    else:
        match list_type.lower():
            case "zones":
                result = ""
                zones = roonservicemanager.roon.zones
                for index, zone in enumerate(zones.values()):
                    result = result + f"[{index}]\t{zone['display_name']}\n"
                result = result.strip()
            case _:
                return f"list_type {list_type} not defined"
        return Response(response=result, status=200, mimetype="text/plain")


@webserver.route("/zones")
@webserver.route("/zones/<zone>") #zone is index (from list zones) or name
def zones(zone='', indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        if request.args.get('indent', '') != '':
            indent = int(request.args.get('indent')) if request.args.get('indent').isdigit() else 0
        #return results for specified zone
        if zone == '':
            result = f"{json.dumps(roonservicemanager.roon.zones, indent=indent)}"
        elif zone.isdigit():
            zones = roonservicemanager.roon.zones.values()
            if int(zone) < len(zones) and int(zone) > -1:
                zone = list(zones)[int(zone)]
                result = f"{json.dumps(zone, indent=indent)}"
            else:
                return f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
        else:
            result = roonservicemanager.roon.zone_by_name(zone)
            if result:
                result = f"{json.dumps(result, indent=indent)}"
            else:
                return f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"

        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/ping")
def ping(indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        result = f"{json.dumps(roonservicemanager.ping_core(), indent=indent)}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/getlog")
def getlog(indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        result = f"{roonservicemanager.getLog()}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/settings")
def settings(indent = 0):
    if roonservicemanager is None:
        return "roonservicemanager not initialized"
    else:
        result = f"{json.dumps(roonservicemanager.settings, indent=indent)}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/terminal")
def terminal():
    line = request.args.get('line')
    tokens = shlex.split(line.lower())
    result = ""
    try:
        command = tokens.pop(0)
        args, unknown = parser.parse_known_args(tokens)
        indent = args.indent
        match command:
            case "restart":
                result = restart(indent=indent)
            case "status":
                result = status(indent=indent)
            case _ as _command if _command=="zones" or _command=="zone":
                if len(tokens) < 1:
                    result = zones(indent=indent)
                else:
                    result = zones(zone=tokens[0], indent=indent)
            case "ping":
                result = ping(indent=indent)
            case "log":
                result = getlog(indent=indent)
            case "settings":
                result = settings(indent=indent)
            case "list":
                if len(tokens) < 1:
                    result = _list(indent=indent)
                else:
                    result = _list(list_type=tokens[0], indent=indent)
            case _:
                result = f"{{{command}}} not implemented."
        # return json data if it exists, else return plain text result string
        try:
            result = result.data
        except:
            result = result
    except Exception as exception:
        result = f"error running command line {line}"
    finally:
        return result
@webserver.route("/")
def index():
    return render_template("index.html")


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
