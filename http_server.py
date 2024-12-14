import os

from douzero.dmc import parser
from douzero.dmc import getModel, predict

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time

class MyHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, model=None, flags=None, **kwargs):
        self.model = model  # Injected dependency
        self.flags = flags
        super().__init__(*args, **kwargs)

    def do_POST(self):
        # Get content length to read the body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            # Parse the request body as JSON
            request_body = json.loads(post_data)

            # Log the received data
            print(f"request_body: {request_body}")
            responseBody = predict(self.model, request_body, self.flags)
            print(f"responseBody: {responseBody}")

            # Send response
            response = {"status": "succ", "action": responseBody}
            self.send_response(200)  # HTTP status code
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except json.JSONDecodeError:
            # Handle JSON parsing errors
            self.send_response(400)  # Bad Request
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode('utf-8'))
            return

# Set up and start the server
def run(server_class=HTTPServer, handler_class=MyHandler, port=8000, model=None, flags=None):
    def handler(*args, **kwargs):
        handler_class(*args, model=model, flags=flags, **kwargs)

    server_address = ('',  8000)
    httpd = server_class(server_address, handler)
    print(f"Starting server on port {port}")
    httpd.serve_forever()


if __name__ == '__main__':
    flags = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = flags.gpu_devices
    model = getModel(flags)
    run(model=model, flags=flags)