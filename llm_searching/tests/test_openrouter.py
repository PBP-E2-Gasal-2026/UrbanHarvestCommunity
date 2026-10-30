import json
from unittest.mock import Mock

import requests
from django.test import SimpleTestCase

from llm_searching.exceptions import ProviderUnavailable
from llm_searching.filters import SearchFilters
from llm_searching.openrouter import OpenRouterClient


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
    def test_location_capitalization_produces_identical_model_requests(self):
        payload = {
            "status": "search",
            "filters": {
                "keyword": "segar",
                "categories": ["sayuran"],
                "location": "Depok",
            },
            "clarification": "",
            "unsupported_conditions": [],
        }
        request = Mock(
            return_value=Response(
                json.dumps({"choices": [{"message": {"content": json.dumps(payload)}}]})
            )
        )
        client = OpenRouterClient(api_key="test-key", request=request)
        client.extract("sayuran segar di sekitar depok", ["sayuran"])
        first = request.call_args.kwargs["json"]
        client.extract("sayuran segar di sekitar Depok", ["sayuran"])
        second = request.call_args.kwargs["json"]
        self.assertEqual(first, second)
        self.assertEqual(
            first["messages"][-1]["content"], "sayuran segar di sekitar depok"
        )

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
        self.assertEqual(kwargs["json"]["messages"][-1]["content"], "cari tomat")

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
                    api_key="key", request=lambda *a, body=body, **k: Response(body)
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

    def test_ranking_receives_product_description_and_larger_response_budget(self):
        transport = Mock(
            return_value=Response(
                json.dumps(
                    {
                        "choices": [
                            {"message": {"content": json.dumps({"suggestions": []})}}
                        ]
                    }
                )
            )
        )
        candidate = Mock()
        candidate.to_dict.return_value = {
            "id": 7,
            "name": "Tomat",
            "description": "Dari kebun lokal",
        }
        OpenRouterClient(api_key="test", request=transport).suggest(
            "rekomendasikan sayur", SearchFilters(categories=("sayuran",)), [candidate]
        )
        payload = transport.call_args.kwargs["json"]
        data = json.loads(payload["messages"][-1]["content"])
        self.assertIn("description", data["candidates"][0])
        self.assertEqual(data["candidates"][0]["description"], "Dari kebun lokal")
        self.assertEqual(payload["max_tokens"], 3000)
