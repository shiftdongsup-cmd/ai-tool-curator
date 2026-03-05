import argparse
import html
import importlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

feedparser = None
requests = None


DEFAULT_SOURCES = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
    {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/"},
]


@dataclass
class Source:
    name: str
    url: str


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: datetime
    summary: str


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def ensure_dependencies() -> None:
    global feedparser, requests

    missing = []
    try:
        feedparser = importlib.import_module("feedparser")
    except ModuleNotFoundError:
        missing.append("feedparser")

    try:
        requests = importlib.import_module("requests")
    except ModuleNotFoundError:
        missing.append("requests")

    if not missing:
        return

    logging.info("Installing missing dependencies: %s", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    feedparser = importlib.import_module("feedparser")
    requests = importlib.import_module("requests")


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_sources(config_path: Path) -> List[Source]:
    if not config_path.exists():
        logging.warning("sources.json not found. Falling back to default sources.")
        return [Source(**item) for item in DEFAULT_SOURCES]

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        sources = payload.get("sources", [])
        loaded = [Source(name=item["name"], url=item["url"]) for item in sources]
        if not loaded:
            raise ValueError("No sources in config")
        return loaded
    except Exception as exc:
        logging.error("Failed to parse sources.json: %s", exc)
        return [Source(**item) for item in DEFAULT_SOURCES]


def parse_datetime(entry: dict) -> datetime:
    if "published_parsed" in entry and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if "updated_parsed" in entry and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def normalize_summary(raw_summary: str) -> str:
    text = raw_summary.replace("\n", " ").replace("\r", " ").strip()
    return (text[:177] + "...") if len(text) > 180 else text


def clean_text(raw_text: str) -> str:
    text = html.unescape(raw_text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_korean_text(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text or ""))


def to_korean_one_line_summary(article: Article) -> str:
    summary = clean_text(article.summary)
    title = clean_text(article.title)

    if is_korean_text(summary):
        return summary[:90] + ("..." if len(summary) > 90 else "")

    if summary:
        # Keep concise Korean-style wording for English sources.
        return f"{title[:55]} 관련 업데이트입니다. 핵심 내용은 원문 링크에서 확인하세요."

    return "핵심 업데이트가 게시되었습니다. 자세한 내용은 원문 링크를 확인하세요."


def fetch_source_articles(source: Source, timeout_sec: int) -> List[Article]:
    logging.info("Fetching: %s", source.name)
    try:
        feed = feedparser.parse(source.url)
    except Exception as exc:
        logging.warning("Feed parse failed for %s: %s", source.name, exc)
        return []

    articles: List[Article] = []
    for entry in feed.entries:
        link = entry.get("link", "").strip()
        if not link:
            continue

        title = entry.get("title", "Untitled").strip()
        published = parse_datetime(entry)
        summary = normalize_summary(entry.get("summary", "") or entry.get("description", ""))

        if not summary:
            summary = "요약 정보가 제공되지 않았습니다."

        articles.append(
            Article(
                title=title,
                link=link,
                source=source.name,
                published=published,
                summary=summary,
            )
        )

    # Connectivity check (helps surface DNS/SSL/network issues clearly)
    try:
        requests.get(source.url, timeout=timeout_sec)
    except Exception as exc:
        logging.warning("Network check failed for %s: %s", source.name, exc)

    return articles


def deduplicate_articles(articles: List[Article]) -> List[Article]:
    seen = set()
    unique: List[Article] = []
    for article in articles:
        key = article.link.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        unique.append(article)
    return unique


def filter_recent_articles(articles: List[Article], lookback_hours: int) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return [article for article in articles if article.published >= cutoff]


def rank_articles(articles: List[Article], max_items: int) -> List[Article]:
    sorted_items = sorted(articles, key=lambda a: a.published, reverse=True)
    return sorted_items[:max_items]


def host_from_url(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def build_slack_message(articles: List[Article], lookback_hours: int) -> dict:
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"*AI 뉴스 데일리 피드* ({now_local})\n최근 {lookback_hours}시간 기준"
    if not articles:
        return {"text": "AI 뉴스 데일리 피드: 새 소식이 없습니다.", "mrkdwn": True}

    lines = [header, ""]
    for idx, article in enumerate(articles, start=1):
        when = article.published.astimezone().strftime("%m-%d %H:%M")
        ko_summary = to_korean_one_line_summary(article)
        lines.append(
            f"{idx}. <{article.link}|{article.title}> "
            f"({article.source} / {host_from_url(article.link)} / {when})"
        )
        lines.append(f"   - 요약: {ko_summary}")
    return {"text": "\n".join(lines), "mrkdwn": True}


def post_to_slack(webhook_url: str, payload: dict, timeout_sec: int, channel: str = "") -> None:
    if channel:
        payload = {**payload, "channel": channel}
    resp = requests.post(webhook_url, json=payload, timeout=timeout_sec)
    if resp.status_code >= 300:
        raise RuntimeError(f"Slack webhook failed: {resp.status_code} {resp.text}")


def run_pipeline(
    config_path: Path,
    webhook_url: Optional[str],
    slack_channel: str,
    lookback_hours: int,
    max_items: int,
    timeout_sec: int,
    dry_run: bool = False,
) -> None:
    sources = load_sources(config_path)
    all_articles: List[Article] = []
    for source in sources:
        all_articles.extend(fetch_source_articles(source, timeout_sec=timeout_sec))

    unique_articles = deduplicate_articles(all_articles)
    recent_articles = filter_recent_articles(unique_articles, lookback_hours=lookback_hours)
    ranked_articles = rank_articles(recent_articles, max_items=max_items)

    payload = build_slack_message(ranked_articles, lookback_hours=lookback_hours)
    if dry_run or not webhook_url:
        logging.warning("Dry-run mode: Slack webhook send is skipped.")
        print("\n" + "=" * 80)
        print(payload["text"])
        print("=" * 80 + "\n")
    else:
        post_to_slack(
            webhook_url=webhook_url,
            payload=payload,
            timeout_sec=timeout_sec,
            channel=slack_channel,
        )

    logging.info(
        "Done. posted=%s fetched=%s unique=%s recent=%s",
        len(ranked_articles),
        len(all_articles),
        len(unique_articles),
        len(recent_articles),
    )


def seconds_until(target_hhmm: str, tz_name: str) -> int:
    hour, minute = [int(v) for v in target_hhmm.split(":")]
    now = datetime.now(ZoneInfo(tz_name))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max(1, int((target - now).total_seconds()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI news crawler + Slack daily feed")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect and print feed to console without sending to Slack",
    )
    parser.add_argument(
        "--config",
        default="sources.json",
        help="Path to source config JSON (default: sources.json)",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file (default: .env)",
    )
    parser.add_argument(
        "--require-webhook",
        action="store_true",
        help="Fail if SLACK_WEBHOOK_URL is missing (useful for CI/GitHub Actions)",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    ensure_dependencies()
    args = parse_args()

    load_env_file(Path(args.env_file))

    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    slack_channel = os.getenv("SLACK_CHANNEL", "#ai-tool-news").strip()
    schedule_time = os.getenv("SCHEDULE_TIME", "17:00").strip()
    schedule_timezone = os.getenv("SCHEDULE_TIMEZONE", "Asia/Seoul").strip()
    lookback_hours = int(os.getenv("LOOKBACK_HOURS", "24"))
    max_items = int(os.getenv("MAX_ITEMS", "12"))
    timeout_sec = int(os.getenv("REQUEST_TIMEOUT_SEC", "15"))

    if not webhook_url and args.require_webhook:
        raise RuntimeError("Missing required env var: SLACK_WEBHOOK_URL")

    if not webhook_url and not args.dry_run:
        logging.warning("SLACK_WEBHOOK_URL is missing. Automatically switching to dry-run mode.")
        args.dry_run = True

    config_path = Path(args.config)

    if args.once:
        run_pipeline(
            config_path=config_path,
            webhook_url=webhook_url,
            slack_channel=slack_channel,
            lookback_hours=lookback_hours,
            max_items=max_items,
            timeout_sec=timeout_sec,
            dry_run=args.dry_run,
        )
        return

    logging.info("Scheduler started. Daily run at %s (%s)", schedule_time, schedule_timezone)
    while True:
        sleep_sec = seconds_until(schedule_time, schedule_timezone)
        logging.info("Next run in %s seconds", sleep_sec)
        time.sleep(sleep_sec)
        try:
            run_pipeline(
                config_path=config_path,
                webhook_url=webhook_url,
                slack_channel=slack_channel,
                lookback_hours=lookback_hours,
                max_items=max_items,
                timeout_sec=timeout_sec,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            logging.exception("Run failed: %s", exc)
            # Safety sleep to avoid fast crash loops on repeated failures.
            time.sleep(30)


if __name__ == "__main__":
    main()
