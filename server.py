"""HIDONNA × POKEKAMEN コラボ導線ポータル用 軽量Webサーバー + 全4媒体（Kick・ツイキャス・X・YouTube）最新情報取得API。

すべて無料・APIキー不要の公開エンドポイントを使用。
起動:
  python server.py [--host 127.0.0.1] [--port 8789]
"""
from __future__ import annotations

import argparse
import errno
import html as html_lib
import json
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/136.0.0.0 Safari/537.36'
)

CACHE_TTL_SEC = 45.0
_CACHE_LOCK = threading.Lock()
_CACHE: dict = {'at': 0.0, 'data': None}

FALLBACK_YOUTUBE = [
    {
        'id': 'LGNH6C2m7r0',
        'title': '【総集編】歌い手界隈で起きたヤバすぎる炎上まとめ...この動画が消される前に絶対に見てください。',
        'published': '2026-11-12',
        'url': 'https://www.youtube.com/watch?v=LGNH6C2m7r0',
        'thumbnail': 'https://i.ytimg.com/vi/LGNH6C2m7r0/hqdefault.jpg',
    },
    {
        'id': 'W-0k1c87jMw',
        'title': '【総集編】嘘を吐き中⚫︎費用を支援希望するクズを晒します...更にホストの家から違法⚫︎物が見つかり警察沙汰になりとんでもない事が起きた。',
        'published': '2026-11-03',
        'url': 'https://www.youtube.com/watch?v=W-0k1c87jMw',
        'thumbnail': 'https://i.ytimg.com/vi/W-0k1c87jMw/hqdefault.jpg',
    },
    {
        'id': 'EhF_J1Wn20M',
        'title': '【注意喚起】これから動物を飼おうとしてる方はこの動画を見てください...そしてこの動画を拡散してください。',
        'published': '2026-10-25',
        'url': 'https://www.youtube.com/watch?v=EhF_J1Wn20M',
        'thumbnail': 'https://i.ytimg.com/vi/EhF_J1Wn20M/hqdefault.jpg',
    },
]

FALLBACK_KICK_VODS = [
    {
        'id': '01a1f1ea-2b50-7aa3-9a5e-64a5844a6173',
        'title': 'ヒドンナさんとデート！俺の暴露が出る！？嘘つくなマティアス',
        'date': '2026-11-19',
        'duration': '4:50:28',
        'category': 'IRL',
        'url': 'https://kick.com/pokekamen/videos/01a1f1ea-2b50-7aa3-9a5e-64a5844a6173',
        'thumbnail': './assets/poke_avatar_kick.webp',
    },
    {
        'id': '01a1ecf5-e3a0-7024-891a-2456cfbf0fc8',
        'title': 'ねむこと一緒に野田草履の家に向かう！今日はkick公式！',
        'date': '2026-11-18',
        'duration': '3:57:39',
        'category': 'Just Chatting',
        'url': 'https://kick.com/pokekamen/videos/01a1ecf5-e3a0-7024-891a-2456cfbf0fc8',
        'thumbnail': './assets/poke_avatar_kick.webp',
    },
    {
        'id': '01a1e7e2-4868-7011-a2ea-de4e4615065f',
        'title': 'ポケカメンの誕生日会のその後…もんじょりがそくと行動！？他にもやばい話が…',
        'date': '2026-11-17',
        'duration': '2:03:10',
        'category': 'Just Chatting',
        'url': 'https://kick.com/pokekamen/videos/01a1e7e2-4868-7011-a2ea-de4e4615065f',
        'thumbnail': './assets/poke_avatar_kick.webp',
    },
]

FALLBACK_TWITCASTING_MOVIES = [
    {
        'id': '843145974',
        'title': '緊急メンシプ',
        'date': '2026-11-19 23:00',
        'duration': '1:12:34',
        'views': 0,
        'url': 'https://twitcasting.tv/gc5r5ogikgv0yvz/movie/843145974',
        'thumbnail': './assets/poke_avatar_tc.jpg',
    },
    {
        'id': '843062991',
        'title': 'ライフイズストレンジ１',
        'date': '2026-11-17 19:29',
        'duration': '2:58:47',
        'views': 0,
        'url': 'https://twitcasting.tv/gc5r5ogikgv0yvz/movie/843062991',
        'thumbnail': './assets/poke_avatar_tc.jpg',
    },
    {
        'id': '842965305',
        'title': '緊急',
        'date': '2026-11-14 23:55',
        'duration': '1:12:54',
        'views': 0,
        'url': 'https://twitcasting.tv/gc5r5ogikgv0yvz/movie/842965305',
        'thumbnail': './assets/poke_avatar_tc.jpg',
    },
]


def _http_get(url: str, timeout: float = 8.0) -> str:
    headers = {
        'User-Agent': UA,
        'Accept': 'application/json, application/xml, text/xml, */*',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', 'replace')
    except Exception:
        try:
            from curl_cffi import requests as cffi_requests
            r = cffi_requests.get(url, headers=headers, impersonate='chrome', timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception:
            raise


def _fmt_duration(seconds: int | float | None) -> str:
    if not seconds or seconds <= 0:
        return ''
    sec = int(round(seconds))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'


def _iso_to_jst_date(iso_str: str | None) -> str:
    if not iso_str:
        return ''
    try:
        s = str(iso_str).replace('Z', '+00:00')
        dt = datetime.fromisoformat(s).astimezone(JST)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return str(iso_str)[:10]


def _fetch_kick() -> dict:
    out = {
        'is_live': False,
        'title': '',
        'viewers': 0,
        'category': '',
        'thumbnail': '',
        'followers': 57499,
        'username': 'pokekamen',
        'avatar': './assets/poke_avatar_kick.webp',
        'bio': '相談事にのりそれを晒してる配信者！なんでも相談乗ります！',
        'url': 'https://kick.com/pokekamen',
        'videos': list(FALLBACK_KICK_VODS),
        'status_ok': False,
    }
    channel_id = 57131560
    for ep in (
        'https://kick.com/api/v2/channels/pokekamen',
        'https://kick.com/api/v1/channels/pokekamen',
    ):
        try:
            d = json.loads(_http_get(ep, timeout=8.0))
            out['status_ok'] = True
            if d.get('id'):
                channel_id = int(d['id'])
            if d.get('followers_count') is not None:
                out['followers'] = int(d['followers_count'])
            u = d.get('user') or {}
            if u.get('username'):
                out['username'] = str(u['username'])
            if u.get('profile_pic'):
                out['avatar'] = str(u['profile_pic'])
            if u.get('bio'):
                lines = [ln.strip() for ln in str(u['bio']).splitlines() if ln.strip()]
                if lines:
                    out['bio'] = '\n'.join(lines)
            ls = d.get('livestream')
            if isinstance(ls, dict) and ls.get('is_live') is not False:
                out['is_live'] = True
                out['title'] = str(ls.get('session_title') or '').strip()
                out['viewers'] = int(ls.get('viewer_count') or 0)
                cats = ls.get('categories') or []
                if cats and isinstance(cats[0], dict):
                    out['category'] = str(cats[0].get('name') or '')
                thumb = ls.get('thumbnail')
                if isinstance(thumb, dict):
                    out['thumbnail'] = str(thumb.get('url') or thumb.get('src') or '')
                elif isinstance(thumb, str):
                    out['thumbnail'] = thumb
            break
        except Exception:
            continue

    # Kick 最新過去配信アーカイブ 3本（正規 VOD UUID が取れる web.kick.com API）
    try:
        vd = json.loads(_http_get(f'https://web.kick.com/api/v1/channels/{channel_id}/videos', timeout=8.0))
        raw_list = vd.get('data') if isinstance(vd, dict) else (vd if isinstance(vd, list) else [])
        vods = []
        for item in raw_list:
            if not isinstance(item, dict) or item.get('is_live'):
                continue
            vid = str(item.get('id') or '').strip()
            if not vid:
                continue
            th = item.get('thumbnail')
            thumb_url = str(th.get('src') or th.get('url') or '') if isinstance(th, dict) else str(th or '')
            cat = (item.get('category') or {}).get('name') if isinstance(item.get('category'), dict) else ''
            vods.append({
                'id': vid,
                'title': str(item.get('title') or 'Kick 過去配信').strip(),
                'date': _iso_to_jst_date(item.get('start_time') or item.get('created_at')),
                'duration': _fmt_duration(item.get('duration')),
                'category': str(cat or ''),
                'url': f'https://kick.com/pokekamen/videos/{vid}',
                'thumbnail': thumb_url or './assets/poke_avatar_kick.webp',
            })
            if len(vods) >= 3:
                break
        if vods:
            out['videos'] = vods
    except Exception:
        pass
    return out


def _fetch_twitcasting() -> dict:
    """ツイキャス（@GC5R5OGIKgV0yvz）のリアルタイム配信判定＋最新録画3本＋プロフィールを無料取得。"""
    out = {
        'is_live': False,
        'title': '',
        'viewers': 0,
        'thumbnail': '',
        'supporters': '269.0k',
        'level': 80,
        'name': 'ポケカメン@配信者',
        'screen_id': '@GC5R5OGIKgV0yvz',
        'avatar': './assets/poke_avatar_tc.jpg',
        'bio': 'YouTube/ツイキャスで動画だして配信してる晒し系歌い手です！！サブ垢→【@8IcoEitHGybnh5V】ちょこらび🍫🐰【@_Chofficial】DMで炎上や害悪のやばい情報募集してます！',
        'url': 'https://twitcasting.tv/gc5r5ogikgv0yvz',
        'movies': list(FALLBACK_TWITCASTING_MOVIES),
        'status_ok': False,
    }
    try:
        ss = json.loads(_http_get('https://twitcasting.tv/streamserver.php?target=GC5R5OGIKgV0yvz&mode=client', timeout=7.0))
        mv = ss.get('movie') if isinstance(ss, dict) else None
        if isinstance(mv, dict):
            out['status_ok'] = True
            if mv.get('live') is True:
                out['is_live'] = True
                if mv.get('id'):
                    out['url'] = f'https://twitcasting.tv/gc5r5ogikgv0yvz/movie/{mv["id"]}'
    except Exception:
        pass

    try:
        page = _http_get('https://twitcasting.tv/gc5r5ogikgv0yvz', timeout=8.0)
        out['status_ok'] = True
        m_name = re.search(r'class="tw-user-nav2-name"[^>]*>(.*?)<', page, re.S)
        if m_name and m_name.group(1).strip():
            out['name'] = html_lib.unescape(m_name.group(1).strip())
        m_av = re.search(r'class="tw-user-nav2-icon"[^>]*>.*?<img[^>]+src="([^"]+)"', page, re.S)
        if m_av and m_av.group(1).strip():
            out['avatar'] = html_lib.unescape(m_av.group(1).strip())
        m_sup = re.search(r'/backers/"[^>]*>.*?class=[\'"]tw-user-nav-list-count[\'"][^>]*>([^<]+)<', page, re.S)
        if m_sup and m_sup.group(1).strip():
            out['supporters'] = m_sup.group(1).strip()
        m_lv = re.search(r'レベル\s*(\d+)', page)
        if m_lv:
            out['level'] = int(m_lv.group(1))
        m_bio = re.search(r'id="authorcomment"[^>]*>(.*?)</div>', page, re.S)
        if m_bio:
            raw_bio = html_lib.unescape(re.sub(r'<[^>]+>', '', m_bio.group(1))).strip()
            if raw_bio:
                out['bio'] = raw_bio
        if out['is_live']:
            m_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', page)
            if m_title and m_title.group(1).strip():
                out['title'] = html_lib.unescape(m_title.group(1).strip())
            m_og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page)
            if m_og and m_og.group(1).strip():
                out['thumbnail'] = html_lib.unescape(m_og.group(1).strip())
    except Exception:
        pass

    try:
        sh = _http_get('https://twitcasting.tv/gc5r5ogikgv0yvz/show/', timeout=8.0)
        cards = re.findall(r'<a class="tw-movie-thumbnail2"[^>]*href="(/gc5r5ogikgv0yvz/movie/(\d+))"[^>]*>(.*?)</a>', sh, re.S | re.I)
        movies = []
        seen = set()
        for href, mid, body in cards:
            if mid in seen:
                continue
            seen.add(mid)
            m_img = re.search(r'class="tw-movie-thumbnail2-image"[^>]*src="([^"]+)"(?:[^>]*title="([^"]*)")?', body)
            m_dur = re.search(r'class="tw-movie-thumbnail2-duration"[^>]*>(.*?)</span>', body, re.S)
            m_view = re.search(r'class="tw-movie-thumbnail2-view"[^>]*>(.*?)</span>', body, re.S)
            m_title = re.search(r'class="tw-movie-thumbnail2-title[^"]*"[^>]*>(.*?)</', body, re.S)

            thumb = ''
            date_str = ''
            if m_img:
                thumb = html_lib.unescape(m_img.group(1)).replace('-s.jpg', '.jpg')
                raw_date = (m_img.group(2) or '').strip()
                if raw_date:
                    date_str = raw_date.replace('/', '-')[:16]
            views = 0
            if m_view:
                digits = re.sub(r'[^\d]', '', m_view.group(1))
                if digits:
                    views = int(digits)
            title = 'ツイキャス配信アーカイブ'
            if m_title:
                t_clean = html_lib.unescape(re.sub(r'<[^>]+>', '', m_title.group(1))).replace('\xa0', ' ').strip()
                if t_clean:
                    title = t_clean

            movies.append({
                'id': mid,
                'title': title,
                'date': date_str,
                'duration': m_dur.group(1).strip() if m_dur else '',
                'views': views,
                'url': f'https://twitcasting.tv{href}',
                'thumbnail': thumb or './assets/poke_avatar_tc.jpg',
            })
            if len(movies) >= 3:
                break
        if movies:
            out['movies'] = movies
    except Exception:
        pass
    return out


def _fetch_x_profile() -> dict:
    out = {
        'handle': '@GC5R5OGIKgV0yvz',
        'name': 'ポケカメン@配信者',
        'followers': 338091,
        'avatar': './assets/poke_avatar_x.jpg',
        'banner': './assets/poke_banner_x.jpg',
        'bio': (
            '動画だして配信してる晒し系！サブ垢→【@8IcoEitHGybnh5V】'
            '相談など暴露はDMまで！インスタでも相談乗ってます→【instagram.com/pokestgram】'
            'ポケカメンインフォ垢→【@Pokekamen_info】\n'
            '配信してる場所：ツイキャス・kick・YouTube'
        ),
        'url': 'https://x.com/GC5R5OGIKgV0yvz',
        'status_ok': False,
    }
    try:
        d = json.loads(_http_get('https://api.fxtwitter.com/GC5R5OGIKgV0yvz', timeout=6.0))
        u = d.get('user') if isinstance(d, dict) else None
        if isinstance(u, dict):
            out['status_ok'] = True
            if u.get('name'):
                out['name'] = str(u['name'])
            if u.get('followers') is not None:
                out['followers'] = int(u['followers'])
            if u.get('description'):
                out['bio'] = str(u['description']).strip()
            if u.get('avatar_url'):
                out['avatar'] = str(u['avatar_url']).replace('_normal', '_400x400')
    except Exception:
        pass
    return out


def _fetch_youtube() -> dict:
    """通常動画のみ（ショート動画除外）の最新3本を YouTube 公式 UULF フィードから取得。"""
    out = {
        'channel_url': 'https://www.youtube.com/@pokekamen15',
        'videos': list(FALLBACK_YOUTUBE),
        'status_ok': False,
    }
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'yt': 'http://www.youtube.com/xml/schemas/2015',
    }
    for feed_url in (
        'https://www.youtube.com/feeds/videos.xml?playlist_id=UULFhVJyKoxVGt4KAqQodRlNBQ',
        'https://www.youtube.com/feeds/videos.xml?channel_id=UChVJyKoxVGt4KAqQodRlNBQ',
    ):
        try:
            xml_text = _http_get(feed_url, timeout=8.0)
            root = ET.fromstring(xml_text)
            vids = []
            for entry in root.findall('atom:entry', ns):
                vid_el = entry.find('yt:videoId', ns)
                title_el = entry.find('atom:title', ns)
                pub_el = entry.find('atom:published', ns)
                link_el = entry.find('atom:link', ns)
                href = link_el.attrib.get('href', '') if link_el is not None else ''
                if '/shorts/' in href:
                    continue
                if vid_el is not None and title_el is not None:
                    vid = (vid_el.text or '').strip()
                    if not vid:
                        continue
                    vids.append({
                        'id': vid,
                        'title': (title_el.text or '').strip(),
                        'published': ((pub_el.text or '')[:10] if pub_el is not None else ''),
                        'url': f'https://www.youtube.com/watch?v={vid}',
                        'thumbnail': f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
                    })
                    if len(vids) >= 3:
                        break
            if vids:
                out['videos'] = vids
                out['status_ok'] = True
                break
        except Exception:
            continue
    return out


def get_live_status(force: bool = False) -> dict:
    now = time.time()
    with _CACHE_LOCK:
        if not force and _CACHE['data'] is not None and (now - _CACHE['at']) < CACHE_TTL_SEC:
            return _CACHE['data']

    results: dict = {}
    threads = [
        threading.Thread(target=lambda: results.__setitem__('kick', _fetch_kick()), daemon=True),
        threading.Thread(target=lambda: results.__setitem__('twitcasting', _fetch_twitcasting()), daemon=True),
        threading.Thread(target=lambda: results.__setitem__('x', _fetch_x_profile()), daemon=True),
        threading.Thread(target=lambda: results.__setitem__('youtube', _fetch_youtube()), daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    payload = {
        'fetched_at': datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST'),
        'kick': results.get('kick') or _fetch_kick(),
        'twitcasting': results.get('twitcasting') or _fetch_twitcasting(),
        'x': results.get('x') or _fetch_x_profile(),
        'youtube': results.get('youtube') or _fetch_youtube(),
    }
    with _CACHE_LOCK:
        _CACHE['at'] = time.time()
        _CACHE['data'] = payload
    return payload


class SafeThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


class PortalHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        path = urlparse(self.path).path
        if path.startswith(('/assets/', '/fonts/')):
            self.send_header('Cache-Control', 'public, max-age=300')
        else:
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/live-status':
            qs = parse_qs(parsed.query)
            force = qs.get('refresh', ['0'])[0] in ('1', 'true', 'yes')
            data = get_live_status(force=force)
            raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            return
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, format, *args):
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8789)
    a = ap.parse_args()
    try:
        srv = SafeThreadingHTTPServer((a.host, a.port), PortalHandler)
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, 10048):
            print(f'Port {a.port} already active (reusing running server).', flush=True)
            return
        raise
    print(f'HIDONNA x POKEKAMEN Portal Server listening on http://{a.host}:{a.port}/', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
