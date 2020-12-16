
from json import dumps
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)

from jsonite import Parser

INDEX_HTML_PATH = 'theater/index.html'

def get_send(socket):
    def send (event, payload=None):
        data = bytes(f'data: {dumps([event, payload])}\n\n', encoding='utf-8')
        socket.write(data)
    return send

def player(send, url):
    send('LOADING', url)

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
