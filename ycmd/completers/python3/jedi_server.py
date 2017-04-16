import os
import sys
import json
from urllib.parse import parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

ABSPATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ABSPATH + '/../../../third_party/jedi')
import jedi


class JediServerHandler(BaseHTTPRequestHandler):

    supported_requests = ['gotodefinition',
                          'gotodelcaration',
                          'getcompletions']

    def do_POST(self):
        # cut '/'
        cmd = self.path[1:]
        if cmd in self.supported_requests:
            length = int(self.headers['Content-Length'])
            request_data = parse_qs(self.rfile.read(length).decode('utf-8'))
            getattr(self, cmd)(request_data)
        else:
            self.send_response(404)
            self.end_headers()

    def gotodefinition(self, request_data):
        script = self._get_script(request_data)
        definitions = script.goto_definitions()
        definitions = [
            {
                "in_builtin_module": definition.in_builtin_module(),
                "is_keyword": definition.is_keyword,
                "module_path": definition.module_path,
                "line": definition.line,
                "column": definition.column,
                "description": definition.description,
            }
            for definition in definitions
        ]
        self._send_response(definitions)

    def gotodeclaration(self, request_data):
        script = self._get_script(request_data)
        definitions = script.goto_assignments()
        definitions = [
            {
                "in_builtin_module": definition.in_builtin_module(),
                "is_keyword": definition.is_keyword,
                "module_path": definition.module_path,
                "line": definition.line,
                "column": definition.column,
                "description": definition.description,
            }
            for definition in definitions
        ]
        self._send_response(definitions)

    def getcompletions(self, request_data):
        script = self._get_script(request_data)
        completions = script.completions()
        completions = [
            {
                "name": completion.name,
                "description": completion.description,
                "docstring": completion.docstring()
            }
            for completion in completions
        ]
        self._send_response(completions)


    def _get_script(self, request_data):
        try:
            filename = request_data['filename'][0]
            contents = request_data['buffer'][0]
            line = int(request_data['line'][0])
            # Jedi expects columns to start at 0, not 1
            column = int(request_data['column'][0]) - 1
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            raise e

        return jedi.Script(contents, line, column, filename)

    def _send_response(self, dict_data):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(json.dumps(dict_data), 'utf8'))


class JediServer(HTTPServer):
    pass


def run(port):
    server = JediServer
    httpd = server(("127.0.0.1", port), JediServerHandler)
    httpd.serve_forever()


if __name__ ==  "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", type=int, default=6321)
    args = ap.parse_args()
    run(args.port)
