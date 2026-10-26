import json
from unittest.mock import Mock
import requests
from django.test import SimpleTestCase
from llm_searching.openrouter import OpenRouterClient
from llm_searching.exceptions import ProviderUnavailable


class Response:
    def __init__(self, content, status=200):
        self.content = content.encode()
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("secret provider detail")

    def iter_content(self, chunk_size):
        yield self.content

    def close(self):
        pass


class OpenRouterTests(SimpleTestCase):
    def test_request_contract_and_valid_response(self):
        payload = {
            "status": "search",
            "filters": {"keyword": "tomat"},
            "clarification": "",
            "unsupported_conditions": [],
        }
        transport = Mock(
            return_value=Response(
                json.dumps({"choices": [{"message": {"content": json.dumps(payload)}}]})
            )
        )
        result = OpenRouterClient(api_key="private-key", request=transport).extract(
            "cari tomat", ["sayuran"]
        )
        self.assertEqual(result["filters"], {"keyword": "tomat"})
        args, kwargs = transport.call_args
        self.assertEqual(args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(kwargs["timeout"], (5, 30))
        self.assertEqual(kwargs["json"]["model"], "google/gemma-3-27b-it")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer private-key")
        self.assertNotIn("private-key", json.dumps(kwargs["json"]))
        self.assertEqual(kwargs["json"]["response_format"]["type"], "json_schema")

    def test_invalid_external_responses_are_safe_errors(self):
        bodies = [
            "not json",
            "{}",
            '{"choices": []}',
            json.dumps({"choices": [{"message": {"content": "not-json"}}]}),
            "x" * 65537,
        ]
        for body in bodies:
            with self.subTest(body=body[:30]), self.assertRaises(ProviderUnavailable):
                OpenRouterClient(
                    api_key="key", request=lambda *a, **k: Response(body)
                ).extract("tomat", [])
        for failure in (requests.Timeout("secret"), requests.ConnectionError("secret")):
            with self.assertRaises(ProviderUnavailable) as caught:
                OpenRouterClient(
                    api_key="key", request=Mock(side_effect=failure)
                ).extract("tomat", [])
            self.assertNotIn("secret", str(caught.exception))

    def test_http_error_and_missing_key(self):
        with self.assertRaises(ProviderUnavailable):
            OpenRouterClient(
                api_key="key", request=lambda *a, **k: Response("{}", 429)
            ).extract("tomat", [])
        with self.assertRaises(ProviderUnavailable):
            OpenRouterClient(api_key="", request=Mock()).extract("tomat", [])
