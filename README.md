# Skills

Reusable Claude Code skills — solutions I built while solving real problems with AI agents.

## Available Skills

### [video-fetch](./video-fetch)

Fetch, transcribe, and summarize any YouTube or Bilibili video.

4-level fallback: Subtitle API → ElevenLabs STT → local Whisper → description.

```bash
clawhub install video-fetch
```

[View on ClawHub](https://clawhub.ai/LambertAlpha/video-fetch)

### [weekly-report](./weekly-report)

Auto-generate institutional-grade macro research weekly reports from Research OS model outputs (Liquidity v3.0 + Macro v4.0 + Equity v1.0), then publish to Lark (飞书) group chat.

Fetches model data via API → Claude generates report with full analysis → sends to Lark webhook.

### [wechat-reader](./wechat-reader)

解析微信公众号文章，提取标题、作者、发布时间、正文和图片。用移动端 UA（MicroMessenger）绕过桌面验证码拦截，被拦截时自动轮换 UA 重试。

```bash
# 发送微信文章链接即可自动触发，或手动调用：
python3 scripts/wechat_reader.py "https://mp.weixin.qq.com/s/xxxxx" --full
```
