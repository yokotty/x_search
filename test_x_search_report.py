"""
x_search_report.py のテスト

API呼び出しはモックし、ロジック部分（ファイル読み込み・レポート生成・CLI）をテストする。
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from x_search_report import read_markdown, generate_report, collect_x_reactions, extract_date_range, main


# ------------------------------------------------------------------ #
# read_markdown
# ------------------------------------------------------------------ #

def test_read_markdown_returns_content(tmp_path):
    md = tmp_path / "news.md"
    md.write_text("# テスト\n\nコンテンツ", encoding="utf-8")
    assert read_markdown(str(md)) == "# テスト\n\nコンテンツ"


def test_read_markdown_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_markdown("/nonexistent/path.md")


# ------------------------------------------------------------------ #
# generate_report
# ------------------------------------------------------------------ #

def test_generate_report_contains_filename():
    report = generate_report("input/20260410.md", "grok-4-fast-non-reasoning", "本文")
    assert "`20260410.md`" in report


def test_generate_report_contains_model():
    report = generate_report("input/20260410.md", "grok-4-fast-non-reasoning", "本文")
    assert "grok-4-fast-non-reasoning" in report


def test_generate_report_contains_reactions():
    reactions = "## 1. テスト企業\n\n反応の内容"
    report = generate_report("input/news.md", "grok-4-fast-non-reasoning", reactions)
    assert reactions in report


def test_generate_report_has_header_table():
    report = generate_report("input/news.md", "grok-4-fast-non-reasoning", "")
    assert "# X投稿反応レポート" in report
    assert "元ニュースファイル" in report
    assert "使用モデル" in report
    assert "データソース" in report


# ------------------------------------------------------------------ #
# extract_date_range
# ------------------------------------------------------------------ #

def test_extract_date_range_from_filename():
    from_date, to_date = extract_date_range("input/20260410.md")
    assert to_date == "2026-04-10"
    assert from_date == "2026-04-03"


def test_extract_date_range_7days_before():
    from_date, to_date = extract_date_range("input/20260101.md")
    assert from_date == "2025-12-25"
    assert to_date == "2026-01-01"


def test_extract_date_range_fallback_to_today(tmp_path):
    from datetime import datetime, timedelta
    md = tmp_path / "no_date.md"
    from_date, to_date = extract_date_range(str(md))
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    assert to_date == today
    assert from_date == week_ago


# ------------------------------------------------------------------ #
# collect_x_reactions
# ------------------------------------------------------------------ #

def test_collect_x_reactions_calls_responses_api():
    mock_response = MagicMock()
    mock_response.output_text = "## 1. テスト\n\nX上の反応"

    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch("x_search_report.OpenAI", return_value=mock_client):
        result = collect_x_reactions("ニュース本文", "test_key", "grok-4-fast-non-reasoning", "2026-04-03", "2026-04-10")

    assert result == "## 1. テスト\n\nX上の反応"


def test_collect_x_reactions_passes_x_search_tool():
    mock_response = MagicMock()
    mock_response.output_text = "結果"

    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch("x_search_report.OpenAI", return_value=mock_client):
        collect_x_reactions("本文", "test_key", "grok-4-fast-non-reasoning", "2026-04-03", "2026-04-10")

    _, kwargs = mock_client.responses.create.call_args
    assert {"type": "x_search"} in kwargs["tools"]


def test_collect_x_reactions_uses_xai_base_url():
    mock_response = MagicMock()
    mock_response.output_text = "結果"

    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch("x_search_report.OpenAI", return_value=mock_client) as mock_openai:
        collect_x_reactions("本文", "test_key", "grok-4-fast-non-reasoning", "2026-04-03", "2026-04-10")

    _, kwargs = mock_openai.call_args
    assert kwargs["base_url"] == "https://api.x.ai/v1"


def test_collect_x_reactions_includes_news_content_in_input():
    mock_response = MagicMock()
    mock_response.output_text = "結果"

    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    news = "## マネーフォワード\n\nAI Cowork 発表"
    with patch("x_search_report.OpenAI", return_value=mock_client):
        collect_x_reactions(news, "test_key", "grok-4-fast-non-reasoning", "2026-04-03", "2026-04-10")

    _, kwargs = mock_client.responses.create.call_args
    user_content = kwargs["input"][0]["content"]
    assert news in user_content


def test_collect_x_reactions_includes_date_range_in_input():
    mock_response = MagicMock()
    mock_response.output_text = "結果"

    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch("x_search_report.OpenAI", return_value=mock_client):
        collect_x_reactions("本文", "test_key", "grok-4-fast-non-reasoning", "2026-04-03", "2026-04-10")

    _, kwargs = mock_client.responses.create.call_args
    user_content = kwargs["input"][0]["content"]
    assert "2026-04-03" in user_content
    assert "2026-04-10" in user_content


# ------------------------------------------------------------------ #
# main (CLI)
# ------------------------------------------------------------------ #

def test_main_exits_without_api_key(tmp_path):
    md = tmp_path / "news.md"
    md.write_text("# ニュース", encoding="utf-8")

    with patch.dict("os.environ", {}, clear=True):
        with patch("x_search_report.load_dotenv"):
            with pytest.raises(SystemExit) as exc:
                sys.argv = ["x_search_report.py", str(md)]
                main()
    assert exc.value.code == 1


def test_main_exits_when_file_not_found():
    with patch.dict("os.environ", {"XAI_API_KEY": "test_key"}):
        with pytest.raises(SystemExit) as exc:
            sys.argv = ["x_search_report.py", "/nonexistent/file.md"]
            main()
    assert exc.value.code == 1


def test_main_prints_report_to_stdout(tmp_path, capsys):
    md = tmp_path / "news.md"
    md.write_text("# ニュース\n\nテスト内容", encoding="utf-8")

    mock_response = MagicMock()
    mock_response.output_text = "## 1. テスト\n\nX上の反応"
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch.dict("os.environ", {"XAI_API_KEY": "test_key"}):
        with patch("x_search_report.OpenAI", return_value=mock_client):
            sys.argv = ["x_search_report.py", str(md)]
            main()

    captured = capsys.readouterr()
    assert "X投稿反応レポート" in captured.out
    assert "## 1. テスト" in captured.out


def test_main_saves_report_to_file(tmp_path):
    md = tmp_path / "news.md"
    md.write_text("# ニュース", encoding="utf-8")
    output_file = tmp_path / "out" / "report.md"

    mock_response = MagicMock()
    mock_response.output_text = "## 1. テスト\n\nX上の反応"
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch.dict("os.environ", {"XAI_API_KEY": "test_key"}):
        with patch("x_search_report.OpenAI", return_value=mock_client):
            sys.argv = ["x_search_report.py", str(md), "-o", str(output_file)]
            main()

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "X投稿反応レポート" in content


def test_main_creates_output_dir_if_not_exists(tmp_path):
    md = tmp_path / "news.md"
    md.write_text("# ニュース", encoding="utf-8")
    output_file = tmp_path / "deep" / "nested" / "report.md"

    mock_response = MagicMock()
    mock_response.output_text = "反応"
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response

    with patch.dict("os.environ", {"XAI_API_KEY": "test_key"}):
        with patch("x_search_report.OpenAI", return_value=mock_client):
            sys.argv = ["x_search_report.py", str(md), "-o", str(output_file)]
            main()

    assert output_file.exists()
