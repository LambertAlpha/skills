#!/usr/bin/env python3
"""
发送消息到飞书群机器人 (Lark Webhook)。

用法:
    # 发送纯文本
    python3 scripts/send_to_lark.py --webhook @~/.lark_webhook "消息内容"

    # 从 stdin 读取（适合管道）
    echo "消息内容" | python3 scripts/send_to_lark.py --webhook @~/.lark_webhook --stdin

    # 发送富文本（Markdown 格式，飞书 interactive card）
    python3 scripts/send_to_lark.py --webhook @~/.lark_webhook --markdown "# 标题\n内容"

安全提示:
    Webhook URL 是群聊凭证，泄露后任何人都能往群里发消息。
    务必使用 @filepath 方式传入，不要直接在命令行写 URL。
"""
import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)


def load_secret(value: str) -> str:
    """加载凭证：@filepath 从文件读取，否则直接使用"""
    if value.startswith("@"):
        path = value[1:]
        if path.startswith("~"):
            import os
            path = os.path.expanduser(path)
        with open(path, "r") as f:
            return f.read().strip()
    return value


def send_text(webhook_url: str, text: str) -> bool:
    """发送纯文本消息"""
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    result = resp.json()
    if result.get("code") != 0 and result.get("StatusCode") != 0:
        print(f"Lark API error: {result}", file=sys.stderr)
        return False
    return True


def send_interactive(webhook_url: str, title: str, content: str) -> bool:
    """
    发送富文本卡片消息（飞书 interactive message card）。
    content 使用飞书 Markdown 语法（支持加粗、链接、列表等）。
    """
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content,
                }
            ],
        },
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    result = resp.json()
    if result.get("code") != 0 and result.get("StatusCode") != 0:
        print(f"Lark API error: {result}", file=sys.stderr)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Send message to Lark webhook")
    parser.add_argument("message", nargs="?", help="Message text (or use --stdin)")
    parser.add_argument("--webhook", required=True,
                        help="Lark webhook URL (use @filepath for security)")
    parser.add_argument("--stdin", action="store_true",
                        help="Read message from stdin")
    parser.add_argument("--markdown", action="store_true",
                        help="Send as interactive card with markdown")
    parser.add_argument("--title", default="Research OS 周报",
                        help="Card title (only for --markdown)")
    args = parser.parse_args()

    webhook_url = load_secret(args.webhook)

    if args.stdin:
        message = sys.stdin.read().strip()
    elif args.message:
        message = args.message
    else:
        print("ERROR: Provide message as argument or use --stdin", file=sys.stderr)
        sys.exit(1)

    if not message:
        print("ERROR: Empty message", file=sys.stderr)
        sys.exit(1)

    if args.markdown:
        ok = send_interactive(webhook_url, args.title, message)
    else:
        ok = send_text(webhook_url, message)

    if ok:
        print("Message sent successfully")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
