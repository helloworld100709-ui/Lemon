"""Core Biome Sniper engine for LemonTea Android (Flet APK)."""

from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time
import urllib.request
from urllib.parse import parse_qs, urlsplit

import requests

BIOME_COLOURS = {
    "GLITCHED": "#3BE37A",
    "DREAMSPACE": "#E86AF0",
    "CYBERSPACE": "#2FD3FF",
    "THE RADIANT FOREST": "#FFF1A8",
    "SINGULARITY": "#4B1E8C",
    "BLOOD RAIN": "#8B0A1A",
    "GRAVEYARD": "#5E6B5A",
    "PUMPKIN MOON": "#FF7A1A",
    "NULL": "#6B6B6B",
    "CORRUPTION": "#8E44AD",
    "STARFALL": "#6C7BFF",
    "HELL": "#C0392B",
    "HEAVEN": "#FFE89A",
    "LOST FOREST": "#2E8B57",
    "SAND STORM": "#E0A85A",
    "RAINY": "#4A7BD0",
    "SNOWY": "#DCEBFF",
    "WINDY": "#9ED9FF",
}

RARE_BIOMES = [
    "GLITCHED",
    "DREAMSPACE",
    "CYBERSPACE",
    "THE RADIANT FOREST",
    "SINGULARITY",
]

BIOME_ALIASES = {
    "GLITCHED": ("glitched", "glitch"),
    "DREAMSPACE": ("dreamspace", "dream space"),
    "CYBERSPACE": ("cyberspace", "cyber space"),
    "THE RADIANT FOREST": ("the radiant forest", "radiant forest"),
    "SINGULARITY": ("singularity",),
    "BLOOD RAIN": ("blood rain", "bloodrain"),
    "GRAVEYARD": ("graveyard",),
    "PUMPKIN MOON": ("pumpkin moon", "pumpkinmoon"),
    "NULL": ("null",),
    "CORRUPTION": ("corruption", "corrupted"),
    "STARFALL": ("starfall", "star fall"),
    "HELL": ("hell",),
    "HEAVEN": ("heaven",),
    "LOST FOREST": ("lost forest",),
    "SAND STORM": ("sand storm", "sandstorm"),
    "RAINY": ("rainy", "rain"),
    "SNOWY": ("snowy", "snow"),
    "WINDY": ("windy", "wind"),
}

IGNORE_PATTERNS = (
    re.compile(r"\b(lf|looking for|need|anyone have|any)\b", re.I),
    re.compile(r"\b(ended|over|fake|expired)\b", re.I),
)

ROBLOX_URL_RE = re.compile(
    r"https?://(?:www\.|web\.)?roblox\.com/[^\s<>()\"']+",
    re.I,
)


def tidy_link(text):
    text = re.sub(
        r"(privateServerLinkCode=[A-Za-z0-9_-]+)[^A-Za-z0-9_&#\s-]+",
        r"\1",
        (text or "").strip(),
        flags=re.I,
    )
    return re.sub(r"(code=[a-fA-F0-9]{32})[^&#\s]+", r"\1", text, flags=re.I)


def deeplink(text):
    m = ROBLOX_URL_RE.search(tidy_link(text))
    if not m:
        return None
    raw_url = m.group(0).rstrip(".,);!]")
    parts = urlsplit(raw_url)
    host = (parts.hostname or "").lower()
    if host != "roblox.com" and not host.endswith(".roblox.com"):
        return None
    query = {k.lower(): v[0] for k, v in parse_qs(parts.query).items()}
    path = [seg for seg in parts.path.split("/") if seg]
    if path and path[0].lower() == "share":
        code = query.get("code", "")
        if re.fullmatch(r"[a-fA-F0-9]{32}", code) and query.get("type", "").lower() == "server":
            return f"roblox://navigation/share_links?code={code}&type=Server"
        return None
    for i, seg in enumerate(path[:2]):
        if seg.lower() in ("games", "game-places") and i + 1 < len(path) and path[i + 1].isdigit():
            code = query.get("privateserverlinkcode")
            if code is None:
                return None
            if re.fullmatch(r"[A-Za-z0-9_-]+", code):
                return f"roblox://placeId={path[i + 1]}&linkCode={code}"
    return None


def extract_server_links(text):
    results = []
    seen = set()
    for match in ROBLOX_URL_RE.finditer(text or ""):
        raw = tidy_link(match.group(0).rstrip(".,);!]"))
        dl = deeplink(raw)
        if dl and dl not in seen:
            seen.add(dl)
            results.append((raw, dl))
    return results


def post_webhook(webhook_url, biome, raw_link, channel_id, on_log=None):
    url = "".join((webhook_url or "").split())
    if not url:
        return
    hex_str = BIOME_COLOURS.get(biome, "#AAAAFF").lstrip("#")
    colour = int(hex_str, 16)
    payload = {
        "username": "LemonTea Mobile",
        "embeds": [
            {
                "title": f"🎯 Đã Snipe Biome: {biome}",
                "description": f"**Server Link:** {raw_link}\n**Kênh nguồn:** `{channel_id}`",
                "color": colour,
                "footer": {"text": "LemonTea APK • Sol's RNG"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }

    def _send():
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "LemonTea-APK/1.1"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception as e:
            if on_log:
                on_log(f"Gửi webhook thất bại: {e}", "warn")

    threading.Thread(target=_send, daemon=True).start()


class BiomeSniperEngine:
    """Concurrent Discord poller with Stay-in-Server lock & manual switch for Android."""

    def __init__(
        self,
        token,
        channel_ids,
        target_biomes,
        cooldown=10.0,
        poll_interval=0.8,
        use_deeplink=True,
        ignore_requests=True,
        stay_in_server=True,
        webhook_url="",
        on_log=None,
        on_launch=None,
        on_snipe=None,
        on_status=None,
        on_pending=None,
    ):
        self.token = (token or "").strip()
        self.channel_ids = [c.strip() for c in channel_ids if c.strip()]
        self.target_biomes = [b.upper() for b in target_biomes]
        self.cooldown = max(1.0, float(cooldown))
        self.poll_interval = max(0.4, float(poll_interval))
        self.use_deeplink = bool(use_deeplink)
        self.ignore_requests = bool(ignore_requests)
        self.stay_in_server = bool(stay_in_server)
        self.webhook_url = (webhook_url or "").strip()

        self.on_log = on_log or (lambda msg, level="info": None)
        self.on_launch = on_launch or (lambda target_url: None)
        self.on_snipe = on_snipe
        self.on_status = on_status
        self.on_pending = on_pending

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread = None

        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
        self._session.mount("https://", adapter)
        self._session.headers.update({
            "Authorization": self.token,
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
        })

        self.last_message_ids = {}
        self.seen_links = {}
        self.last_join_time = 0.0
        self.snipe_count = 0
        self.in_server = False
        self.pending_server = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def _set_status(self, text):
        if self.on_status:
            self.on_status(text)

    def _notify_pending(self):
        if self.on_pending:
            self.on_pending(self.pending_server)

    @staticmethod
    def extract_text(msg):
        parts = [msg.get("content") or ""]
        for embed in msg.get("embeds") or []:
            parts.append(embed.get("title") or "")
            parts.append(embed.get("description") or "")
            footer = embed.get("footer") or {}
            parts.append(footer.get("text") or "")
            for field in embed.get("fields") or []:
                parts.append(field.get("name") or "")
                parts.append(field.get("value") or "")
        return " ".join(p for p in parts if p)

    def match_biome(self, text):
        lower = text.lower()
        if self.ignore_requests:
            for pat in IGNORE_PATTERNS:
                if pat.search(lower):
                    return None
        for biome in self.target_biomes:
            for alias in BIOME_ALIASES.get(biome, (biome.lower(),)):
                if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lower):
                    return biome
        return None

    def _execute_join(self, biome, raw_url, dl_url, channel_id, manual=False):
        now = time.monotonic()
        self.seen_links[dl_url] = now
        self.last_join_time = now
        self.snipe_count += 1
        if self.stay_in_server:
            self.in_server = True
            self._set_status("Đang ở server (Đã khóa)")
        else:
            self.in_server = False

        tag = "⏭ CHUYỂN SERVER" if manual else "🎯 PHÁT HIỆN"
        self.on_log(f"{tag}: {biome} (kênh {channel_id})! Đang mở Roblox...", "good")

        target = dl_url if self.use_deeplink else raw_url
        self.on_launch(target)
        if self.webhook_url:
            post_webhook(self.webhook_url, biome, raw_url, channel_id, on_log=self.on_log)
        if self.on_snipe:
            self.on_snipe(biome, raw_url, channel_id, self.snipe_count)

    def switch_server(self):
        if not self.running:
            self.on_log("Sniper chưa chạy. Hãy bấm Bắt đầu trước.", "warn")
            return
        with self._lock:
            pending = self.pending_server
            self.pending_server = None
            self.last_join_time = 0.0
            if pending:
                self._notify_pending()
                threading.Thread(
                    target=self._execute_join,
                    args=(pending["biome"], pending["raw_url"], pending["dl_url"], pending["channel_id"], True),
                    daemon=True,
                ).start()
            else:
                self.in_server = False
                self._set_status("Đang săn server mới")
                self._notify_pending()
                self.on_log("Đã mở khóa server! Sẽ tự động vào ngay khi có Biome mới.", "accent")

    def _check_channel(self, cid):
        url = f"https://discord.com/api/v9/channels/{cid}/messages?limit=3"
        try:
            resp = self._session.get(url, timeout=4)
        except requests.RequestException as e:
            self.on_log(f"Lỗi mạng kênh {cid}: {e}", "warn")
            return

        if resp.status_code == 401:
            self.on_log("Token Discord không hợp lệ hoặc hết hạn (401). Đang dừng...", "error")
            self._stop_event.set()
            return
        if resp.status_code == 403:
            self.on_log(f"Không có quyền đọc kênh {cid} (403).", "warn")
            return
        if resp.status_code == 429:
            retry = 1.5
            try:
                retry = float(resp.json().get("retry_after", 1.5))
            except Exception:
                pass
            self.on_log(f"Rate Limit (429), nghỉ {retry:.1f}s...", "warn")
            self._stop_event.wait(retry + 0.2)
            return
        if resp.status_code != 200:
            return

        try:
            messages = resp.json()
        except ValueError:
            return
        if not messages:
            return

        newest_id = messages[0]["id"]
        if cid not in self.last_message_ids:
            self.last_message_ids[cid] = newest_id
            self.on_log(f"Đã kết nối kênh {cid}.", "good")
            return

        last_seen = int(self.last_message_ids[cid])
        for msg in reversed(messages):
            if int(msg["id"]) <= last_seen:
                continue
            full_text = self.extract_text(msg)
            links = extract_server_links(full_text)
            if not links:
                continue
            matched = self.match_biome(full_text)
            if not matched:
                continue

            raw_url, dl_url = links[0]
            now = time.monotonic()

            with self._lock:
                if dl_url in self.seen_links and (now - self.seen_links[dl_url] < 300):
                    continue

                if self.stay_in_server and self.in_server:
                    self.pending_server = {
                        "biome": matched,
                        "raw_url": raw_url,
                        "dl_url": dl_url,
                        "channel_id": cid,
                        "found_at": time.strftime("%H:%M:%S"),
                    }
                    self._notify_pending()
                    self.on_log(
                        f"📌 Có {matched} mới trong hàng chờ! Bấm 'Chuyển Server' để nhảy ngay.",
                        "accent",
                    )
                    break

                if now - self.last_join_time < self.cooldown:
                    continue

                self._execute_join(matched, raw_url, dl_url, cid, manual=False)
                break

        self.last_message_ids[cid] = newest_id

    def _run(self):
        self._set_status("Đang săn server mới")
        self.on_log(
            f"Quét song song {len(self.channel_ids)} kênh | Mục tiêu: {', '.join(self.target_biomes)}",
            "accent",
        )
        max_workers = min(8, max(1, len(self.channel_ids)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while not self._stop_event.is_set():
                futures = [pool.submit(self._check_channel, cid) for cid in self.channel_ids]
                for f in futures:
                    if self._stop_event.is_set():
                        break
                    try:
                        f.result()
                    except Exception:
                        pass
                self._stop_event.wait(self.poll_interval)
        self._set_status("Đã dừng")
        self.on_log("LemonTea đã dừng.", "dim")

    def start(self):
        if self.running:
            return False
        self._stop_event.clear()
        self.in_server = False
        self.pending_server = None
        self._notify_pending()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
