---
name: meitou-daily
version: "1.0.0"
description: "美投每日投研助手 - 自动读取jdbinvesting.com新内容（视频、交易、问答），生成投资日报并推送到Lark/Telegram。支持股票行情查询、视频内容摘要、社区动态追踪。"
argument-hint: "meitou, 美投日报, 美投行情 NVDA TSLA"
allowed-tools: Bash, Read, Write, Agent, WebFetch
user-invocable: true
author: lambertlin
license: MIT
metadata:
  openclaw:
    emoji: "📈"
    requires:
      bins:
        - python3
        - curl
      pip:
        - boto3
        - warrant-lite
      env:
        - MEITOU_USERNAME
        - MEITOU_PASSWORD
      optionalEnv:
        - LARK_WEBHOOK
        - TG_BOT_TOKEN
        - TG_CHAT_ID
    primaryEnv: MEITOU_USERNAME
    files:
      - "scripts/*"
    tags:
      - investing
      - us-stocks
      - daily-report
      - chinese
      - graphql
      - lark
      - telegram
      - automation
      - research
---

# 美投每日投研助手 (Meitou Daily Research Agent)

从美投平台(jdbinvesting.com)自动抓取最新投资内容，生成结构化投研日报，推送到Lark/Telegram。

## Script Location

```bash
SKILL_DIR="$(dirname "$(find ~/.claude/skills -name SKILL.md -path '*/meitou-daily/*' 2>/dev/null | head -1)")"
```

## Prerequisites

### 1. Python 依赖

```bash
pip3 install --break-system-packages boto3 warrant-lite
```

### 2. 美投账号配置

```bash
# 方式一：环境变量
export MEITOU_USERNAME="your_email@example.com"
export MEITOU_PASSWORD="your_password"

# 方式二：配置文件（推荐）
cat > ~/.meitou_credentials.json << 'EOF'
{"username": "your_email@example.com", "password": "your_password"}
EOF
chmod 600 ~/.meitou_credentials.json
```

### 3. 推送配置（可选）

**Lark/飞书：**
```bash
echo "https://open.larksuite.com/open-apis/bot/v2/hook/YOUR_WEBHOOK" > ~/.lark_webhook
chmod 600 ~/.lark_webhook
```

**Telegram：**
```bash
cat > ~/.tg_meitou.json << 'EOF'
{"bot_token": "YOUR_BOT_TOKEN", "chat_id": "YOUR_CHAT_ID"}
EOF
chmod 600 ~/.tg_meitou.json
```

## When This Skill Activates

- 用户说 "美投日报"、"美投报告"、"meitou daily"、"/meitou-daily"
- 用户说 "美投行情"、"美投最新视频"、"美投社区动态"
- 用户要求查看美投平台的任何内容
- 定时触发（配合 /schedule 使用）

## Workflow

### 模式一：完整每日投研报告

**严格按以下步骤执行：**

#### Step 1: 获取数据

```bash
cd "$SKILL_DIR/scripts"
python3 -c "
from meitou_client import build_daily_digest
import json
digest = build_daily_digest(since_hours=24, stock_tickers=['NVDA','TSLA','META','MSFT','AAPL','AMZN'])
print(json.dumps(digest, indent=2, ensure_ascii=False))
" > /tmp/meitou_digest.json
```

#### Step 2: 生成报告

Claude 读取 `/tmp/meitou_digest.json`，按以下结构生成中文投研日报：

**报告模板：**

```markdown
# 美投每日投研报告 - YYYY年MM月DD日

## 一、今日行情速览
| 股票 | 价格 | 涨跌幅 | PE |
|------|------|--------|-----|
| NVDA | $xxx | +x.x% | xx |
...

## 二、今日新视频 (N条)
### 1. [视频标题]
- Ticker: XXX | 发布时间: xx:xx
- 核心观点: [从richText提取的1-3句核心论点]
- 互动: 👍xx | 💬xx
- 链接: [shareableLink]

## 三、社区交易动态
- [交易者] [方向] [标的] - [摘要]
...

## 四、社区热门问答
- Q: [问题标题]
  摘要: [...]
...

## 五、AI投研观察 (Claude分析)
基于今天的内容，Claude提供的跨视频/跨话题洞察：
- [综合分析]
- [值得关注的信号]
- [潜在的投资机会/风险]
```

#### Step 3: 推送

```bash
python3 "$SKILL_DIR/scripts/push_notify.py" "@/tmp/meitou_report.md" --title "美投日报 $(date +%Y-%m-%d)"
```

### 模式二：快速查询

用户可直接查询特定信息，Claude 调用对应 API：

```bash
cd "$SKILL_DIR/scripts"

# 股票行情
python3 -c "from meitou_client import get_stock_quote; import json; print(json.dumps(get_stock_quote('NVDA'), indent=2))"

# 最新视频
python3 -c "from meitou_client import get_latest_videos; import json; print(json.dumps(get_latest_videos(since_hours=48), indent=2, ensure_ascii=False))"

# 视频详情（含正文）
python3 -c "from meitou_client import get_video_detail, extract_rich_text; import json; v = get_video_detail('PSYlP-TOFU'); print(v['title']); print(extract_rich_text(v.get('richText','')))"

# 话题列表
python3 -c "from meitou_client import get_topics; import json; print(json.dumps(get_topics(), indent=2, ensure_ascii=False))"

# 搜索视频
python3 -c "from meitou_client import search_videos; import json; print(json.dumps(search_videos('特斯拉'), indent=2, ensure_ascii=False))"
```

### 模式三：定时推送（配合 /schedule）

```
/schedule 每天早上9点运行 /meitou-daily
```

## Report Style Guide

- 语言：**中文**，专业但易读
- 行情数据精确到小数点后两位
- 视频内容提取核心论点，不是简单复制desc
- AI观察部分要有跨内容的综合分析能力，提出非显而易见的洞察
- 如果某支持的股票在美投没有数据（返回null），跳过不显示
- richText 是 Slate.js JSON，用 `extract_rich_text()` 转纯文本后再分析

---

## API Reference (逆向工程字典)

> 以下是从 jdbinvesting.com 前端 JS bundle 逆向提取的完整 GraphQL API。
> 认证方式: AWS Cognito SRP -> Bearer access_token
> GraphQL 端点: `https://gql.jdbinvesting.com/gqlrealauth` (认证) / `gqlrealanon` (匿名)

### Queries

#### 股票行情
```graphql
# 单支股票行情
query LatestStockQuoteInfo($ticker: String!) {
    latestStockQuoteInfo(ticker: $ticker) {
        change changePercent currentPrice high low open previousClose
        peRatio createdAt
        fiftyTwoWeek { high low }
    }
}
# 已验证可用: NVDA, TSLA, META, MSFT
# 部分ticker可能返回null (AAPL, GOOGL, AMZN, QQQ, SPY)

# 股票图表数据
query StockQuoteGraphInfo($ticker: String!, $type: String!) {
    stockQuoteGraphInfo(ticker: $ticker, type: $type) { ... }
}

# 股票评级
query Query($numMonths: Int!, $ticker: String!) {
    listStockRatings(numMonths: $numMonths, ticker: $ticker) { ... }
}

# 科技导航页股票列表
query ListStocksInTechNavPage($id: String!) {
    listStocksInTechNavPage(id: $id) { ... }
}
```

#### 视频内容 (Tofu体系)
```graphql
# 视频列表 (分页+缓存)
query CacheableTofuList(
    $cid: String! $page: Int!
    $videoForMagicRootPageType: VideoForMagicRootPageType!
) {
    cacheableTofuList(cid: $cid, page: $page, videoForMagicRootPageType: $videoForMagicRootPageType) {
        cid page totalHits totalPages
        data { id title desc createdAt ticker payingStatus tofuType imageUrl shareableLink
               interactionStatus { numComment numLike } }
    }
}
# videoForMagicRootPageType enum: LATEST, RECOMMENDED (已验证)

# 最新视频列表 (按时间)
query ListTofuVideoList($key: String!, $returnNum: Int!, $parentTopicId: String, $timeSince: String) {
    listTofu(key: $key, returnNum: $returnNum, parentTopicId: $parentTopicId, timeSince: $timeSince) {
        id title desc createdAt ticker payingStatus tofuType imageUrl shareableLink sTags richText
        interactionStatus { numComment numLike }
        accessInfoVideo { playableID }
    }
}

# 视频详情 (含完整richText正文)
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

# 收藏列表
query CacheableBookmarkableList($bookmarkableType: String!, $page: Int!, $uid: String!, $hitsPerPage: Int!) {
    cacheableBookmarkableList(...) { ... }
}

# 笔记列表
query NoteForVideoList($page: Int!, $uid: String!) {
    noteForVideoList(page: $page, uid: $uid) { ... }
}

# 搜索视频
query Query($input: UniversalSearchInput!) {
    universalSearchTofu(input: $input) {
        id title desc ticker createdAt payingStatus shareableLink
    }
}
```

#### 话题/专题 (MagicTopic)
```graphql
# 话题列表
query MagicTopicsList($topicType: String!) {
    magicTopicsList(topicType: $topicType) {
        id name desc imageUrl linkTo shareableLink watched
        totalTofuVideosInTopic
        userWatchingStatus { numVideoWatchedInTopic percentVideoWatchedInTopic }
    }
}
# topicType: "stock" 返回71个话题

# 魔法页面 (多态: ROOT, TOPICS, TOPIC_DETAIL, COMING_SOON)
query MagicPageGet($cid: String!, $pageType: String!, $subjectID: String!) {
    magicPageGet(cid: $cid, pageType: $pageType, subjectID: $subjectID) {
        id pageType
        ... on MagicPageRoot { giantTopics { ...MagicTopicInfo } recommendedVideos { ...TofuInfo } }
        ... on MagicPageTopics { topics { ...MagicTopicInfo } }
        ... on MagicPageTopicDetail { allVideos { ...TofuInfo } mustReads { ...TofuInfo } news { ...TofuInfo } }
    }
}
```

#### 频道/订阅
```graphql
# 频道列表
query Query($id: String!) {
    chanList(id: $id) {
        id channels { id name pathName desc numSubscribers showNumSubscribers }
    }
}
# id: "meitou"

# 频道详情 (含订阅状态)
query Query($cid: String!, $pathName: String!) {
    chanInfo(cid: $cid, pathName: $pathName) {
        channel {
            id name numSubscribers
            purchaseStatus { followedAt subscribedServiceStatus { shortCode purchaseStatus } }
            unlockedMTServiceCodes
        }
    }
}
# cid: "18e1deb7-87a4-5ded-9c49-73e4356621b6", pathName: "meitouquan"

# 套餐信息
query Query($packageCode: String!) {
    meitouPackageInfo(id: $packageCode) { mtPackage { ...SubMeitouPackageInfo } }
}

# 商品列表
query Query($productListCid: String!, $productListPType: ProductType!, $includeOffShelf: Boolean!) {
    cacheableProductList(cid: $productListCid, pType: $productListPType, includeOffShelf: $includeOffShelf) { ... }
}

# 支付历史
query Query($cid: String!, $page: Int!) {
    cacheableSearchablePaymentHistoryChannel(cid: $cid, page: $page) {
        data { amountPaidInDollar desc itemName cusNickname createdAt }
        page totalPages
    }
}
```

#### 社区互动
```graphql
# 交易帖列表
query Query($cid: String!, $page: Int!, $positionType: String, $tags: String, $keywords: String) {
    cacheableSearchableHandanList(cid: $cid, page: $page, positionType: $positionType, tags: $tags, keywords: $keywords) {
        data { id createdAt text author { nickname } tradingInfo { ticker direction } numLike numComment }
        page totalPages
    }
}

# 交易Dashboard
query Query($cid: String!) {
    dashboardList(cid: $cid) { cid boards { cid } }
}

# 单条帖子详情
query Query($postId: String!) {
    handanInfo(postID: $postId) { ... }
}

# 问答列表
query Query($cid: String!, $page: Int!, $keywords: String, $tags: String, $category: String) {
    cacheableSearchableQuestionList(cid: $cid, page: $page, keywords: $keywords, category: $category) {
        data { id createdAt qTitle qSummary tags category }
        page totalPages
    }
}

# 通知历史
query NotiHistoryFetch($uid: String!, $cursor: String) {
    notiHistoryFetch(uid: $uid, cursor: $cursor) { ... }
}

# PRO统计
query GetTofuProStats { getTofuProStats { __typename } }  # MTProStats type
query GetWeeklyTofuSugs { getWeeklyTofuSugs { __typename } }  # WeeklyTofuSugPayload type
query SubSections { subSections { ... } }  # 动态首页板块
```

### Mutations

#### 用户
```graphql
mutation UpdateProfile($input: UpdateProfileInput!) { updateProfile(input: $input) { profileID uid ... } }
mutation ClaimWelcomePack { claimWelcomePack }
mutation ClaimProfile($input: ClaimProfileInput!) { claimProfile(input: $input) { ... } }
mutation FeedbackInterviewSubmit($input: feedbackInterviewSubmitInput!) { feedbackInterviewSubmit(input: $input) { bool } }
mutation UserMutation($input: UserUpdateInput!) { userUpdate(input: $input) { ... } }
```

#### 内容交互
```graphql
mutation PostReact($input: PostReactInput!) { postReact(input: $input) { ... } }
mutation Bookmark($input: BookmarkInput!) { bookmark(input: $input) { ... } }
mutation IncTofuVideoViewCount($input: IncTofuVideoViewCountInput!) { incTofuVideoViewCount(input: $input) { ... } }
mutation SetTopicWatch($input: SetTopicWatchInput!) { setTopicWatch(input: $input) { ... } }
mutation DismissUnreadContentByCategory($input: DismissUnreadContentByCategoryInput!) { dismissUnreadContentByCategory(input: $input) }
```

#### 交易
```graphql
mutation Mutation($input: PositionThreadOpenInput!) { positionThreadOpen(input: $input) { post { ... } } }
mutation Mutation($input: PositionThreadAdjustInput!) { positionThreadAdjust(input: $input) { ... } }
mutation Mutation($input: PositionThreadCloseInput!) { positionThreadClose(input: $input) { post { ... } } }
mutation Mutation($input: PositionThreadFollowInput!) { positionThreadFollow(input: $input) { ... } }
mutation Mutation($input: CreatePTDashboardInput!) { createPTDashboard(input: $input) { ... } }
```

#### 问答
```graphql
mutation QuestionAskMutation($input: AskQuestionInput!) { questionAsk(input: $input) { ... } }
mutation AnswerQuestionMutation($input: AnswerQuestionInput!) { answerQuestion(input: $input) { ... } }
```

#### 频道
```graphql
mutation ChannelFollow($input: ChannelFollowInput!) { channelFollow(input: $input) { ... } }
mutation ChannelUpdateMutation($input: ChannelUpdateInput!) { channelUpdate(input: $input) { ... } }
```

#### 通知
```graphql
mutation ToggleNotiItem($input: ToggleNotiItemInput!) { toggleNotiItem(input: $input) { ... } }
mutation NotiHistoryMarkAllAsRead($input: ...) { notiHistoryMarkAllAsRead(input: $input) }
```

#### 订阅/支付
```graphql
mutation ToggleStripeSubscriptionAutoRenew($input: ...) { toggleStripeSubscriptionAutoRenew(input: $input) { ... } }
# Stripe endpoints (REST, not GraphQL):
# POST https://gql.jdbinvesting.com/stripe/create-checkout-session
# POST https://gql.jdbinvesting.com/stripe/create-subscription-session
# POST https://gql.jdbinvesting.com/stripe/create-customer-portal-session
```

### Key Fragments

```graphql
fragment TofuInfo on Tofu {
    createdAt desc sTags richText richImg { src thumbnail }
    id imageUrl link payingStatus title tofuType ticker shareableLink
    interactionStatus { numComment numLike }
    accessInfoVideo { playableID }
    userStatus { lastWatchedTo watchedTimes }
}

fragment MagicTopicInfo on MagicTopic {
    desc id imageUrl name presentationalType linkTo shareableLink watched
    previewTofus { ...TofuInfo }
    totalTofuVideosInTopic
    userWatchingStatus { numVideoWatchedInTopic percentVideoWatchedInTopic }
}

fragment HandanPostInfo on HandanPost {
    id createdAt text
    author { ...AuthorInfo }
    tradingInfo { ticker direction }
    numLike numComment
}

fragment PositionThreadInfo on PositionThread {
    positions { ticker price quantity direction }
    tradingPlanInfo { planText riskManagement }
}

fragment StockQuote_LatestStockQuoteInfo on StockQuote {
    change changePercent createdAt currentPrice high low open previousClose
    peRatio id
    fiftyTwoWeek { high low }
}
```

### Architecture Notes

- **Tech Stack**: Next.js App Router + Apollo Client + AWS Amplify (Cognito) + S3
- **内容系统内部代号**: "Tofu" = 视频/文章内容单元
- **认证流**: Cognito SRP -> access_token (24h有效) -> Bearer header on GraphQL
- **两个GQL端点**: `gqlrealauth` (需token) / `gqlrealanon` (匿名，功能受限)
- **richText格式**: Slate.js JSON，需解析提取文本
- **S3 Bucket**: `mtweb438232a9ccab4d00b91bcb87502adcf2112223-prod` (us-east-2)
