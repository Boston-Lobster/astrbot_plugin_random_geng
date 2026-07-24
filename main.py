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

    # ========== /烂梗 ==========

    @filter.command("烂梗")
    async def random_geng(self, event: AstrMessageEvent):
        barrage = await self._fetch_geng()
        if barrage:
            yield event.plain_result(barrage)
        else:
            yield event.plain_result("烂梗获取失败，玩机器正在咬打火机")

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
                    yield event.plain_result("热门榜暂无数据")
            else:
                yield event.plain_result("热门烂梗获取失败")
        except Exception as e:
            logger.error(f"热门烂梗插件出错: {e}")
            yield event.plain_result("热门烂梗获取失败")

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
            yield event.plain_result(
                f"🤖 AI自动烂梗：{status}\n"
                f"⚙ 判断模型：{pname} | 冷却：{self.config.get('ai_cooldown', 300)}秒\n"
                f"用法：/烂梗ai on | off | status\n"
                f"提示：在 WebUI 插件设置中选择 LLM 提供商"
            )
            return

        cmd = parts[1].lower()
        if cmd == "on":
            if not self.config.get("ai_provider_id", ""):
                yield event.plain_result("⚠️ 请先在 WebUI 插件设置中选择一个 LLM 提供商，再开启 AI 模式")
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
            yield event.plain_result(f"🤖 AI自动烂梗：{status}\n⚙ 判断模型：{pname} | 冷却：{cooldown}秒\n⏱ {cd}")
        else:
            yield event.plain_result(f"未知参数: {cmd}，请用 on / off / status")

    # ========== AI 自动判断钩子 ==========

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
                    logger.info("AI 判断通过，自动发送烂梗")
        except Exception as e:
            logger.warning(f"AI烂梗判断异常（不影响回复）: {e}")

    # ========== 工具方法 ==========

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
                "你是梗警察。根据群聊消息判断：现在是否适合发一条网络烂梗/抽象话活跃气氛？\n"
                "适合：群友在玩梗、开玩笑、闲聊、讨论主播/电竞、气氛轻松。\n"
                "不适合：认真讨论、求助、吵架、严肃话题。\n"
                "只回复 YES 或 NO。\n\n"
                f"群聊消息：{user_message}\n\n"
                "现在适合发烂梗吗？"
            )

            if hasattr(provider, 'text_chat'):
                resp = await asyncio.wait_for(
                    provider.text_chat(prompt),
                    timeout=10
                )
                text = resp if isinstance(resp, str) else str(resp)
                return "YES" in text.strip().upper()

        except Exception as e:
            logger.warning(f"AI判断失败: {e}")
        return False

    def _get_selected_provider(self):
        """获取用户在设置中选择的提供商"""
        try:
            provider_id = self.config.get("ai_provider_id", "").strip()
            if not provider_id:
                return None

            providers = self.context.get_all_providers()
            for p in providers:
                # AstrBot 的 provider 对象通常有 __class__.__name__ 或 name 属性
                # select_provider 返回的 ID 可能是类名或配置键名
                cls_name = p.__class__.__name__
                p_name = getattr(p, 'name', '') or ''
                p_id = getattr(p, 'id', '') or ''
                cfg_id = getattr(p, 'config_id', '') or ''

                ids = [cls_name, p_name, p_id, cfg_id]
                if provider_id in ids:
                    return p

            # 模糊匹配
            for p in providers:
                cls_name = p.__class__.__name__
                if provider_id.lower() in cls_name.lower():
                    return p

            return None
        except Exception as e:
            logger.warning(f"获取提供商失败: {e}")
            return None

    def _get_provider_display_name(self, provider_id: str) -> str:
        """获取提供商的显示名称"""
        try:
            providers = self.context.get_all_providers()
            for p in providers:
                cls_name = p.__class__.__name__
                if provider_id in cls_name:
                    # 尝试获取模型名
                    model = getattr(p, 'model_name', '') or getattr(p, 'model', '') or ''
                    if model:
                        return f"{cls_name} ({model})"
                    return cls_name
            return provider_id
        except:
            return provider_id

    async def terminate(self):
        pass
