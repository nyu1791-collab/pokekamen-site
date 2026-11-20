"""GitHub Actions 等から定期実行し、ポケカメン全4媒体の最新状態を live-status.json へ書き出す。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import server  # noqa: E402


def main() -> None:
    data = server.get_live_status(force=True)
    out_path = ROOT / 'live-status.json'
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(
        f"Updated live-status.json at {data.get('fetched_at')} | "
        f"kick_live={data['kick'].get('is_live')} (ok={data['kick'].get('status_ok')}, viewers={data['kick'].get('viewers')}) "
        f"tc_live={data['twitcasting'].get('is_live')} (ok={data['twitcasting'].get('status_ok')}) "
        f"x_ok={data['x'].get('status_ok')} yt_videos={len(data['youtube'].get('videos', []))}"
    )


if __name__ == '__main__':
    main()
