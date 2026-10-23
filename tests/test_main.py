"""Offline tests for the plugin's real methods using small AstrBot/httpx stubs."""

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeFilter:
    @staticmethod
    def _decorator(*args, **kwargs):
        return lambda function: function

    command = _decorator
    regex = _decorator
    on_decorating_result = _decorator


class FakePlain:
    def __init__(self, text):
        self.text = text


class FakeLogger:
    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: None


class FakeResponse:
    def __init__(self, body=None, error=None):
        self.body = body
        self.error = error
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True
        if self.error:
            raise self.error

    def json(self):
        return self.body


class FakeAsyncClient:
    responses = []
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.response = self.responses.pop(0)
        self.requests = []
        self.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.response


def install_framework_stubs():
    astrbot = types.ModuleType("astrbot")
    astrbot.__path__ = []
    api = types.ModuleType("astrbot.api")
    api.__path__ = []
    api.AstrBotConfig = dict
    api.logger = FakeLogger()

    event_module = types.ModuleType("astrbot.api.event")
    event_module.filter = FakeFilter()
    event_module.AstrMessageEvent = object

    star_module = types.ModuleType("astrbot.api.star")

    class Star:
        def __init__(self, context):
            self.context = context

    star_module.Context = object
    star_module.Star = Star

    components_module = types.ModuleType("astrbot.api.message_components")
    components_module.Plain = FakePlain

    httpx_module = types.ModuleType("httpx")
    httpx_module.AsyncClient = FakeAsyncClient

    sys.modules.update(
        {
            "astrbot": astrbot,
            "astrbot.api": api,
            "astrbot.api.event": event_module,
            "astrbot.api.star": star_module,
            "astrbot.api.message_components": components_module,
            "httpx": httpx_module,
        }
    )


install_framework_stubs()
plugin_module = importlib.import_module("main")
RandomGeng = plugin_module.RandomGeng


class Provider:
    def __init__(self, provider_id, model="same-model", response="YES"):
        self.model_name = model
        self.type = "openai"
        self.response = response
        self.prompt_calls = []
        self._provider_id = provider_id

    def meta(self):
        return SimpleNamespace(id=self._provider_id)

    async def text_chat(self, prompt):
        self.prompt_calls.append(prompt)
        return self.response


class Context:
    def __init__(self, providers=()):
        self.providers = list(providers)

    def get_all_providers(self):
        return self.providers


class Event:
    def __init__(self, message_str="", components=()):
        self.message_str = message_str
        self.message_obj = SimpleNamespace(
            message=list(components), message_str=message_str
        )
        self.results = []

    def plain_result(self, text):
        result = SimpleNamespace(text=text)
        self.results.append(result)
        return result


class PluginTests(unittest.TestCase):
    def setUp(self):
        FakeAsyncClient.responses.clear()
        FakeAsyncClient.instances.clear()

    def make_plugin(self, config=None, providers=()):
        return RandomGeng(Context(providers), config or {})

    @staticmethod
    def collect(async_generator):
        async def consume():
            return [item async for item in async_generator]

        return asyncio.run(consume())

    def test_toggle_ai_reads_text_with_message_component_chain(self):
        provider = Provider("judge-prod-01")
        plugin = self.make_plugin(
            {"ai_provider_id": "judge-prod-01", "ai_enabled": False}, [provider]
        )
        event = Event(
            "/烂梗ai on", [FakePlain("/烂梗ai on")]
        )

        results = self.collect(plugin.toggle_ai(event))

        self.assertTrue(plugin.config["ai_enabled"])
        self.assertEqual(results[0].text, "✅ AI自动烂梗已开启")

    def test_selected_provider_uses_exact_configured_id_not_substrings(self):
        first = Provider("other-instance", model="judge-prod-01")
        selected = Provider("judge-prod-01", model="same-model")
        plugin = self.make_plugin(
            {"ai_provider_id": "judge-prod-01"}, [first, selected]
        )

        self.assertIs(plugin._get_selected_provider(), selected)

    def test_message_text_falls_back_to_plain_components(self):
        plugin = self.make_plugin()
        event = SimpleNamespace(
            message_str=None,
            message_obj=SimpleNamespace(
                message_str=None,
                message=[FakePlain("hello "), FakePlain("world")],
            ),
        )

        self.assertEqual(plugin._get_message_text(event), "hello world")

    def test_ai_judge_requires_exact_yes_token(self):
        yes_provider = Provider("selected", response=" yes ")
        plugin = self.make_plugin({"ai_provider_id": "selected"}, [yes_provider])
        self.assertTrue(asyncio.run(plugin._ask_ai("哈哈哈")))

        yes_provider.response = "NO, YES"
        self.assertFalse(asyncio.run(plugin._ask_ai("哈哈哈")))

    def test_fetch_geng_checks_status_and_keeps_tls_verification(self):
        response = FakeResponse({"code": 200, "data": {"barrage": "梗"}})
        FakeAsyncClient.responses.append(response)
        plugin = self.make_plugin()

        self.assertEqual(asyncio.run(plugin._fetch_geng()), "梗")
        self.assertTrue(response.status_checked)
        self.assertIsNot(FakeAsyncClient.instances[0].kwargs.get("verify"), False)

    def test_fetch_geng_returns_empty_on_http_error(self):
        response = FakeResponse(error=RuntimeError("HTTP 500"))
        FakeAsyncClient.responses.append(response)
        plugin = self.make_plugin()

        self.assertEqual(asyncio.run(plugin._fetch_geng()), "")
        self.assertTrue(response.status_checked)

    def test_hot_list_accepts_list_and_object_payloads(self):
        for payload in (
            [{"barrage": "第一条"}, {"barrage": "第二条"}],
            {"list": [{"barrage": "第一条"}, {"barrage": "第二条"}]},
        ):
            FakeAsyncClient.responses.append(
                FakeResponse({"code": 200, "data": payload})
            )
            plugin = self.make_plugin()
            event = Event("/烂梗榜")

            results = self.collect(plugin.hot_geng(event))

            self.assertEqual(results[0].text, "1. 第一条\n2. 第二条")
            self.assertTrue(FakeAsyncClient.instances[-1].response.status_checked)

    def test_hot_list_sends_required_empty_tags_to_current_api(self):
        FakeAsyncClient.responses.append(
            FakeResponse({"code": 200, "data": {"list": [{"barrage": "第一条"}]}})
        )
        results = self.collect(self.make_plugin().hot_geng(Event("/烂梗榜")))
        url, kwargs = FakeAsyncClient.instances[-1].requests[0]
        self.assertEqual(url, "https://api.hguofichp.cn/machine/sortAllBarrage")
        self.assertEqual(kwargs["params"], {"pageNum": 1, "pageSize": 5, "tags": ""})
        self.assertEqual(results[0].text, "1. 第一条")

    def test_fetch_geng_uses_current_official_api(self):
        FakeAsyncClient.responses.append(
            FakeResponse({"code": 200, "data": {"barrage": "梗"}})
        )
        self.assertEqual(asyncio.run(self.make_plugin()._fetch_geng()), "梗")
        self.assertEqual(
            FakeAsyncClient.instances[-1].requests[0][0],
            "https://api.hguofichp.cn/machine/getRandOne",
        )

    def test_hot_list_reports_business_failure_even_with_http_success(self):
        response = FakeResponse({"code": 500, "msg": None})
        FakeAsyncClient.responses.append(response)
        results = self.collect(self.make_plugin().hot_geng(Event("/烂梗榜")))
        self.assertTrue(response.status_checked)
        self.assertEqual(results[0].text, "热门烂梗获取失败")

    def test_hot_list_handles_malformed_payload(self):
        FakeAsyncClient.responses.append(FakeResponse({"code": 200, "data": "bad"}))
        plugin = self.make_plugin()
        event = Event("/烂梗榜")

        results = self.collect(plugin.hot_geng(event))

        self.assertEqual(results[0].text, "热门榜暂无数据")


if __name__ == "__main__":
    unittest.main()
