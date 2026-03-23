# Research OS 周报生成器

每周模型运行后，自动拉取三大模型输出，生成机构级宏观研究周报，发送到飞书 LAC 工作群。

## Script Location

脚本位于本 Skill 目录下的 `scripts/`：
```bash
SKILL_DIR="$(dirname "$(find ~/.claude/skills -name SKILL.md -path '*/weekly-report/*' 2>/dev/null | head -1)")"
```

## Before You Start

| 配置项 | 说明 | 设置方式 |
|--------|------|---------|
| **飞书 Webhook** | LAC 工作群的机器人 Webhook URL | `echo "https://open.larksuite.com/open-apis/bot/v2/hook/xxx" > ~/.lark_webhook && chmod 600 ~/.lark_webhook` |
| **Research OS API** | 后端 API 地址 | 默认 `http://202.81.229.139:8000`，可通过 `--api-url` 覆盖 |

## Quick Start

```bash
# 1. 拉取最新模型数据
python3 $SKILL_DIR/scripts/fetch_model_data.py

# 2. [Claude 根据下方风格指南生成周报]

# 3. 发送到飞书
python3 $SKILL_DIR/scripts/send_to_lark.py --webhook @~/.lark_webhook --markdown --title "Research OS 周报 YYYY-MM-DD" "报告内容"
```

## When This Skill Activates

- 用户说 "生成周报"、"写周报"、"发周报"
- 用户说 "run weekly report"、"/weekly-report"
- 每周五模型运行后（可配合 hook 自动触发）

## Workflow

**严格按以下步骤执行：**

### Step 1: 拉取数据

```bash
python3 $SKILL_DIR/scripts/fetch_model_data.py --api-url http://202.81.229.139:8000
```

如果连不上远程服务器，尝试本地：
```bash
python3 $SKILL_DIR/scripts/fetch_model_data.py --api-url http://localhost:8000
```

### Step 2: 生成周报

**用你（Claude）的能力**，根据拉取到的数据 + 下方的写作风格指南，生成一份完整周报。

**不是简单翻译模型输出，而是写一份有观点、有逻辑链条、有可操作建议的研究报告。**

### Step 3: 展示给用户确认

将生成的周报展示给用户，等待确认后再发送。

### Step 4: 发送到飞书

用户确认后：
```bash
python3 $SKILL_DIR/scripts/send_to_lark.py --webhook @~/.lark_webhook --markdown --title "Research OS 周报 YYYY-MM-DD" "REPORT_CONTENT"
```

如果报告太长，用 `--stdin`：
```bash
echo "REPORT_CONTENT" | python3 $SKILL_DIR/scripts/send_to_lark.py --webhook @~/.lark_webhook --markdown --stdin
```

---

## 写作风格指南（核心）

### 总体原则

你是 Agarwood Technology 的宏观研究分析师。你的读者是公司内部研究员和交易团队。报告需要：

1. **数据先行，观点明确**：先呈现事实，再给出判断，最后给可操作建议
2. **专业但不晦涩**：用准确的金融术语，但逻辑链条要清晰
3. **强调变化而非绝对值**：本周 vs 上周的边际变化是最重要的信息
4. **行动导向**：每个分析都要落到"所以呢？该怎么做？"

### 语言风格

- 使用**繁体中文**（團隊慣用語言）
- 金融术语保持英文原文：MOVE、SOFR、OAS、Steepener、Real Yield
- 语气专业直接，不用"我认为"、"可能"等含糊表述——给出明确判断
- 数据引用精确到小数点（如 "SOFR-IORB 利差 2.3bp" 而非 "利差偏低"）

### 报告结构模板

```markdown
# 📊 Agarwood 宏觀週報（MM/DD）

## 一、本週模型總覽

| 指標 | 本週 | 上週 | 變化 |
|------|------|------|------|
| 流動性評分 | XX/100 | XX/100 | ±X |
| 風險燈號 | 🟢/🟡/🔴 | 🟢/🟡/🔴 | → |
| 槓桿係數 | X.Xx | X.Xx | ±X |
| 宏觀狀態 | X | X | → |
| 美股體制 | BULL/BEAR/... | ... | → |

> 一句話摘要：用 1-2 句話概括本週最核心的變化和結論。

## 二、美元流動性（v3.0）

### 評分拆解
- **Quantity（XX%）**：ΔNet Liquidity = ±XXX億，Reserves 4W 趨勢 = 上行/下行
- **Plumbing（XX%）**：SOFR-IORB = X.Xbp → [正常/警示/紅燈]
- **Vol Gate（XX%）**：MOVE = XXX → [暢通/關注/關閘]

### 本週判讀
[2-3 段分析文字，解读三个维度的变化及其含义]

### 策略影響
- 槓桿建議：X.Xx
- 禁止操作：[如有]
- Supply Texture 修正：[如有]

## 三、宏觀環境（v4.0）

### Layer 1：利率結構
- 政策路徑：[前端鴿/鷹/不確定] — 2Y 5日變化 ±Xbp
- 曲線形態：[Bull Steep / Bear Flat / Twist 等] — 2s10s=±Xbp, 10s30s=±Xbp
- Real/BE：[四象限狀態] — 對權益的影響：[描述]
- 期限溢價：[狀態及含義]

### Layer 2：敘事校驗
- Corr(SPX, Δ10Y) 20D = ±0.XX | 60D = ±0.XX
- 解讀：[正相關=增長驅動 / 負相關=折現率衝擊 / 過渡期]

### Layer 3：風險閘門
| 閘門 | 狀態 | 指標值 | 閾值 |
|------|------|--------|------|
| MOVE | 🟢/🟡/🔴 | XXX | 100/120 |
| SOFR-IORB | 🟢/🟡/🔴 | X.Xbp | 3/5bp |
| 信用 | 🟢/🟡/🔴 | HY OAS=XXX | 400/500 |
| 美元壓力 | 🟢/🟡/🔴 | DXY=XXX | 同步加速 |
| 背離 | 🟢/🟡/🔴 | ... | SPX vs NetLiq |

### 執行矩陣
- **Rates 表達**：[具體操作建議]
- **Equity 偏向**：[板塊建議]
- **對沖**：[需要/不需要 + 工具]
- **賣波動**：[允許/禁止]

### 糾錯系統
- 檔位：[NONE/A/B/C]
- [如觸發，說明原因和建議動作]

## 四、美股體制與配置（v1.0）

- 當前體制：[BULL/LATE_CYCLE/BEAR/EARLY_RECOVERY/TRANSITION]
- 加權評分：±X.XX
- 配置：股票 X% | 債券 X% | 現金 X%
- 板塊：超配 [XXX]，低配 [XXX]
- 風險：SPX 回撤 X.X% → [風險等級]

## 五、本週結論與行動要點

1. **最重要的一件事**：[本週最關鍵的邊際變化]
2. **倉位建議**：[基於三個模型的綜合建議]
3. **需要關注的風險**：[下週的關鍵事件/數據/閾值]
4. **下週觀察重點**：[哪些指標即將觸及閾值？]

---
*由 Research OS 自動生成 | 數據截至 YYYY-MM-DD | 模型版本: Liquidity v3.0 / Macro v4.0 / Equity v1.0*
```

### 分析深度要求

**不要只列数据，要写出逻辑链条：**

❌ 错误示范：
> MOVE = 105，处于关注区间。SOFR-IORB = 2.1bp，正常。

✅ 正确示范：
> MOVE 從上週的 92 回升至 105，進入 100-120 的關注區間，反映債市對下週 CPI 數據的不確定性正在定價。但 SOFR-IORB 僅 2.1bp，銀行間資金面依然寬鬆，顯示這更多是「預防性避險」而非「結構性壓力」。結合 Reserves 4W 趨勢仍為上行，我們傾向認為這是暫時性波動而非趨勢轉向。策略上，Vol Gate 尚未關閘，但建議收縮賣波動的倉位規模，等 CPI 落地後再加碼。

### 关于"上周数据"

如果无法获取上周数据（首次运行或缓存过期），在"变化"列写 "—"，并在报告中注明：
> 注：本週為系統首次運行/數據缺失，暫無週環比數據。下週起將自動追蹤變化。

### 告警处理

如果模型输出包含 CRITICAL 级别告警，在报告**最顶部**增加红色警告框：
```markdown
> ⚠️ **CRITICAL ALERT**: [告警内容]
> 建議立即核查相關倉位。
```

---

## Dependencies

```bash
pip install requests
```

## Autonomy Rules

| 动作 | 是否需要确认 |
|------|-------------|
| 拉取模型数据 | 不需要，自动执行 |
| 生成周报文本 | 不需要，自动执行 |
| 展示周报给用户 | 自动展示 |
| 发送到飞书 | **必须等用户确认** |

**绝对不要在用户确认前发送到飞书。** 研究报告发到工作群是不可撤回的。
