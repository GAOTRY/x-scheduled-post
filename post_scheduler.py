"""posts.csv の予約を見て、時刻が来たものをXに投稿する。

GitHub Actions から15分ごとに呼ばれる想定。投稿済みの記録は state.json に残す。
環境変数 X_API_KEY などが無いとき、または DRY_RUN=1 のときは投稿せず内容を表示するだけ。
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).parent
POSTS = ROOT / "posts.csv"
STATE = ROOT / "state.json"
# 予定時刻からこれ以上遅れたものは投稿しない（Actionsが止まっていた後にまとめて流れるのを防ぐ）
MAX_DELAY = timedelta(hours=3)
REPEAT_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def latest_occurrence(start, repeat, now):
    """now 以前で最も新しい予定時刻。まだ始まっていなければ None。"""
    if now < start:
        return None
    step = REPEAT_STEP.get(repeat)
    if step is None:
        return start
    return start + step * ((now - start) // step)


def due_posts(rows, state, now):
    for row in rows:
        start = datetime.strptime(row["datetime"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=JST)
        slot = latest_occurrence(start, row.get("repeat", "").strip(), now)
        if slot is None or now - slot > MAX_DELAY:
            continue
        if state.get(row["id"]) == slot.isoformat():
            continue
        yield row, slot


def make_session():
    from requests_oauthlib import OAuth1Session

    return OAuth1Session(
        os.environ["X_API_KEY"],
        client_secret=os.environ["X_API_SECRET"],
        resource_owner_key=os.environ["X_ACCESS_TOKEN"],
        resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def upload_image(session, path):
    with open(ROOT / path, "rb") as f:
        res = session.post(
            "https://api.x.com/2/media/upload",
            files={"media": f},
            data={"media_category": "tweet_image"},
        )
    res.raise_for_status()
    return res.json()["data"]["id"]


def post(session, row):
    body = {"text": row["text"]}
    image = row.get("image", "").strip()
    if image:
        try:
            body["media"] = {"media_ids": [upload_image(session, image)]}
        except Exception as e:  # 画像だけ失敗したときは文字だけで投稿する
            print(f"[WARN] {row['id']}: 画像を付けられませんでした: {e}", file=sys.stderr)
    res = session.post("https://api.x.com/2/tweets", json=body)
    res.raise_for_status()
    return res.json()["data"]["id"]


def main():
    now = datetime.now(JST)
    dry_run = os.environ.get("DRY_RUN") == "1" or "X_API_KEY" not in os.environ
    with open(POSTS, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    state = load_state()
    session = None if dry_run else make_session()
    failed = False

    for row, slot in due_posts(rows, state, now):
        if dry_run:
            print(f"[DRY RUN] {row['id']} ({slot:%Y-%m-%d %H:%M}): {row['text']}")
            continue
        try:
            tweet_id = post(session, row)
        except Exception as e:  # 1件失敗しても他の予約は続ける
            print(f"[ERROR] {row['id']}: {e}", file=sys.stderr)
            failed = True
            continue
        state[row["id"]] = slot.isoformat()
        print(f"[POSTED] {row['id']} -> https://x.com/i/status/{tweet_id}")

    if not dry_run:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
