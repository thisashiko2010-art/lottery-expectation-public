#!/usr/bin/env python3
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def inspect_html(content):
    soup = BeautifulSoup(content, "html.parser")
    tables = []

    for i, table in enumerate(soup.find_all("table")):
        rows = table.find_all("tr")
        previews = []

        for tr in rows[:4]:
            cells = tr.find_all(["th", "td"])
            previews.append([
                " ".join(c.get_text(" ", strip=True).split())
                for c in cells
            ])

        tables.append({
            "table_index": i,
            "row_count": len(rows),
            "column_counts": [
                len(r.find_all(["th", "td"]))
                for r in rows[:10]
            ],
            "preview": previews
        })

    text = " ".join(soup.get_text(" ", strip=True).split())

    keywords = {
        k: (k in text)
        for k in [
            "回別", "抽せん日", "本数字",
            "ボーナス数字", "販売実績額",
            "キャリーオーバー", "口数", "当せん金額"
        ]
    }

    return {
        "table_count": len(tables),
        "tables": tables,
        "keyword_presence": keywords,
        "html_bytes": len(content),
        "title": soup.title.get_text(" ", strip=True)
        if soup.title else None
    }


def run(config_path, out_dir):
    config = json.loads(
        Path(config_path).read_text(encoding="utf-8")
    )

    out = Path(out_dir)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": config["policy"]["user_agent"]
    })

    results = {}

    for game, url in config["games"].items():
        item = {
            "requested_url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            response = session.get(
                url,
                timeout=config["policy"]["timeout_seconds"]
            )

            item.update({
                "http_status": response.status_code,
                "final_url": response.url,
                "content_type": response.headers.get("Content-Type"),
                "sha256": hashlib.sha256(
                    response.content
                ).hexdigest()
            })

            if response.ok:
                path = raw_dir / f"{game}.html"
                path.write_bytes(response.content)

                item["snapshot_file"] = str(
                    path.relative_to(out)
                )
                item["inspection"] = inspect_html(
                    response.content
                )
            else:
                item["error"] = "non-success HTTP status"

        except Exception as exc:
            item["error"] = (
                f"{type(exc).__name__}: {exc}"
            )

        results[game] = item
        time.sleep(1.0)

    report = {
        "probe_version": "0.6",
        "results": results,
        "production_ready": False,
        "note": (
            "A successful HTTP fetch does not prove that "
            "all historical draw records were present or parsed."
        )
    }

    (out / "probe_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default="config/official_sources.json"
    )
    ap.add_argument(
        "--out",
        default="data/official_probe"
    )

    args = ap.parse_args()

    print(json.dumps(
        run(args.config, args.out),
        ensure_ascii=False,
        indent=2
    ))
