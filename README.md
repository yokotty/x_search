# x_search_report

週次ニュースのマークダウンファイルを入力として、[Grok API](https://docs.x.ai) の X Search ツールで各トピックへの X（旧Twitter）投稿を収集・要約し、マークダウン形式のレポートを生成するツール。

## 出力イメージ

```markdown
# X投稿反応レポート

| 元ニュースファイル | `20260410.md` |
| 使用モデル        | grok-4-fast-non-reasoning |
...

## 1. マネーフォワード AI Cowork

> **ニュース概要**: バックオフィス業務を自律実行するAIエージェントを発表

### X上の反応
業務効率化への期待が高まっており...

### 代表的な投稿
> マネーフォワード AI Coworkすごい...
> — @example_user

### センチメント
肯定的 80% ／ 否定的 10% ／ 中立 10%
```

## セットアップ

```bash
pip install -r requirements.txt

cp .env.example .env
# .env を開いて XAI_API_KEY を設定
```

## 使い方

```bash
# 標準出力
python x_search_report.py input/20260410.md

# ファイルに保存
python x_search_report.py input/20260410.md -o output/report.md

# モデル指定
python x_search_report.py input/20260410.md --model grok-4-fast-reasoning
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `input` | 入力マークダウンファイルのパス（必須） | — |
| `-o`, `--output` | 出力ファイルのパス | 標準出力 |
| `--model` | 使用する Grok モデル | `grok-4-fast-non-reasoning` |
| `--api-key` | xAI API キー | 環境変数 `XAI_API_KEY` |

### 利用可能なモデル

x_search ツールは Grok-4 系のみ対応。

| モデル | 特徴 |
|--------|------|
| `grok-4-fast-non-reasoning` | 高速・低コスト（デフォルト） |
| `grok-4-fast-reasoning` | 推論あり・より高精度 |
| `grok-4.20-0309-reasoning` | 最新版・高精度 |

## 入力ファイルの形式

`input/` ディレクトリにマークダウンファイルを配置する。構造は問わず、Grok が自動でトピックを抽出して各トピックを X 検索する。

```
input/
  20260410.md   # 週次ニュースまとめ
  20260417.md
```

> `input/` と `output/` は `.gitignore` に含まれているため git 管理外。

## API の仕組み

xAI の [Responses API](https://docs.x.ai/docs/guides/tools/overview)（`/v1/responses`）に `x_search` ツールを指定して呼び出す。モデルが各トピックのクエリを自律的に組み立てて X を検索し、結果を統合してレポートを生成する。

> Chat Completions API（`/v1/chat/completions`）では `x_search` ツールは利用不可。

## テスト

```bash
python -m pytest test_x_search_report.py -v
```
