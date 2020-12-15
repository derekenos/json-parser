
from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)

from jsonite import Parser

INDEX_HTML = b"""
<!DOCTYPE html>

<html lang="en">
  <head>
    <meta charset="utf-8">

    <script>
      function init () {
        const urlInput = document.getElementById("url")

        // Add URL keydown handler.
        urlInput.addEventListener("keydown", e => {
          if (e.key === "Enter") {
            window.location.pathname = `/${e.target.value}`
          }
        })

        // Attempt to parse the URL from pathname.
        const url = window.location.pathname.slice(1)
        if (!url.startsWith('http')) {
          return
        }
        urlInput.value = url
      }
      document.addEventListener("DOMContentLoaded", () => init())
    </script>

    <style>
      body {
        margin: 0;
        padding: 0;
      }

      #top-bar {
        padding: 1rem;
        background-color: #222266;
        color: #fff;
        font-variant: small-caps;
        font-weight: bold;
        letter-spacing: 0.1rem;
      }

      #url {
        width: 50%;
      }
    </style>
  </head>

  <body>
    <div id="top-bar">
      <label for="url">url</label>
      <input id="url" type="text" name="url"
             placeholder="Enter the URL of some JSON data and hit ENTER"
             size="64">
    </div>

  </body>

</html>
"""

def get_parser_for_url(url):


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
        self.send_response(200)
        self.send_header('content-type', 'text/html; charset=UTF-8')
        self.send_header('content-length', str(len(INDEX_HTML)))
        self.end_headers()
        self.wfile.write(INDEX_HTML)

    def _serve_play(self):
        # Parse the URL from the path.
        url = self.path.split('/', 2)[-1]
        print(url)

        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.end_headers()
        self.wfile.write(bytes('data: {}\n\n'.format(url), encoding='utf-8'))


def serve():
    server = HTTPServer(('0.0.0.0', 5000), RequestHandler)
    server.serve_forever()


if __name__ == '__main__':
    serve()
