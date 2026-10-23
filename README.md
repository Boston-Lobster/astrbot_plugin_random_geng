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

也可从 [GitHub Release](https://github.com/Boston-Lobster/astrbot_plugin_random_geng/releases) 下载源码包，解压到插件目录；SHA256SUMS 用于校验下载文件。升级前保留 WebUI 中已有插件设置。

## 验证和发布

`python -m unittest discover -s tests -v` 运行无网络测试。默认分支通过 GitHub Actions 测试和版本校验后自动发布新版本 Release；已有标签保持原指向。版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## 版本

v1.5.1 — 修复烂梗榜缺少 tags 参数导致业务码 500；随机和榜单请求使用当前官方 API 地址

v1.5.0 — 修复 AI 命令读取消息链和模型提供商选择；恢复 HTTPS 证书校验，完善 API 响应校验
v1.4.0 — AI 判断改为严格模式（默认拒绝，三条条件同时满足才触发），冷却时间可调
v1.3.0 — 自然语言 regex + AI 自动判断 + select_provider

