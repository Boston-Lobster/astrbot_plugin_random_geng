import time
import httpx
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import AstrBotConfig, logger
from astrbot.api.message_components import Plain


class RandomGeng(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.geng_api = "https://hguofichp.cn:10086/machine/getRandOne"
        self.last_ai_check = 0

    # ========== /烂梗 (斜杠命令) ==========

    @filter.command("烂梗")
    async def random_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)
        else:
            yield event.plain_result("烂梗获取失败")

    # ========== 自然语言正则匹配 ==========

    @filter.regex(r"来[条个]?[烂乱随]梗")
    async def lai_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)

    @filter.regex(r"给[我俺].*[烂乱随]梗")
    async def gei_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)

    @filter.regex(r"整[条个]?[烂乱随]梗")
    async def zheng_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)

    @filter.regex(r"[发讲说搞][条个]?[烂乱随]梗")
    async def fa_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)

    @filter.regex(r"来点[烂乱随]梗")
    async def laidian_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)

    # ========== /烂梗榜 ==========

    @filter.command("烂梗榜")
    async def hot_geng(self, event: AstrMessageEvent):
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(
                    "https://hguofichp.cn:10086/machine/sortAllBarrage",
                    params={"pageNum": 1, "pageSize": 5}
                )
                data = resp.json()
            if data.get("code") == 200 and data.get("data"):
                geng_list = data["data"].get("list", [])[:5]
                if not geng_list:
                    geng_list = data["data"] if isinstance(data["data"], list) else []
                if geng_list:
                    lines = []
                    for i, g in enumerate(geng_list, 1):
                        barrage = g.get("barrage", "")
                        if barrage:
                            lines.append(f"{i}. {barrage}")
                    if lines:
                        yield event.plain_result("\n".join(lines))
                else:
                    yield event.plain_result("热门榜暂无数据")
            else:
                yield event.plain_result("热门烂梗获取失败")
        except Exception as e:
            logger.error(f"热门烂梗插件出错: {e}")

    # ========== /烂梗ai ==========

    @filter.command("烂梗ai")
    async def toggle_ai(self, event: AstrMessageEvent):
        msg = event.message_obj.message.strip()
        parts = msg.split()
        if len(parts) < 2:
            enabled = self.config.get("ai_enabled", False)
            status = "开启" if enabled else "关闭"
            pid = self.config.get("ai_provider_id", "")
            pname = self._get_provider_display_name(pid) if pid else "未设置"
            yield event.plain_result(f"🤖 AI自动烂梗：{status}\n⚙ {pname} | 冷却：{self.config.get('ai_cooldown', 300)}秒")
            return

        cmd = parts[1].lower()
        if cmd == "on":
            if not self.config.get("ai_provider_id", ""):
                yield event.plain_result("⚠️ 请先在 WebUI 插件设置中选择一个 LLM 提供商")
                return
            self.config["ai_enabled"] = True
            self.last_ai_check = 0
            yield event.plain_result("✅ AI自动烂梗已开启")
        elif cmd == "off":
            self.config["ai_enabled"] = False
            yield event.plain_result("❌ AI自动烂梗已关闭")
        elif cmd in ("status", "状态"):
            enabled = self.config.get("ai_enabled", False)
            cooldown = self.config.get("ai_cooldown", 300)
            pid = self.config.get("ai_provider_id", "")
            pname = self._get_provider_display_name(pid) if pid else "未设置"
            left = int(cooldown - (time.time() - self.last_ai_check))
            cd = f"冷却中（{left}秒后下次检查）" if left > 0 and enabled else "就绪"
            status = "开启" if enabled else "关闭"
            yield event.plain_result(f"🤖 AI自动烂梗：{status}\n⚙ {pname} | 冷却：{cooldown}秒\n⏱ {cd}")
        else:
            yield event.plain_result(f"未知参数: {cmd}")

    # ========== AI 自动判断 ==========

    @filter.on_decorating_result(priority=200)
    async def ai_judge_meme(self, event: AstrMessageEvent):
        if not self.config.get("ai_enabled", False):
            return

        cooldown = self.config.get("ai_cooldown", 300)
        now = time.time()
        if now - self.last_ai_check < cooldown:
            return

        self.last_ai_check = now

        try:
            user_msg = event.message_obj.message
            if not user_msg:
                return
            if len(user_msg) > 200:
                user_msg = user_msg[:200] + "..."

            should_send = await self._ask_ai(user_msg)
            if should_send:
                barrage = await self._fetch_geng()
                if barrage:
                    chain = event.get_result().chain
                    chain.insert(0, Plain(barrage))
                    logger.info("[烂梗AI] ✅ 已插入烂梗")
        except Exception as e:
            logger.warning(f"[烂梗AI] 异常: {e}")

    # ========== 工具 ==========

    async def _fetch_geng(self) -> str:
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get(self.geng_api)
                data = resp.json()
            if data.get("code") == 200 and data.get("data"):
                return data["data"].get("barrage", "")
        except Exception as e:
            logger.error(f"获取烂梗失败: {e}")
        return ""

    async def _ask_ai(self, user_message: str) -> bool:
        provider = self._get_selected_provider()
        if not provider:
            return False
        try:
            prompt = (
                "你是严格的梗警察。判断：这条群聊消息值不值得插一条网络烂梗。\n"
                "规则：默认不插。只有同时满足以下三条才回复 YES：\n"
                "1. 消息里有明显玩梗信号：哈哈哈、抽象话、网络梗词、表情包密集、调侃打趣；\n"
                "2. 消息是纯闲聊娱乐，绝不是提问、求助、请教、汇报、或认真讨论某话题；\n"
                "3. 语气轻松愉快，没有任何认真、焦虑、争论、不满、求助的情绪。\n"
                "任何一条不满足都回复 NO。不要被群友的玩笑话误导，拿不准就 NO。\n"
                "只回复 YES 或 NO。"
                f"\n\n群聊消息：{user_message}"
            )
            if hasattr(provider, 'text_chat'):
                resp = await asyncio.wait_for(provider.text_chat(prompt), timeout=10)
                text = self._extract_text(resp)
                return "YES" in text.strip().upper() if text else False
        except Exception as e:
            logger.warning(f"[烂梗AI] 失败: {e}")
        return False

    def _extract_text(self, response_obj) -> str:
        if isinstance(response_obj, str):
            return response_obj.strip()
        if response_obj is None:
            return ""
        for attr in ('completion_text', 'text', 'content'):
            if hasattr(response_obj, attr):
                val = getattr(response_obj, attr)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        if hasattr(response_obj, 'result_chain'):
            parts = []
            for c in response_obj.result_chain:
                if hasattr(c, 'text') and c.text:
                    parts.append(c.text)
                elif isinstance(c, str):
                    parts.append(c)
            if parts:
                return ' '.join(parts).strip()
        return str(response_obj).strip()

    def _get_selected_provider(self):
        try:
            provider_id = self.config.get("ai_provider_id", "").strip()
            if not provider_id:
                return None
            providers = self.context.get_all_providers()
            search = provider_id.split('/')[-1] if '/' in provider_id else provider_id
            for p in providers:
                cls = p.__class__.__name__
                name = getattr(p, 'name', '') or ''
                model = getattr(p, 'model_name', '') or getattr(p, 'model', '') or ''
                ptype = getattr(p, 'type', '') or ''
                for v in [cls, name, model, ptype]:
                    if search.lower() in v.lower():
                        return p
            return None
        except Exception as e:
            logger.error(f"获取提供商失败: {e}")
            return None

    def _get_provider_display_name(self, provider_id: str) -> str:
        p = self._get_selected_provider()
        if p:
            cls = p.__class__.__name__
            model = getattr(p, 'model_name', '') or getattr(p, 'model', '') or ''
            return f"{cls}({model})" if model else cls
        return provider_id

    async def terminate(self):
        pass
