import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from django.test import SimpleTestCase

from llm_searching.provider_http import bounded_post


class ProviderDeadlineTests(SimpleTestCase):
    def test_trickling_response_is_cancelled_before_a_chunk_finishes(self):
        class SlowHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(200)
                self.send_header("Content-Length", "10000")
                self.end_headers()
                try:
                    for _ in range(100):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.05)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            started = time.monotonic()
            with self.assertRaises(requests.Timeout):
                bounded_post(
                    f"http://127.0.0.1:{server.server_port}/",
                    json={"prompt": "test"},
                    timeout=(5, 30),
                    stream=True,
                    deadline_seconds=0.5,
                )
            self.assertLess(time.monotonic() - started, 2)
            self.assertFalse(any(p.name.startswith("llm-provider-") for p in __import__("multiprocessing").active_children()))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_completed_response_is_returned_and_process_is_reaped(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                body = b'{"choices": []}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = bounded_post(
                f"http://127.0.0.1:{server.server_port}/",
                json={}, timeout=(5, 30), stream=True, deadline_seconds=3,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.iter_content(8192)), b'{"choices": []}')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
