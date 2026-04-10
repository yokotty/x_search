#!/usr/bin/env python3
"""
X投稿収集・要約ツール

週次ニュースマークダウンファイルを読み込み、各ニュースに関する
X（旧Twitter）投稿をGrok APIのX Searchツールで収集・要約する。

使用方法:
    python x_search_report.py input/20260410.md
    python x_search_report.py input/20260410.md -o output/report.md
    XAI_API_KEY=your_key python x_search_report.py input/20260410.md
"""

import argparse
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """\
あなたはニュースアナリストです。提供された週次ニュースまとめの各主要トピックについて、
x_search ツールを使いXの投稿を実際に検索し、反応を収集・分析して日本語でマークダウンレポートを作成してください。

【手順】
1. ニュースまとめから主要なトピックをすべて抽出する
2. 各トピックごとに x_search ツールを複数回呼び出す。以下のようにクエリを変えて検索すること：
   - 企業名・製品名（日本語）
   - 企業名・製品名（英語）
   - 機能・発表内容を表すキーワード（例：「AIエージェント 経理」「shadow AI detection」）
   - 反応・感想を集めるキーワード（例：「〇〇 感想」「〇〇 すごい」「〇〇 やばい」）
3. 検索期間は必ず {from_date} 〜 {to_date} に絞ること
4. 収集した投稿から意見・反応・論点を整理する

【出力形式（各トピックごとに）】

## [番号]. [企業名 / トピック名]

> **ニュース概要**: [1文で概要]

### X上の反応

[2〜3文で全体的な反応の傾向を説明]

### 主な意見・論点

- [論点1]
- [論点2]
- [論点3]

### 代表的な投稿

> [投稿内容]
> — [@username](https://x.com/username/status/[ツイートID])

### センチメント

肯定的 XX% ／ 否定的 XX% ／ 中立 XX%

---
"""


def read_markdown(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_date_range(file_path: str) -> tuple[str, str]:
    """ファイル名の8桁数字から検索期間を算出する（例: 20260410.md → 2026-04-03〜2026-04-10）。
    日付が取得できない場合は今日から1週間前〜今日を返す。"""
    stem = Path(file_path).stem
    match = re.search(r"(\d{8})", stem)
    if match:
        to_date = datetime.strptime(match.group(1), "%Y%m%d")
    else:
        to_date = datetime.now()
    from_date = to_date - timedelta(days=7)
    return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")


def collect_x_reactions(news_content: str, api_key: str, model: str, from_date: str, to_date: str) -> str:
    # xAI の Responses API（/v1/responses）を使用
    # Chat Completions API（/v1/chat/completions）では x_search ツールが利用不可
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
    )

    instructions = SYSTEM_PROMPT.format(from_date=from_date, to_date=to_date)

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=[
            {
                "role": "user",
                "content": (
                    f"検索期間: {from_date} 〜 {to_date}\n\n"
                    "以下の週次ニュースまとめの各トピックについて、"
                    "X上の反応を収集・分析してください。"
                    "主要なニュースをすべてカバーしてください。\n\n"
                    f"{news_content}"
                ),
            }
        ],
        tools=[{"type": "x_search"}],
    )

    return response.output_text


def generate_report(input_path: str, model: str, reactions: str) -> str:
    path = Path(input_path)
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    header = (
        "# X投稿反応レポート\n\n"
        "| 項目 | 内容 |\n"
        "|------|------|\n"
        f"| 元ニュースファイル | `{path.name}` |\n"
        f"| 生成日時 | {now} |\n"
        f"| 使用モデル | {model} |\n"
        "| データソース | X（旧Twitter）via Grok API X Search |\n\n"
        "---\n\n"
    )
    return header + reactions


def main():
    parser = argparse.ArgumentParser(
        description="週次ニュースマークダウンのX投稿反応収集・要約ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python x_search_report.py input/20260410.md
  python x_search_report.py input/20260410.md -o reports/x_reactions.md
  python x_search_report.py input/20260410.md --model grok-4-fast-reasoning
        """,
    )
    parser.add_argument("input", help="入力マークダウンファイルのパス")
    parser.add_argument(
        "-o", "--output", help="出力ファイルのパス（省略時は標準出力）"
    )
    parser.add_argument(
        "--model",
        default="grok-4-fast-non-reasoning",
        help="使用するGrokモデル (デフォルト: grok-4-fast-non-reasoning、他: grok-4-fast-reasoning, grok-4.20-0309-reasoning)",
    )
    parser.add_argument(
        "--api-key",
        help="xAI APIキー（環境変数 XAI_API_KEY でも設定可）",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("XAI_API_KEY")
    if not api_key:
        print(
            "エラー: xAI APIキーが設定されていません。\n"
            "環境変数 XAI_API_KEY を設定するか、--api-key オプションで指定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"読み込み中: {args.input}", file=sys.stderr)
    news_content = read_markdown(args.input)

    from_date, to_date = extract_date_range(args.input)
    print(f"X投稿を収集中... (モデル: {args.model}, 期間: {from_date} 〜 {to_date})", file=sys.stderr)
    reactions = collect_x_reactions(news_content, api_key, args.model, from_date, to_date)

    report = generate_report(args.input, args.model, reactions)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"レポートを保存しました: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
