
from io import BytesIO
from json import dumps
from time import sleep
from types import FunctionType
from urllib import request
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)

from __init__ import (
    Matchers,
    Parser,
)

INDEX_HTML_PATH = 'theater/index.html'

def stringify_matcher(matcher, encoding):
    # Convert a matcher byte string or function to unicode.
    if not isinstance(matcher, FunctionType):
        # Matcher is a byte string.
        return matcher.decode(encoding)
    # Matcher is a function.
    for k, v in Matchers.__dict__.items():
        if matcher == v:
            return k
    raise AssertionError

def stringify_expect_stack_item(item, encoding):
    # Convert expect stack element to unicode.
    if not isinstance(item, tuple):
        return stringify_matcher(item, encoding)
    return (
        stringify_matcher(item[0], encoding),
        stringify_expect_stack_item(item[1], encoding)
    )

class InstrumentedExpectStack(list):
    def __init__(self, old_expect_stack, send, encoding):
        super().__init__(old_expect_stack)
        self.send = send
        self.encoding = encoding
        self.send('EXPECT_STACK', self.to_payload())

    def append(self, v):
        super().append(v)
        self.send('EXPECT_STACK', self.to_payload())

    def pop(self):
        v = super().pop()
        return v

    def to_payload(self):
        return [stringify_expect_stack_item(x, self.encoding) for x in self]

class InstrumentedParser(Parser):
    def __init__(self, stream, send):
        super().__init__(stream)
        self.send = send
        self.expect_stack = InstrumentedExpectStack(self.expect_stack, send,
                                                    self.encoding)

    def next_char(self):
        # Check wether any character is stuff, cause we already send'd it.
        any_stuffed = self.stuffed_char is not None
        c = super().next_char()
        if not any_stuffed:
            self.send('NEXT_CHAR', c.decode(self.encoding))
        return c

    def expect(self, matcher):
        c, matcher = super().expect(matcher)
        self.send('MATCHED', stringify_matcher(matcher, self.encoding))
        return c, matcher

def get_send(socket):
    def send (event, payload=None):
        data = bytes(f'data: {dumps([event, payload])}\n\n', encoding='utf-8')
        socket.write(data)
        # Sleep after certain messages.
        if event == 'NEXT_CHAR':
            sleep(0)
        elif event == 'EXPECT_STACK':
            sleep(.5)
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
    send('MESSAGE', 'Instantiating Parser')
    parser = InstrumentedParser(data, send)

    try:
        for event, value in parser.parse():
            if value is None:
                send('PARSE', event)
            else:
                value = parser.convert(event, value)
                send('PARSE', [event, value])
    except Exception as e:
        # DEBUG
        raise
        send('ERROR', str(e))
    send('DONE')


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
