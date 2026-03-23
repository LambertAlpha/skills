#!/usr/bin/env python3
"""
从 Research OS API 拉取最新模型输出，格式化为结构化 JSON 供 Claude 生成周报。
支持拉取流动性 v3.0 + 宏观 v4.0 + 美股 v1.0 三个模型的完整输出。

用法:
    python3 scripts/fetch_model_data.py --api-url http://202.81.229.139:8000
    python3 scripts/fetch_model_data.py --api-url http://localhost:8000 --json
"""
import argparse
import json
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)


def fetch_latest(api_url: str) -> dict:
    """拉取最新综合模型输出"""
    resp = requests.get(f"{api_url}/api/model/latest", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"API error: {data.get('error', 'unknown')}")
    return data["data"]


def fetch_equity(api_url: str) -> dict | None:
    """拉取最新美股模型输出"""
    try:
        resp = requests.get(f"{api_url}/api/equity", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except Exception:
        pass
    return None


def format_readable(combined: dict, equity: dict | None) -> str:
    """格式化为可读文本（供 Claude 阅读）"""
    lines = []
    lines.append("=" * 60)
    lines.append("Research OS 模型数据快照")
    lines.append(f"拉取时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    # === 流动性模型 ===
    liq = combined.get("liquidity", {})
    lines.append("")
    lines.append("【一、美元流动性模型 v3.0】")
    lines.append(f"  评分: {liq.get('liquidity_score', 'N/A')}/100")
    lines.append(f"  风险灯号: {liq.get('risk_light', 'N/A')}")
    lines.append(f"  杠杆系数: {liq.get('leverage_coef', 'N/A')}")
    lines.append(f"  一票否决: {'触发' if liq.get('hard_stop_triggered') else '未触发'}")
    if liq.get("hard_stop_reason"):
        lines.append(f"    原因: {liq['hard_stop_reason']}")
    lines.append(f"  Supply Texture 修正: {liq.get('supply_texture_adjustment', 0)}")
    lines.append(f"  RRP 缓冲放大: {'是' if liq.get('rrp_buffer_amplified') else '否'}")

    # 分项得分
    for comp in liq.get("component_scores", []):
        lines.append(f"  {comp.get('category', '')}/{comp.get('name', '')}: "
                      f"得分={comp.get('score', 0):.0f} (权重{comp.get('weight', 0) * 100:.0f}%) "
                      f"- {comp.get('label', '')}")

    # 禁止策略
    forbidden = liq.get("forbidden_strategies", [])
    if forbidden:
        lines.append(f"  禁止策略: {', '.join(forbidden)}")

    # === 宏观模型 ===
    macro = combined.get("macro", {})
    lines.append("")
    lines.append("【二、宏观主模型 v4.0】")

    macro_state = macro.get("macro_state", {})
    lines.append(f"  宏观状态: {macro_state.get('code', 'N/A')} - {macro_state.get('name', '')}")

    # Layer 1
    l1 = macro.get("layer1", {})
    pp = l1.get("policy_path", {})
    cs = l1.get("curve_structure", {})
    rb = l1.get("real_be", {})
    tp = l1.get("term_premium", {})
    lines.append(f"  Layer 1 (利率结构):")
    lines.append(f"    政策路径: {pp.get('label', 'N/A')} ({pp.get('interpretation', '')})")
    lines.append(f"    曲线: 2s10s={cs.get('curve_2s10s', 'N/A')}bp, 10s30s={cs.get('curve_10s30s', 'N/A')}bp")
    lines.append(f"    曲线方向: {cs.get('direction_label', 'N/A')}")
    lines.append(f"    Real/BE: {rb.get('state', 'N/A')} - {rb.get('interpretation', '')}")
    lines.append(f"    期限溢价: {tp.get('state', 'N/A')}")

    # Layer 2
    l2 = macro.get("layer2", {})
    corr = l2.get("correlation", {})
    lines.append(f"  Layer 2 (叙事校验):")
    lines.append(f"    Corr(SPX, Δ10Y) 20D: {corr.get('corr_20d', 'N/A')}")
    lines.append(f"    Corr(SPX, Δ10Y) 60D: {corr.get('corr_60d', 'N/A')}")
    lines.append(f"    叙事状态: {corr.get('narrative_state', 'N/A')}")

    # Layer 3
    l3 = macro.get("layer3", {})
    lines.append(f"  Layer 3 (风险闸门):")
    for gate in l3.get("gates", []):
        emoji = {"open": "🟢", "closed": "🔴", "caution": "🟡", "warning": "⚠️"}.get(
            str(gate.get("status", "")).lower(), "⚪"
        )
        lines.append(f"    {emoji} {gate.get('name', 'N/A')}: {gate.get('status', 'N/A')} "
                      f"(值={gate.get('value', 'N/A')}, 阈值={gate.get('threshold', 'N/A')})")

    # 执行矩阵
    em = macro.get("execution_matrix", {})
    lines.append(f"  Layer 4 (执行矩阵):")
    lines.append(f"    Rates: {em.get('rates_action', 'N/A')}")
    lines.append(f"    Equity: {em.get('equity_sector_bias', 'N/A')} {em.get('equity_sectors', [])}")
    lines.append(f"    对冲: {'需要' if em.get('hedge_required') else '不需要'} {em.get('hedge_type', '') or ''}")
    lines.append(f"    卖波动: {'允许' if em.get('short_vol_allowed') else '禁止'}")

    # 纠错
    corr_out = macro.get("correction", {})
    lines.append(f"  纠错: {corr_out.get('level', 'NONE')}档 - {corr_out.get('reason', '无')}")

    # === 美股模型 ===
    if equity:
        eq = equity.get("equity", {}) if "equity" in equity else equity
        lines.append("")
        lines.append("【三、美股中长期模型 v1.0】")
        regime = eq.get("regime", {})
        lines.append(f"  体制: {regime.get('code', 'N/A')} - {regime.get('name', '')}")
        lines.append(f"  仓位上限: {regime.get('position_cap', 'N/A')}%")
        lines.append(f"  加权总分: {eq.get('weighted_score', 'N/A')}")

        alloc = eq.get("allocation", {})
        lines.append(f"  配置: 股票={alloc.get('equity_pct', 'N/A')}% | "
                      f"债券={alloc.get('bond_pct', 'N/A')}% | 现金={alloc.get('cash_pct', 'N/A')}%")

        sb = eq.get("sector_bias", {})
        lines.append(f"  超配: {sb.get('overweight', [])}")
        lines.append(f"  低配: {sb.get('underweight', [])}")

        rm = eq.get("risk_management", {})
        lines.append(f"  风险: SPX回撤={rm.get('drawdown_pct', 'N/A')}% → {rm.get('level', 'N/A')}")

    # === 告警 ===
    alerts = combined.get("alerts", [])
    if alerts:
        lines.append("")
        lines.append("【告警信息】")
        for a in alerts:
            lines.append(f"  [{a.get('level', 'INFO')}] {a.get('message', '')}")

    # === 原始报告 ===
    summary = combined.get("report_summary", "")
    if summary:
        lines.append("")
        lines.append("【模型原始报告】")
        lines.append(summary)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch Research OS model output")
    parser.add_argument("--api-url", default="http://202.81.229.139:8000",
                        help="Research OS API base URL")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of formatted text")
    args = parser.parse_args()

    try:
        combined = fetch_latest(args.api_url)
        equity = fetch_equity(args.api_url)

        if args.json:
            output = {"combined": combined, "equity": equity}
            print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        else:
            print(format_readable(combined, equity))

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {args.api_url}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
