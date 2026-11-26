"""LemonTea Mobile (Flet) — Sol's RNG Biome Sniper APK."""

import json
import time
import flet as ft

from sniper_engine import BIOME_COLOURS, RARE_BIOMES, BiomeSniperEngine

# Exact Manas Macro / LemonTea Dark Palette
BG = "#101116"
PANEL = "#16181F"
SUNK = "#0C0D11"
EDGE = "#272B36"
TEXT = "#E6E8F0"
DIM = "#767D92"
ACCENT = "#AAAAFF"
GOOD = "#7EE08A"
BAD = "#EF6B6B"
WARN = "#F5C26B"

STORAGE_KEY = "lemontea_settings_v1"
LEVEL_COLORS = {
    "info": TEXT,
    "good": GOOD,
    "warn": WARN,
    "error": BAD,
    "accent": ACCENT,
    "dim": DIM,
}


def main(page: ft.Page):
    page.title = "LemonTea"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    sniper_ref = {"engine": None}

    # Load persisted settings from Android client_storage
    saved = {}
    try:
        raw_saved = page.client_storage.get(STORAGE_KEY)
        if isinstance(raw_saved, str):
            saved = json.loads(raw_saved)
        elif isinstance(raw_saved, dict):
            saved = raw_saved
    except Exception:
        saved = {}

    # Status widgets
    status_text = ft.Text("Sẵn sàng", size=12, weight=ft.FontWeight.W_600, color=ACCENT)
    status_badge = ft.Container(
        content=status_text,
        bgcolor=SUNK,
        border=ft.border.all(1, EDGE),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
    )

    snipe_count_txt = ft.Text("0", size=13, weight=ft.FontWeight.BOLD, color=GOOD)
    current_biome_txt = ft.Text("Chưa có", size=13, weight=ft.FontWeight.BOLD, color=ACCENT)
    pending_txt = ft.Text("Chưa có server chờ", size=12, color=DIM)

    # Inputs
    token_field = ft.TextField(
        label="Discord Token",
        value=saved.get("token", ""),
        password=True,
        can_reveal_password=True,
        bgcolor=SUNK,
        border_color=EDGE,
        focused_border_color=ACCENT,
        text_size=13,
        dense=True,
    )
    channels_field = ft.TextField(
        label="Channel IDs (cách nhau dấu phẩy)",
        value=saved.get("channels", ""),
        hint_text="1234567890, 9876543210",
        bgcolor=SUNK,
        border_color=EDGE,
        focused_border_color=ACCENT,
        text_size=13,
        dense=True,
    )
    webhook_field = ft.TextField(
        label="Discord Webhook (tùy chọn)",
        value=saved.get("webhook", ""),
        bgcolor=SUNK,
        border_color=EDGE,
        focused_border_color=ACCENT,
        text_size=13,
        dense=True,
    )
    poll_field = ft.TextField(
        label="Quét mỗi (s)",
        value=str(saved.get("poll_interval", 0.8)),
        width=110,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=SUNK,
        border_color=EDGE,
        focused_border_color=ACCENT,
        text_size=13,
        dense=True,
    )
    cooldown_field = ft.TextField(
        label="Cooldown (s)",
        value=str(saved.get("cooldown", 10)),
        width=110,
        keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor=SUNK,
        border_color=EDGE,
        focused_border_color=ACCENT,
        text_size=13,
        dense=True,
    )

    stay_sw = ft.Switch(
        label="Ở lại server đến khi bấm Chuyển Server",
        value=bool(saved.get("stay_in_server", True)),
        active_color=GOOD,
    )
    deeplink_sw = ft.Switch(
        label="Mở thẳng Roblox (roblox://)",
        value=bool(saved.get("use_deeplink", True)),
        active_color=ACCENT,
    )
    ignore_sw = ft.Switch(
        label="Bỏ qua tin xin link (LF / ended / fake)",
        value=bool(saved.get("ignore_requests", True)),
        active_color=ACCENT,
    )

    # Biome checkboxes
    selected_biomes = set(saved.get("biomes", RARE_BIOMES))
    biome_checks = {}
    biome_chips = []
    for biome, hex_col in BIOME_COLOURS.items():
        cb = ft.Checkbox(
            label=biome.title(),
            value=(biome in selected_biomes),
            active_color=hex_col,
            check_color="#0C0D11",
            label_style=ft.TextStyle(size=12, color=TEXT),
        )
        biome_checks[biome] = cb
        biome_chips.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=hex_col),
                        cb,
                    ],
                    spacing=2,
                    tight=True,
                ),
                width=165,
            )
        )

    # Live Log list
    log_list = ft.ListView(expand=True, spacing=3, auto_scroll=True)

    def add_log(msg, level="info"):
        ts = time.strftime("%H:%M:%S")
        color = LEVEL_COLORS.get(level, TEXT)
        log_list.controls.append(
            ft.Text(f"[{ts}] {msg}", size=11, color=color, font_family="monospace", selectable=True)
        )
        if len(log_list.controls) > 150:
            del log_list.controls[:40]
        try:
            page.update()
        except Exception:
            pass

    def show_snack(msg, color=WARN):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color="#0C0D11", weight=ft.FontWeight.W_600), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def collect_cfg():
        try:
            poll = max(0.4, float((poll_field.value or "0.8").strip()))
        except ValueError:
            poll = 0.8
        try:
            cd = max(1.0, float((cooldown_field.value or "10").strip()))
        except ValueError:
            cd = 10.0
        ch_list = [c.strip() for c in (channels_field.value or "").replace("\n", ",").split(",") if c.strip()]
        biomes = [b for b, cb in biome_checks.items() if cb.value]
        return {
            "token": (token_field.value or "").strip(),
            "channels": ", ".join(ch_list),
            "channel_list": ch_list,
            "webhook": (webhook_field.value or "").strip(),
            "poll_interval": poll,
            "cooldown": cd,
            "stay_in_server": bool(stay_sw.value),
            "use_deeplink": bool(deeplink_sw.value),
            "ignore_requests": bool(ignore_sw.value),
            "biomes": biomes,
        }

    def save_cfg(e=None, silent=False):
        cfg = collect_cfg()
        to_save = {k: v for k, v in cfg.items() if k != "channel_list"}
        try:
            page.client_storage.set(STORAGE_KEY, json.dumps(to_save))
            if not silent:
                show_snack("Đã lưu cấu hình LemonTea!", GOOD)
                add_log("Đã lưu cấu hình.", "good")
        except Exception as ex:
            if not silent:
                add_log(f"Lỗi lưu cấu hình: {ex}", "warn")

    def on_launch_url(url):
        try:
            page.launch_url(url)
        except Exception as ex:
            add_log(f"Không mở được Roblox ({ex})", "error")

    def on_snipe(biome, _raw, _cid, count):
        snipe_count_txt.value = str(count)
        current_biome_txt.value = biome.title()
        try:
            page.update()
        except Exception:
            pass

    def on_pending(pending):
        if pending:
            pending_txt.value = f"{pending['biome'].title()} ({pending['found_at']}) — Bấm Chuyển Server!"
            pending_txt.color = GOOD
        else:
            pending_txt.value = "Chưa có server chờ"
            pending_txt.color = DIM
        try:
            page.update()
        except Exception:
            pass

    def on_status(status):
        status_text.value = status
        stopped = status in ("Đã dừng", "Sẵn sàng")
        locked = "Đã khóa" in status
        status_text.color = WARN if locked else (ACCENT if stopped else GOOD)
        start_btn.disabled = not stopped
        stop_btn.disabled = stopped
        switch_btn.disabled = stopped
        try:
            page.update()
        except Exception:
            pass

    def start_click(e):
        eng = sniper_ref["engine"]
        if eng and eng.running:
            return
        cfg = collect_cfg()
        if not cfg["token"]:
            show_snack("Vui lòng nhập Discord Token!", BAD)
            return
        if not cfg["channel_list"]:
            show_snack("Vui lòng nhập ít nhất 1 Channel ID!", BAD)
            return
        if not cfg["biomes"]:
            show_snack("Vui lòng chọn ít nhất 1 Biome!", BAD)
            return

        save_cfg(silent=True)
        eng = BiomeSniperEngine(
            token=cfg["token"],
            channel_ids=cfg["channel_list"],
            target_biomes=cfg["biomes"],
            cooldown=cfg["cooldown"],
            poll_interval=cfg["poll_interval"],
            use_deeplink=cfg["use_deeplink"],
            ignore_requests=cfg["ignore_requests"],
            stay_in_server=cfg["stay_in_server"],
            webhook_url=cfg["webhook"],
            on_log=add_log,
            on_launch=on_launch_url,
            on_snipe=on_snipe,
            on_status=on_status,
            on_pending=on_pending,
        )
        sniper_ref["engine"] = eng
        eng.start()

    def switch_click(e):
        eng = sniper_ref["engine"]
        if eng:
            eng.switch_server()

    def stop_click(e):
        eng = sniper_ref["engine"]
        if eng:
            eng.stop()

    def pick_biomes(mode):
        for b, cb in biome_checks.items():
            if mode == "rare":
                cb.value = b in RARE_BIOMES
            elif mode == "all":
                cb.value = True
            else:
                cb.value = False
        page.update()

    # Action buttons
    start_btn = ft.ElevatedButton(
        "Bắt đầu",
        icon="play_arrow",
        on_click=start_click,
        bgcolor=GOOD,
        color="#0C0D11",
        expand=True,
    )
    switch_btn = ft.ElevatedButton(
        "Chuyển Server",
        icon="skip_next",
        on_click=switch_click,
        bgcolor=ACCENT,
        color="#0C0D11",
        disabled=True,
        expand=True,
    )
    stop_btn = ft.OutlinedButton(
        "Dừng",
        icon="stop",
        on_click=stop_click,
        disabled=True,
        style=ft.ButtonStyle(color=BAD, side=ft.BorderSide(1, EDGE)),
    )

    def card(title, content_controls, trailing=None):
        hdr_row = [ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=ACCENT)]
        if trailing:
            hdr_row.append(trailing)
        return ft.Container(
            bgcolor=PANEL,
            border=ft.border.all(1, EDGE),
            border_radius=12,
            padding=12,
            content=ft.Column(
                [
                    ft.Row(hdr_row, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    *content_controls,
                ],
                spacing=8,
            ),
        )

    header = ft.Container(
        bgcolor=PANEL,
        border=ft.border.only(bottom=ft.BorderSide(1, EDGE)),
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Image(src="avatar.png", width=38, height=38, fit=ft.ImageFit.COVER),
                            border_radius=10,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            border=ft.border.all(1, EDGE),
                        ),
                        ft.Column(
                            [
                                ft.Text("LemonTea", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Text("Sol's RNG Biome Sniper • v1.1", size=11, color=DIM),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=10,
                ),
                status_badge,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    body = ft.Container(
        padding=12,
        content=ft.Column(
            [
                # Controls + Queue card
                card(
                    "Điều khiển nhanh",
                    [
                        ft.Row([start_btn, switch_btn], spacing=8),
                        ft.Row(
                            [
                                stop_btn,
                                ft.OutlinedButton(
                                    "Lưu",
                                    icon="save",
                                    on_click=save_cfg,
                                    style=ft.ButtonStyle(color=TEXT, side=ft.BorderSide(1, EDGE)),
                                ),
                                ft.OutlinedButton(
                                    "Xóa Log",
                                    icon="delete_outline",
                                    on_click=lambda _: (log_list.controls.clear(), page.update()),
                                    style=ft.ButtonStyle(color=DIM, side=ft.BorderSide(1, EDGE)),
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Container(
                            bgcolor=SUNK,
                            border_radius=8,
                            padding=10,
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text("Hàng chờ:", size=12, color=DIM),
                                            pending_txt,
                                        ],
                                        spacing=6,
                                        wrap=True,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text("Đã snipe:", size=12, color=DIM),
                                            snipe_count_txt,
                                            ft.Text(" | Hiện tại:", size=12, color=DIM),
                                            current_biome_txt,
                                        ],
                                        spacing=4,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ),
                    ],
                ),
                # Discord config card
                card(
                    "1. Cấu hình Discord",
                    [
                        token_field,
                        channels_field,
                        webhook_field,
                        ft.Row([poll_field, cooldown_field], spacing=10),
                        stay_sw,
                        deeplink_sw,
                        ignore_sw,
                    ],
                ),
                # Biome picker card
                card(
                    "2. Chọn Biome mục tiêu",
                    [
                        ft.Row(biome_chips, wrap=True, spacing=2, run_spacing=0),
                    ],
                    trailing=ft.Row(
                        [
                            ft.TextButton("Hiếm", on_click=lambda _: pick_biomes("rare")),
                            ft.TextButton("Tất cả", on_click=lambda _: pick_biomes("all")),
                            ft.TextButton("Bỏ", on_click=lambda _: pick_biomes("none")),
                        ],
                        spacing=0,
                    ),
                ),
                # Live log card
                card(
                    "3. Nhật ký hoạt động (Live Log)",
                    [
                        ft.Container(
                            content=log_list,
                            bgcolor=SUNK,
                            border=ft.border.all(1, EDGE),
                            border_radius=8,
                            padding=8,
                            height=210,
                        )
                    ],
                ),
            ],
            spacing=10,
        ),
    )

    page.add(ft.SafeArea(ft.Column([header, body], spacing=0)))
    add_log("Chào mừng đến với LemonTea Mobile!", "accent")
    add_log("Nhập Token, Channel IDs, chọn Biome rồi bấm Bắt đầu.", "dim")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
