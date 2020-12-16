
from io import BytesIO
from json import dumps
from time import sleep
from types import MethodType
from urllib import request
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)

from jsonite import (
    Parser,
    split_event_value,
)

INDEX_HTML_PATH = 'theater/index.html'

def get_send(socket):
    def send (event, payload=None):
        data = bytes(f'data: {dumps([event, payload])}\n\n', encoding='utf-8')
        socket.write(data)
    return send


def fetch_data(url):
    res = request.urlopen(url)
    if res.status != 200:
        raise Exception(f'response status ({res.status}) != 200')
    return BytesIO(res.read())

def player(send, url):
    # Attempt to fetch the data.
    send('MESSAGE', f'Fetching: {url}')
    try:
        data = fetch_data(url)
    except Exception as e:
        send('ERROR', str(e))
        return

    # Instantiate the parser.
    send('MESSAGE', 'Instantiating jsonite.Parser')
    parser = Parser(data)

    # Hijack Parser.next_char() to send each char.
    old_next_char = parser.next_char
    def next_char(self):
        c = old_next_char()
        send('NEXT_CHAR', c.decode('utf-8'))
        return c
    parser.next_char = MethodType(next_char, parser)

    try:
        for event_value in parser.parse():
            event, value = split_event_value(event_value)
            if value is None:
                send('PARSE', event)
            else:
                value = parser.convert(event, value)
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                send('PARSE', [event, value])
            sleep(0.25)
    except Exception as e:
        send('ERROR', str(e))


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        if (self.path == '/'
              or self.path.startswith('/http://')
              or self.path.startswith('/https://')):
            self._serve_index()
        elif self.path.startswith('/play/'):
            self._serve_play()
        else:
            self.send_error(404)

    def _serve_index(self):
        index_html = open(INDEX_HTML_PATH, 'rb').read()
        self.send_response(200)
        self.send_header('content-type', 'text/html; charset=UTF-8')
        self.send_header('content-length', str(len(index_html)))
        self.end_headers()
        self.wfile.write(index_html)

    def _serve_play(self):
        # Parse the URL from the path.
        url = self.path.split('/', 2)[-1]
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.end_headers()
        player(get_send(self.wfile), url)

def serve(host, port):
    server = HTTPServer((host, port), RequestHandler)
    print(f'Watch the show at: http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default="5000")
    args = parser.parse_args()

    serve(args.host, args.port)
