from flask import Flask, render_template, request, Response
import json
import shlex, argparse
import rooncommands

webserver = Flask(__name__)
roonservicemanager = None
parser = argparse.ArgumentParser()
parser.add_argument('command')
parser.add_argument('sub_command', default='', nargs='?')
parser.add_argument('-i', '--indent', type=int, default=4)

_rooncommands = rooncommands.RoonCommands()

def run(host="0.0.0.0", port="18007"):
    webserver.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    webserver.run(host, port)

@webserver.route("/test")
def test():
    result = f"{roonservicemanager.roon.zone_by_name('Saint Zoey')}"
    return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/restart")
def restart(indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        result = f"{roonservicemanager.restart_core_service()}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/status")
def status(indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        result = {'token': roonservicemanager.roon.token,
                  'host': roonservicemanager.roon.host,
                  'port': roonservicemanager.roon._port,
                  'core_id': roonservicemanager.roon.core_id ,
                  'core_name': roonservicemanager.roon.core_name ,
                  'last_ping': roonservicemanager.lastping}
        result = json.dumps(result, indent=indent)
        return Response(response=result, status=200, mimetype="application/json")


def get_zone_by_name_or_index(name_or_index):
    #return results for specified zone
    if name_or_index == '':
        return None
    elif name_or_index.isdigit():
        zones = roonservicemanager.roon.zones.values()
        if int(name_or_index) < len(zones) and int(name_or_index) > -1:
            zone = list(zones)[int(name_or_index)]
            return zone
        else:
            return f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
    else:
        result = roonservicemanager.roon.zone_by_name(name_or_index)
        if result:
            return result
        else:
            return None
@webserver.route("/list")
@webserver.route("/list/<list_type>")
def _list(list_type='', indent = 0, **kwargs):
    if list_type == '':
        result = "list_type missing"
        return Response(response=result, status=400, mimetype="text/plain")
    else:
        match list_type.lower():
            case "zones":
                result = ""
                zones = roonservicemanager.roon.zones
                for index, zone in enumerate(zones.values()):
                    result = result + f"[{index}]\t{zone['display_name']}\n"
                result = result.strip()
            case "playlists":
                result = ""
                if request.args.get('zone', '') != '':
                    zone = request.args.get('zone')
                else:
                    zone = kwargs.get('zone', '')
                if zone == '':
                    result = f"no zone specified"
                    return Response(response=result, status=404, mimetype="text/plain")
                zone = get_zone_by_name_or_index(zone)
                if zone == None:
                    result = f"zone {kwargs.get('zone', '')} not found"
                    return Response(response=result, status=404, mimetype="text/plain")
                zone = zone['display_name']
                if request.args.get('title', '') != '':
                    title = request.args.get('title')
                else:
                    title = kwargs.get('title', '')
                playlists = _rooncommands.list_playlists(zone, title)
                for index, playlist in enumerate(playlists):
                    result = result + f"[{index}]\t{playlist}\n"
                result = result.strip()
            case _:
                result = f"list_type {list_type} not defined"
                return Response(response=result, status=404, mimetype="text/plain")
        return Response(response=result, status=200, mimetype="text/plain")


@webserver.route("/zones")
@webserver.route("/zones/<zone>") #zone is index (from list zones) or name
def zones(zone='', indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        if request.args.get('indent', '') != '':
            indent = int(request.args.get('indent')) if request.args.get('indent').isdigit() else 0
        #return results for specified zone
        if zone == '':
            result = f"{json.dumps(roonservicemanager.roon.zones, indent=indent)}"
        else:
            result = get_zone_by_name_or_index(zone)
            if result:
                result = f"{json.dumps(result, indent=indent)}"
        if result == None:
            return f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
        else:
            return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/play")
@webserver.route("/play/<type>")
def play(title='', type='', zone='', shuffle=False, indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        if request.args.get('type', '') != '':
            item_type = request.args.get('type')
        else:
            item_type = type
        if request.args.get('zone', '') != '':
            zone = request.args.get('zone')
        if request.args.get('shuffle', '') != '':
            shuffle = request.args.get('shuffle') != '0'
        if request.args.get('indent', '') != '' and request.args.get('indent').isdigit():
            indent = int(request.args.get('indent'))
        if request.args.get('title', '') != '':
            title = request.args.get('title')
        #return results for specified zone
        if zone == '':
            result = f"zone must be specified. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
            return Response(response=result, status=200, mimetype="application/json")
        elif zone.isdigit():
            zones = roonservicemanager.roon.zones.values()
            if int(zone) < len(zones) and int(zone) > -1:
                zone = list(zones)[int(zone)]['display_name']
            else:
                result =  f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
                return Response(response=result, status=200, mimetype="application/json")
        else:
            zone = roonservicemanager.roon.zone_by_name(zone)
            if not zone:
                result = f"zone {{{zone}}} not found. (Note zone names are case sensitive. Use \"list zones\" command to see zone names.)"
                return Response(response=result, status=200, mimetype="application/json")
            zone = zone['display_name']

        result = _rooncommands.play_playlist(title, zone, shuffle=shuffle)

        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/ping")
def ping(indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        result = f"{json.dumps(roonservicemanager.ping_core(), indent=indent)}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/getlog")
def getlog(indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        result = f"{roonservicemanager.getLog()}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/settings")
def settings(indent = 0):
    if roonservicemanager is None:
        result = "roonservicemanager not initialized"
        return Response(response=result, status=503, mimetype="text/plain")
    else:
        result = f"{json.dumps(roonservicemanager.settings, indent=indent)}"
        return Response(response=result, status=200, mimetype="application/json")

@webserver.route("/command/<command>")
def runcommand(command, *args, **kwargs):
    command = command.lower()
    if request.args.get('type', '') != '':
        output_name = request.args.get('output')
    else:
        output_name = kwargs.get('output', None)
    if request.args.get('type', '') != '':
        item_type = request.args.get('type')
    else:
        item_type = kwargs.get('type', None)
    if request.args.get('item', '') != '':
        item_string = request.args.get('item')
    else:
        item_string = kwargs.get('item', None)

    return (f"received {command} {args} {kwargs}")

@webserver.route("/terminal")
def terminal():
    line = request.args.get('line')
    tokens = shlex.split(line)
    result = ""
    try:
        # command = tokens.pop(0)
        args, unknown = parser.parse_known_args(tokens)
        command = args.command.lower()
        indent = args.indent
        kwargs = {}
        extra_args = []
        for s in unknown:
            if "=" in s:
                kwargs[s.split("=", maxsplit=1)[0]] = s.split("=", maxsplit=1)[1]
            else:
                extra_args.append(s)
        match command:
            case "restart":
                result = restart(indent=indent)
            case "status":
                result = status(indent=indent)
            case _ as _command if _command=="zones" or _command=="zone":
                if args.sub_command=='':
                    result = zones(indent=indent)
                else:
                    result = zones(zone=args.sub_command, indent=indent)
            case "ping":
                result = ping(indent=indent)
            case "log":
                result = getlog(indent=indent)
            case "settings":
                result = settings(indent=indent)
            case "list":
                if args.sub_command=='':
                    result = _list(indent=indent)
                else:
                    result = _list(list_type=args.sub_command, indent=indent, **kwargs)
            case "play":
                result = play(type=args.sub_command, **kwargs)
            case "command":
                if args.sub_command=='':
                    result = f"command requires name of command to run"
                else:
                    kwargs = {}
                    extra_args = []
                    for s in unknown:
                        if "=" in s:
                            kwargs[s.split("=", maxsplit=1)[0]] = s.split("=", maxsplit=1)[1]
                        else:
                            extra_args.append(s)
                    result = runcommand(args.sub_command, *extra_args, **kwargs)

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
