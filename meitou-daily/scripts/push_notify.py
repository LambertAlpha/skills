"""
Push notification module - Send reports to Lark (Feishu) or Telegram.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def send_to_lark(content: str, title: str = "美投每日投研报告"):
    """Send markdown content to Lark via webhook bot."""
    webhook = os.environ.get("LARK_WEBHOOK")
    if not webhook:
        webhook_file = Path.home() / ".lark_webhook"
        if webhook_file.exists():
            webhook = webhook_file.read_text().strip()
    if not webhook:
        raise RuntimeError(
            "No Lark webhook. Set LARK_WEBHOOK env var or create ~/.lark_webhook"
        )

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": content}
            ],
        },
    }

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", webhook,
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, timeout=15,
    )
    resp = json.loads(result.stdout)
    if resp.get("code", -1) != 0 and resp.get("StatusCode", -1) != 0:
        # Try plain text fallback for long messages
        payload_plain = {
            "msg_type": "text",
            "content": {"text": f"{title}\n\n{content}"}
        }
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", webhook,
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload_plain, ensure_ascii=False)],
            capture_output=True, text=True, timeout=15,
        )
        resp = json.loads(result.stdout)

    return resp


def send_to_telegram(content: str, title: str = "美投每日投研报告"):
    """Send markdown content to Telegram via bot API."""
    bot_token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")

    if not bot_token or not chat_id:
        tg_config = Path.home() / ".tg_meitou.json"
        if tg_config.exists():
            config = json.loads(tg_config.read_text())
            bot_token = bot_token or config.get("bot_token")
            chat_id = chat_id or config.get("chat_id")

    if not bot_token or not chat_id:
        raise RuntimeError(
            "No Telegram config. Set TG_BOT_TOKEN/TG_CHAT_ID env vars "
            "or create ~/.tg_meitou.json with {\"bot_token\": ..., \"chat_id\": ...}"
        )

    full_text = f"*{title}*\n\n{content}"

    # Telegram has a 4096 char limit, split if needed
    chunks = []
    while full_text:
        if len(full_text) <= 4000:
            chunks.append(full_text)
            break
        # Split at last newline before limit
        split_at = full_text[:4000].rfind("\n")
        if split_at < 100:
            split_at = 4000
        chunks.append(full_text[:split_at])
        full_text = full_text[split_at:]

    results = []
    for chunk in chunks:
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.telegram.org/bot{bot_token}/sendMessage",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload, ensure_ascii=False)],
            capture_output=True, text=True, timeout=15,
        )
        results.append(json.loads(result.stdout))

    return results


def push(content: str, title: str = "美投每日投研报告", targets: list[str] = None):
    """Push to all configured targets. Returns dict of results."""
    if targets is None:
        targets = []
        # Auto-detect configured targets
        if os.environ.get("LARK_WEBHOOK") or (Path.home() / ".lark_webhook").exists():
            targets.append("lark")
        if (os.environ.get("TG_BOT_TOKEN") and os.environ.get("TG_CHAT_ID")) or \
           (Path.home() / ".tg_meitou.json").exists():
            targets.append("telegram")

    if not targets:
        print("WARNING: No push targets configured. Report printed to stdout only.")
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
        print(content)
        return {"stdout": True}

    results = {}
    for target in targets:
        try:
            if target == "lark":
                results["lark"] = send_to_lark(content, title)
                print(f"Lark: sent OK")
            elif target == "telegram":
                results["telegram"] = send_to_telegram(content, title)
                print(f"Telegram: sent OK")
            else:
                print(f"Unknown target: {target}")
        except Exception as e:
            results[target] = {"error": str(e)}
            print(f"{target}: FAILED - {e}")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 push_notify.py <message> [--target lark|telegram] [--title 'title']")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="Message content (or @filename to read from file)")
    parser.add_argument("--target", action="append", help="Push target (lark, telegram)")
    parser.add_argument("--title", default="美投每日投研报告")
    args = parser.parse_args()

    msg = args.message
    if msg.startswith("@"):
        msg = Path(msg[1:]).read_text()

    push(msg, title=args.title, targets=args.target)
