#!/usr/bin/env python3
"""
微信公众号文章阅读器

策略：用移动端 UA 绕过微信桌面端验证码拦截
改进：更好的时间提取、去重段落、嵌套 section 处理、JSON 输出
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import sys
from datetime import datetime

# 多个移动端 UA 轮换，降低被封概率
USER_AGENTS = [
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    # WeChat internal browser (最不容易被拦)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47(0x1800302f) NetType/WIFI Language/zh_CN",
]


def fetch_article(url, ua_index=2):
    """尝试用多个 UA 抓取文章，被拦截自动轮换"""
    for i in range(len(USER_AGENTS)):
        idx = (ua_index + i) % len(USER_AGENTS)
        headers = {
            "User-Agent": USER_AGENTS[idx],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://mp.weixin.qq.com/",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            resp.encoding = "utf-8"
            if "环境异常" in resp.text or "完成验证" in resp.text:
                if i < len(USER_AGENTS) - 1:
                    continue
                else:
                    return None, "所有 UA 均被拦截，微信反爬触发"
            return resp.text, None
        except requests.RequestException as e:
            if i < len(USER_AGENTS) - 1:
                continue
            return None, str(e)
    return None, "未知错误"


def extract_title(soup):
    tag = soup.find("h1", class_="rich_media_title")
    if tag:
        t = tag.get_text(strip=True)
        if t:
            return t
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return meta["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return "未找到标题"


def extract_author(soup, html):
    tag = soup.find("a", class_=re.compile(r"rich_media_meta.*nickname"))
    if tag:
        return tag.get_text(strip=True)
    tag = soup.find("span", class_=re.compile(r"rich_media_meta.*nickname"))
    if tag:
        return tag.get_text(strip=True)
    m = re.search(r'var\s+nickname\s*=\s*["\']([^"\']+)', html)
    if m:
        return m.group(1).strip()
    meta = soup.find("meta", property="og:article:author")
    if meta and meta.get("content"):
        return meta["content"].strip()
    return "未知作者"


def extract_publish_time(soup, html):
    tag = soup.find(id="publish_time")
    if tag:
        t = tag.get_text(strip=True)
        if t:
            return t
    for pattern in [
        r'var\s+publish_time\s*=\s*"([^"]+)"',
        r'"publish_time"\s*:\s*"([^"]+)"',
        r'var\s+ct\s*=\s*"(\d+)"',
    ]:
        m = re.search(pattern, html)
        if m:
            val = m.group(1)
            if val.isdigit() and len(val) == 10:
                return datetime.fromtimestamp(int(val)).strftime("%Y-%m-%d %H:%M")
            return val
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"].strip()
    return "未知时间"


def extract_content(soup):
    content_div = soup.find("div", class_="rich_media_content")
    if not content_div:
        return "", []

    for tag in content_div(["script", "style", "noscript"]):
        tag.decompose()

    seen = set()
    paragraphs = []
    for el in content_div.find_all(["p", "h2", "h3", "h4", "blockquote"]):
        text = el.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if text in seen:
            continue
        is_substring = False
        for existing in seen:
            if text in existing:
                is_substring = True
                break
        if is_substring:
            continue
        seen.add(text)
        if el.name in ("h2", "h3", "h4"):
            text = f"## {text}"
        paragraphs.append(text)

    images = []
    for img in content_div.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if src and not src.startswith("data:"):
            images.append(src)

    return "\n\n".join(paragraphs), images


def parse(url):
    html, err = fetch_article(url)
    if err:
        return {"error": err, "url": url}

    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    author = extract_author(soup, html)
    publish_time = extract_publish_time(soup, html)
    content, images = extract_content(soup)

    if not content:
        return {"error": "正文为空，可能被反爬拦截或文章已删除", "url": url}

    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
        "word_count": len(content),
        "images_count": len(images),
        "images": images[:10],
        "url": url,
        "parsed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 wechat_reader.py <URL> [--json] [--save FILE] [--full]")
        sys.exit(1)

    url = sys.argv[1]
    json_mode = "--json" in sys.argv
    full_mode = "--full" in sys.argv
    save_file = None
    if "--save" in sys.argv:
        idx = sys.argv.index("--save")
        save_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    result = parse(url)

    if json_mode:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"解析失败: {result['error']}")
            sys.exit(1)
        print("=" * 70)
        print(f"  {result['title']}")
        print(f"  {result['author']}  |  {result['publish_time']}  |  {result['word_count']}字  |  {result['images_count']}图")
        print("=" * 70)
        content = result["content"]
        if not full_mode and len(content) > 2000:
            print(content[:2000])
            print(f"\n... (截断，共 {len(content)} 字，用 --full 查看全文)")
        else:
            print(content)
        print("=" * 70)

    if save_file:
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {save_file}")


if __name__ == "__main__":
    main()
