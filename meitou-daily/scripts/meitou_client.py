"""
美投 (jdbinvesting.com) GraphQL API Client

Reverse-engineered from Next.js frontend bundles.
Auth: AWS Cognito SRP via warrant-lite -> Bearer access_token on GraphQL.
"""

import json
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
COGNITO_REGION = "us-east-2"
COGNITO_USER_POOL_ID = "us-east-2_fnA5JNchH"
COGNITO_CLIENT_ID = "nhlt84q4sndhj5bcjq65tsg2r"

GQL_AUTH_ENDPOINT = "https://gql.jdbinvesting.com/gqlrealauth"
GQL_ANON_ENDPOINT = "https://gql.jdbinvesting.com/gqlrealanon"

TOKEN_CACHE_PATH = Path.home() / ".meitou_tokens.json"
CREDENTIALS_PATH = Path.home() / ".meitou_credentials.json"

CHANNEL_ID_MEITOU = "18e1deb7-87a4-5ded-9c49-73e4356621b6"
CHANNEL_PATH_MEITOU = "meitouquan"


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _load_credentials():
    """Load credentials from file or environment."""
    username = os.environ.get("MEITOU_USERNAME")
    password = os.environ.get("MEITOU_PASSWORD")
    if username and password:
        return username, password
    if CREDENTIALS_PATH.exists():
        creds = json.loads(CREDENTIALS_PATH.read_text())
        return creds["username"], creds["password"]
    raise RuntimeError(
        "No credentials found. Set MEITOU_USERNAME/MEITOU_PASSWORD env vars "
        f"or create {CREDENTIALS_PATH} with {{\"username\": ..., \"password\": ...}}"
    )


def _authenticate(username, password):
    """Authenticate with Cognito SRP and return tokens."""
    import boto3
    from warrant_lite import WarrantLite

    client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    wl = WarrantLite(
        username=username,
        password=password,
        pool_id=COGNITO_USER_POOL_ID,
        client_id=COGNITO_CLIENT_ID,
        client=client,
    )
    tokens = wl.authenticate_user()
    result = tokens["AuthenticationResult"]
    return {
        "access_token": result["AccessToken"],
        "id_token": result["IdToken"],
        "refresh_token": result.get("RefreshToken", ""),
        "expires_at": time.time() + result.get("ExpiresIn", 3600),
    }


def get_access_token():
    """Get a valid access token, refreshing if needed."""
    if TOKEN_CACHE_PATH.exists():
        cached = json.loads(TOKEN_CACHE_PATH.read_text())
        if cached.get("expires_at", 0) > time.time() + 300:
            return cached["access_token"]

    username, password = _load_credentials()
    tokens = _authenticate(username, password)
    TOKEN_CACHE_PATH.write_text(json.dumps(tokens))
    TOKEN_CACHE_PATH.chmod(0o600)
    return tokens["access_token"]


# ─── GraphQL Client ──────────────────────────────────────────────────────────

def gql(query, variables=None, authenticated=True):
    """Execute a GraphQL query against the meitou API."""
    endpoint = GQL_AUTH_ENDPOINT if authenticated else GQL_ANON_ENDPOINT
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    headers = ["Content-Type: application/json"]
    if authenticated:
        token = get_access_token()
        headers.append(f"Authorization: Bearer {token}")

    cmd = ["curl", "-s", "-X", "POST", endpoint]
    for h in headers:
        cmd.extend(["-H", h])
    cmd.extend(["-d", json.dumps(payload)])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    data = json.loads(result.stdout)

    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {json.dumps(data['errors'], ensure_ascii=False)}")
    return data.get("data", {})


# ─── High-level API ──────────────────────────────────────────────────────────

def get_stock_quote(ticker: str) -> dict | None:
    """Get real-time stock quote for a ticker."""
    data = gql("""
        query LatestStockQuoteInfo($ticker: String!) {
            latestStockQuoteInfo(ticker: $ticker) {
                change changePercent currentPrice high low open previousClose
                peRatio createdAt
                fiftyTwoWeek { high low }
            }
        }
    """, {"ticker": ticker})
    return data.get("latestStockQuoteInfo")


def get_stock_quotes(tickers: list[str]) -> dict:
    """Get quotes for multiple tickers."""
    results = {}
    for t in tickers:
        try:
            results[t] = get_stock_quote(t)
        except Exception:
            results[t] = None
    return results


def get_recommended_videos(page: int = 1) -> dict:
    """Get recommended video list."""
    return gql("""
        query CacheableTofuList($cid: String!, $page: Int!, $videoForMagicRootPageType: VideoForMagicRootPageType!) {
            cacheableTofuList(cid: $cid, page: $page, videoForMagicRootPageType: $videoForMagicRootPageType) {
                cid page totalHits totalPages
                data {
                    id title desc createdAt ticker payingStatus tofuType
                    imageUrl shareableLink
                    interactionStatus { numComment numLike }
                }
            }
        }
    """, {"cid": "meitou", "page": page, "videoForMagicRootPageType": "RECOMMENDED"})


def get_latest_videos(topic_id: str = None, limit: int = 10, since_hours: int = 24) -> list:
    """Get latest videos, optionally filtered by topic. since_hours filters by recency."""
    since_ts = str(int((datetime.now() - timedelta(hours=since_hours)).timestamp() * 1000))
    variables = {
        "key": "createdAt",
        "returnNum": limit,
        "timeSince": since_ts,
    }
    if topic_id:
        variables["parentTopicId"] = topic_id

    data = gql("""
        query ListTofuVideoList(
            $key: String!
            $returnNum: Int!
            $parentTopicId: String
            $timeSince: String
        ) {
            listTofu(
                key: $key
                returnNum: $returnNum
                parentTopicID: $parentTopicId
                timeSince: $timeSince
            ) {
                tofuList {
                    id title viewCount ticker shareableLink sTags
                    parentTopicNameCN parentTopicID imageUrl
                    durationInSeconds createdAt
                    userStatus { liked lastWatchedTo }
                    interactionStatus { numLike numComment }
                }
                timeUntil
            }
        }
    """, variables)
    payload = data.get("listTofu", {})
    return payload.get("tofuList", []) if isinstance(payload, dict) else []


def get_video_detail(tofu_id: str) -> dict:
    """Get full video detail including rich text content."""
    data = gql("""
        query TofuInfoExtended($id: String!) {
            tofuInfoExtended(id: $id) {
                tofu {
                    id title desc createdAt ticker payingStatus tofuType
                    richText sTags imageUrl shareableLink link
                    interactionStatus { numComment numLike }
                    accessInfoVideo { playableID }
                    userStatus { lastWatchedTo watchedTimes }
                }
            }
        }
    """, {"id": tofu_id})
    return data.get("tofuInfoExtended", {}).get("tofu", {})


def get_topics(topic_type: str = "stock") -> list:
    """Get all topic categories."""
    data = gql("""
        query MagicTopicsList($topicType: String!) {
            magicTopicsList(topicType: $topicType) {
                id name desc imageUrl linkTo shareableLink watched
                totalTofuVideosInTopic
            }
        }
    """, {"topicType": topic_type})
    return data.get("magicTopicsList", [])


def get_channel_info() -> dict:
    """Get meitou channel info including subscription status."""
    data = gql("""
        query Query($cid: String!, $pathName: String!) {
            chanInfo(cid: $cid, pathName: $pathName) {
                cid pathName
                channel {
                    id name numSubscribers
                    purchaseStatus {
                        followedAt
                        subscribedServiceStatus { shortCode purchaseStatus }
                    }
                    unlockedMTServiceCodes
                }
            }
        }
    """, {"cid": CHANNEL_ID_MEITOU, "pathName": CHANNEL_PATH_MEITOU})
    return data.get("chanInfo", {})


def get_channel_list() -> list:
    """Get all available channels."""
    data = gql("""
        query Query($id: String!) {
            chanList(id: $id) {
                id
                channels {
                    id name pathName desc numSubscribers showNumSubscribers
                }
            }
        }
    """, {"id": "meitou"})
    return data.get("chanList", {}).get("channels", [])


def get_community_posts(page: int = 1, position_type: str = None) -> dict:
    """Get community trading posts (handan)."""
    variables = {"cid": "meitou", "page": page}
    if position_type:
        variables["positionType"] = position_type

    return gql("""
        query Query($cid: String!, $page: Int!, $positionType: String) {
            cacheableSearchableHandanList(cid: $cid, page: $page, positionType: $positionType) {
                cid page totalPages
                data {
                    id createdAt text
                    author { nickname avatarUrl }
                    tradingInfo { ticker direction }
                    numLike numComment
                }
            }
        }
    """, variables)


def get_questions(page: int = 1, category: str = None) -> dict:
    """Get community Q&A list."""
    variables = {"cid": "meitou", "page": page}
    if category:
        variables["category"] = category

    return gql("""
        query Query($cid: String!, $page: Int!, $category: String) {
            cacheableSearchableQuestionList(cid: $cid, page: $page, category: $category) {
                cid page totalPages
                data {
                    id createdAt qTitle qSummary
                    tags category
                }
            }
        }
    """, variables)


def search_videos(keyword: str) -> dict:
    """Search videos by keyword."""
    return gql("""
        query Query($input: UniversalSearchInput!) {
            universalSearchTofu(input: $input) {
                id title desc ticker createdAt payingStatus
                shareableLink
            }
        }
    """, {"input": {"keyword": keyword}})


def extract_rich_text(rich_text_json: str) -> str:
    """Convert Slate.js richText JSON to plain text."""
    if not rich_text_json:
        return ""
    try:
        nodes = json.loads(rich_text_json)
    except (json.JSONDecodeError, TypeError):
        return str(rich_text_json)

    texts = []
    def walk(node):
        if isinstance(node, dict):
            if "text" in node:
                texts.append(node["text"])
            for child in node.get("children", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(nodes)
    return "\n".join(t for t in texts if t.strip())


# ─── Daily Report Builder ────────────────────────────────────────────────────

def build_daily_digest(since_hours: int = 24, stock_tickers: list[str] = None) -> dict:
    """
    Build a complete daily digest of meitou content.
    Returns structured data for report generation.

    Strategy: Use recommended videos + per-video detail as primary source,
    since listTofu may be restricted on some account tiers.
    """
    if stock_tickers is None:
        stock_tickers = ["NVDA", "TSLA", "META", "MSFT"]

    digest = {
        "generated_at": datetime.now().isoformat(),
        "period_hours": since_hours,
    }

    # 1. Stock quotes
    digest["stock_quotes"] = get_stock_quotes(stock_tickers)

    # 2. Recommended videos (primary content source - always works)
    try:
        rec = get_recommended_videos()
        rec_list = rec.get("cacheableTofuList", {}).get("data", [])
        digest["recommended_videos"] = rec_list
    except Exception as e:
        rec_list = []
        digest["recommended_videos"] = []
        digest["recommended_videos_error"] = str(e)

    # 3. Enrich top recommended videos with full richText
    enriched = []
    for vid in rec_list[:5]:
        try:
            detail = get_video_detail(vid["id"])
            if detail:
                detail["_plain_text"] = extract_rich_text(detail.get("richText", ""))[:2000]
                enriched.append(detail)
        except Exception:
            enriched.append(vid)
    digest["enriched_videos"] = enriched

    # 4. Latest videos via listTofu (may be empty on trial accounts)
    try:
        digest["latest_videos"] = get_latest_videos(since_hours=since_hours)
    except Exception as e:
        digest["latest_videos"] = []
        digest["latest_videos_error"] = str(e)

    # 5. Community posts
    try:
        posts = get_community_posts()
        digest["community_posts"] = posts.get("cacheableSearchableHandanList", {}).get("data", [])
    except Exception as e:
        digest["community_posts"] = []
        digest["community_posts_error"] = str(e)

    # 6. Q&A
    try:
        questions = get_questions()
        digest["questions"] = questions.get("cacheableSearchableQuestionList", {}).get("data", [])
    except Exception as e:
        digest["questions"] = []
        digest["questions_error"] = str(e)

    # 7. Topics snapshot (detect new/trending topics)
    try:
        digest["topics"] = get_topics()
    except Exception as e:
        digest["topics"] = []
        digest["topics_error"] = str(e)

    # 8. Subscription status
    try:
        digest["subscription"] = get_channel_info()
    except Exception as e:
        digest["subscription_error"] = str(e)

    return digest


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing meitou API client...")
        token = get_access_token()
        print(f"Auth OK. Token: {token[:50]}...")

        quote = get_stock_quote("NVDA")
        print(f"\nNVDA: ${quote['currentPrice']} ({quote['changePercent']}%)")

        topics = get_topics()
        print(f"\nTopics: {len(topics)} found")
        for t in topics[:5]:
            print(f"  {t['name']} ({t['totalTofuVideosInTopic']} videos)")

        print("\nAll tests passed!")

    elif len(sys.argv) > 1 and sys.argv[1] == "digest":
        tickers = sys.argv[2].split(",") if len(sys.argv) > 2 else None
        hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
        digest = build_daily_digest(since_hours=hours, stock_tickers=tickers)
        print(json.dumps(digest, indent=2, ensure_ascii=False))

    else:
        print("Usage:")
        print("  python3 meitou_client.py test              # Test API connectivity")
        print("  python3 meitou_client.py digest [tickers] [hours]  # Build daily digest")
        print("    tickers: comma-separated, e.g. NVDA,TSLA,META")
        print("    hours: lookback period (default: 24)")
