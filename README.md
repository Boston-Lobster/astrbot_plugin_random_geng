# astrbot_plugin_random_geng

从 [sb6657.cn](https://sb6657.cn) 随机抓取玩机器烂梗的 AstrBot 插件。

## 命令

| 命令 | 功能 |
|------|------|
| /烂梗 | 随机获取一条烂梗 |
| /烂梗榜 | 热门烂梗 TOP5 |
| /烂梗ai on/off/status | AI 自动判断模式开关 |

## AI 自动判断

开启后，插件会在冷却时间过后，调用 AstrBot 已配置的 LLM 提供商判断当前聊天氛围是否适合发送烂梗。

在 WebUI 插件设置中：
- 选择用于判断的 LLM 提供商（推荐低价模型，如 DeepSeek）
- 设置冷却时间（默认 300 秒）

每次判断仅消耗约 100 token，5 分钟最多调用一次。

## 数据源

API: `https://hguofichp.cn:10086/machine/getRandOne`（无需鉴权）

## 安装

1. 将插件文件夹放入 AstrBot 的 `data/plugins/` 目录
2. 确保 `httpx` 已安装：`pip install httpx`
3. 重启 AstrBot 或从 WebUI 重载插件
4. 在 WebUI 插件管理 → 随机烂梗 → 设置 中配置提供商

## 依赖

- `httpx` — HTTP 请求

## 版本

v1.2.0 — 使用 AstrBot 内置提供商下拉选择（`_special: select_provider`）
