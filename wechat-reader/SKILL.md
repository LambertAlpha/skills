---
name: wechat-reader
description: "解析微信公众号文章，提取标题、作者、发布时间、正文和图片。当用户发送 mp.weixin.qq.com 链接、要求阅读/解析/总结微信文章时触发。用移动端 UA 绕过桌面验证码拦截。"
user-invocable: true
argument-hint: "https://mp.weixin.qq.com/s/xxxxx"
allowed-tools: Bash, Read
---

# 微信公众号文章阅读器

解析 mp.weixin.qq.com 文章，提取结构化内容。

## Workflow

1. 用户发送微信公众号文章链接
2. 运行脚本：`python3 <skill_path>/scripts/wechat_reader.py "<url>"`
3. 脚本自动用移动端 UA 抓取并解析文章内容
4. 返回：标题、作者、发布时间、正文、图片列表

## Usage

```bash
python3 <skill_path>/scripts/wechat_reader.py "URL"            # 基本（正文截断2000字）
python3 <skill_path>/scripts/wechat_reader.py "URL" --full      # 完整正文
python3 <skill_path>/scripts/wechat_reader.py "URL" --json      # JSON 输出
python3 <skill_path>/scripts/wechat_reader.py "URL" --save x.json  # 保存到文件
```

## Strategy

- 默认微信内置浏览器 UA（MicroMessenger），最不易被拦截
- 被拦截时自动轮换 iPhone Safari / Android Chrome 重试
- 带 Referer 头模拟正常跳转

## Prerequisites

- `pip3 install requests beautifulsoup4`

## What NOT to do

- Do NOT use `WebFetch` on mp.weixin.qq.com URLs (会触发验证码)
- Do NOT use桌面端 UA (会被拦截)
