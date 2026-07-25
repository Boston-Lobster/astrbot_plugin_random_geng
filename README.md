# astrbot_plugin_random_geng

从 [sb6657.cn](https://sb6657.cn) 随机抓取玩机器烂梗的 AstrBot 插件。

## 触发方式

| 方式 | 示例 |
|------|------|
| 斜杠命令 | `/烂梗` `/烂梗榜` |
| 自然语言 | `来条烂梗` `整个烂梗` `发条烂梗` `来点烂梗` |
| AI 自动 | 开启后 Bot 回复时自动判断是否丢梗 |

## AI 自动判断

1. 在 WebUI 插件设置中选择 LLM 提供商（推荐低价模型）
2. `/烂梗ai on` 开启
3. Bot 每次回复前用 AI 判断氛围是否适合（YES/NO），~100 token/次
4. 可配置冷却时间（默认 300 秒）

## 安装

1. 放入 AstrBot `data/plugins/` 目录
2. `pip install httpx`
3. 重启 AstrBot，在 WebUI 设置中选择提供商

## 版本

v1.3.0 — 自然语言 regex + AI 自动判断 + select_provider
