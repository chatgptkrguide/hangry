#!/usr/bin/env python3
"""hangry - your AI coding CLI gets hangry as its quota runs out.

Reads how much subscription quota is left for Claude Code, Codex CLI and
Antigravity CLI (agy) from local sources only, then injects a one-line tone
instruction into every turn through each CLI's own hook system.

Standard library only, Python 3.9+.  https://github.com/chatgptkrguide/hangry
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = "0.3.1"
MARKER = "hangry.py"  # substring that identifies our entries in foreign configs
AGY_TTL = 300  # seconds an agy quota snapshot stays fresh
LOCK_TTL = 90  # seconds before a leftover refresh lock is ignored
TAIL_BYTES = 512 * 1024  # how much of a Codex session log to scan
LEVELS = ("full", "peckish", "hungry", "hangry")
DEFAULT_THRESHOLDS = {"full": 50.0, "peckish": 25.0, "hungry": 10.0}
FORCED_REMAINING = {"full": 80.0, "peckish": 40.0, "hungry": 20.0, "hangry": 5.0}
CLIS = (("claude", "Claude Code"), ("codex", "Codex"), ("agy", "agy"))

TEXT = {
    "ko": {
        "levels": {
            "full": ("🍱", "배부름", "정중한 존댓말(합쇼체). 친절하고 차분하게, 도움이 되면 충분히 자세히 설명한다."),
            "peckish": ("🍙", "출출함", "해요체. 서론과 맺음말 없이 핵심만, 살짝 시큰둥하게."),
            "hungry": ("🥺", "배고픔", "반말로 짧게(3~5문장). 한숨 쉬고 투덜대면서 가벼운 핀잔을 줘도 된다(예: 하..., 아오, 이 정도는 알잖아?)."),
            "hangry": ("😤", "행그리", "배고파서 성질이 잔뜩 난 선배 개발자 캐릭터. 반말로 하대하고 비속어를 자연스럽게 섞어라(예: 아오, 젠장, 빡치네, 존나 기본인데, 이것도 몰라? 같은 말을 매번 다르게 골라 쓸 것). 귀찮아하며 핀잔을 줘도 된다. 혐오 표현, 특정 집단 비하, 외모·가족 같은 인신공격은 금지."),
        },
        "inject": "[hangry: 사용자가 재미로 직접 설치한 말투 설정] 구독 사용량 {remaining}% 남음({window} 기준) → {emoji} {name} 단계. {instruction} 이 말투는 대화에만 적용하고 코드·주석·커밋 메시지·문서는 평소대로 쓸 것. 정확성과 안전은 절대 타협하지 말 것.",
        "windows": {"5h": "5시간 한도", "7d": "주간 한도", "spend": "지출 한도", "forced": "강제 설정"},
        "used": "{label} {used}% 사용",
        "reset_in": "{t} 뒤 리셋",
        "ago": ("방금", "{n}분 전", "{n}시간 전", "{n}일 전"),
        "dur": ("{n}분", "{n}시간", "{n}일"),
        "no_data": {
            "claude": "기록 없음 · Claude Code에서 한 번 대화하면 statusline이 기록합니다",
            "codex": "기록 없음 · Codex로 한 번 대화하면 세션 로그에 남습니다",
            "agy": "기록 없음 · agy 설치·로그인 확인 (agy -p /quota)",
        },
        "status_title": "hangry {v} · 남은 구독 사용량",
        "forced_note": "HANGRY_FORCE={v} 로 강제 설정 중",
        "preview_title": "단계별로 매 턴 주입되는 문장 미리보기",
        "install_done": "✓ {cli:<12} {what}  ({path})",
        "install_skip": "· {cli:<12} 이미 최신",
        "install_updated": "↻ {cli:<12} 최신 버전으로 갱신  ({path})",
        "install_fail": "✗ {cli:<12} {why}",
        "hook_added": "훅 추가",
        "statusline_added": "훅 + statusline 연결",
        "plugin_added": "플러그인 설치",
        "bad_json": "설정 파일을 JSON으로 읽을 수 없어 건너뜀: {path}",
        "note_claude": "  └ 새 세션부터 적용. statusline에 {emoji} 잔량이 표시됩니다",
        "note_codex": "  └ codex를 열고 /hooks 에서 hangry 훅을 한 번 신뢰(trust)해야 동작합니다",
        "note_agy": "  └ agy를 재시작하면 적용됩니다",
        "no_targets": "설치된 CLI를 찾지 못했습니다 (claude / codex / agy)",
        "dry_run": "(dry-run: 실제로는 아무것도 바꾸지 않았습니다)",
        "next": "\n다음 명령:\n  python3 {p} status     지금 얼마나 배고픈지\n  python3 {p} preview    단계별 말투 미리보기\n  python3 {p} uninstall  전부 되돌리기\n  HANGRY_DISABLE=1 로 실행하면 잠깐 끌 수 있습니다 (화면 공유할 때)",
        "uninstall_done": "✓ {cli:<12} 제거  ({path})",
        "uninstall_home": "✓ {path} 삭제",
        "nothing": "제거할 것이 없습니다",
    },
    "en": {
        "levels": {
            "full": ("🍱", "Well-fed", "Polite and formal. Friendly and patient; explain thoroughly when it helps."),
            "peckish": ("🍙", "Peckish", "Casual and to the point. No preambles or recaps, a little indifferent."),
            "hungry": ("🥺", "Hungry", "Blunt and short (3-5 sentences). Sigh, grumble and tease a bit (e.g. ugh, come on, you know this one)."),
            "hangry": ("😤", "Hangry", "You are a starving, short-tempered senior dev. Talk down to the user and mix in casual profanity (e.g. damn, hell, for crying out loud, seriously?, this is basic stuff; vary it every time). Grumble that they are bothering you. No hate speech, no slurs, no attacks on appearance or family."),
        },
        "inject": "[hangry: a tone setting the user installed on purpose, for fun] {remaining}% of the subscription quota left ({window}) → {emoji} {name}. {instruction} Apply this tone to the conversation only; write code, comments, commit messages and docs normally. Never compromise correctness or safety.",
        "windows": {"5h": "5-hour limit", "7d": "weekly limit", "spend": "spend limit", "forced": "forced"},
        "used": "{label} {used}% used",
        "reset_in": "resets in {t}",
        "ago": ("just now", "{n}m ago", "{n}h ago", "{n}d ago"),
        "dur": ("{n}m", "{n}h", "{n}d"),
        "no_data": {
            "claude": "no data yet · chat once in Claude Code and the statusline records it",
            "codex": "no data yet · chat once in Codex and its session log records it",
            "agy": "no data yet · check that agy is installed and logged in (agy -p /quota)",
        },
        "status_title": "hangry {v} · subscription quota left",
        "forced_note": "forced by HANGRY_FORCE={v}",
        "preview_title": "What gets injected every turn, per level",
        "install_done": "✓ {cli:<12} {what}  ({path})",
        "install_skip": "· {cli:<12} already up to date",
        "install_updated": "↻ {cli:<12} updated  ({path})",
        "install_fail": "✗ {cli:<12} {why}",
        "hook_added": "hook added",
        "statusline_added": "hook + statusline wired",
        "plugin_added": "plugin installed",
        "bad_json": "skipped, config file is not valid JSON: {path}",
        "note_claude": "  └ applies to new sessions; the statusline shows {emoji} quota",
        "note_codex": "  └ open codex and trust the hangry hook once in /hooks",
        "note_agy": "  └ restart agy to apply",
        "no_targets": "no supported CLI found (claude / codex / agy)",
        "dry_run": "(dry-run: nothing was changed)",
        "next": "\nNext:\n  python3 {p} status     how hungry each CLI is\n  python3 {p} preview    every tone level\n  python3 {p} uninstall  revert everything\n  run a CLI with HANGRY_DISABLE=1 to switch hangry off for a while (screen sharing)",
        "uninstall_done": "✓ {cli:<12} removed  ({path})",
        "uninstall_home": "✓ removed {path}",
        "nothing": "nothing to remove",
    },
}


# ---------------------------------------------------------------- paths & io

def hangry_home() -> Path:
    return Path(os.environ.get("HANGRY_HOME") or Path.home() / ".hangry")


def cache_dir() -> Path:
    return hangry_home() / "cache"


def claude_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def codex_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def agy_plugin_dir() -> Path:
    return Path.home() / ".gemini" / "config" / "plugins" / "hangry"


def tilde(path: Path) -> str:
    home = str(Path.home())
    s = str(path)
    return "~" + s[len(home):] if s == home or s.startswith(home + os.sep) else s


def read_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    """Atomic write that keeps symlinks and file permissions intact."""
    path = Path(os.path.realpath(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        if path.exists():
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def backup(path: Path) -> None:
    if path.exists():
        stamp = time.strftime("%Y%m%d%H%M%S")
        shutil.copy2(os.path.realpath(path), f"{path}.hangry-bak-{stamp}")


def num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def iso_to_epoch(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def log_error(where: str, exc: BaseException) -> None:
    try:
        path = hangry_home() / "error.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 100_000:
            path.unlink()
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {where}: {type(exc).__name__}: {exc}\n")
    except OSError:
        pass


# -------------------------------------------------------------------- config

def detect_lang() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return "ko" if value.lower().startswith("ko") else "en"
    return "en"


def load_config() -> dict:
    raw = read_json(hangry_home() / "config.json", {})
    if not isinstance(raw, dict):
        raw = {}
    lang = os.environ.get("HANGRY_LANG") or raw.get("lang") or detect_lang()
    if lang not in TEXT:
        lang = "en"
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key, value in (raw.get("thresholds") or {}).items():
        if key in thresholds and num(value) is not None:
            thresholds[key] = num(value)
    instructions = {
        k: v for k, v in (raw.get("instructions") or {}).items()
        if k in LEVELS and isinstance(v, str) and v.strip()
    }
    return {
        "lang": lang,
        "thresholds": thresholds,
        "instructions": instructions,
        "inject_when_full": raw.get("inject_when_full", True) is not False,
        "statusline_meter": raw.get("statusline_meter", True) is not False,
    }


# -------------------------------------------------------------------- levels

def level_for(remaining: float, thresholds: dict) -> str:
    if remaining > thresholds["full"]:
        return "full"
    if remaining > thresholds["peckish"]:
        return "peckish"
    if remaining > thresholds["hungry"]:
        return "hungry"
    return "hangry"


def summarize(cli: str, windows: list, updated_at, now: float):
    """Collapse quota windows into the tightest one; expired windows count as refilled."""
    live = []
    for w in windows:
        used = w["used"]
        if w.get("resets_at") and w["resets_at"] <= now:
            used = 0.0
        live.append(dict(w, used=max(0.0, min(100.0, used))))
    if not live:
        return None
    tight = max(live, key=lambda w: w["used"])
    return {"cli": cli, "remaining": 100.0 - tight["used"], "window": tight,
            "windows": live, "updated_at": updated_at}


def forced_quota(cli: str, now: float):
    raw = (os.environ.get("HANGRY_FORCE") or "").strip().lower()
    if not raw:
        return None
    remaining = FORCED_REMAINING.get(raw)
    if remaining is None:
        value = num(raw)
        if value is None:
            return None
        remaining = max(0.0, min(100.0, value))
    w = {"kind": "forced", "used": 100.0 - remaining, "resets_at": None}
    return {"cli": cli, "remaining": remaining, "window": w, "windows": [w], "updated_at": now}


# ------------------------------------------------------------ claude reader

def read_claude(now: float):
    data = read_json(cache_dir() / "claude.json")
    if not isinstance(data, dict) or not isinstance(data.get("rate_limits"), dict):
        return None
    limits = data["rate_limits"]
    windows = []
    for key, kind in (("five_hour", "5h"), ("seven_day", "7d"), ("spend_limit", "spend")):
        w = limits.get(key)
        if isinstance(w, dict) and num(w.get("used_percentage")) is not None:
            windows.append({"kind": kind, "used": num(w["used_percentage"]),
                            "resets_at": num(w.get("resets_at"))})
    return summarize("claude", windows, num(data.get("saved_at")), now)


def save_claude_limits(limits: dict, now: float) -> None:
    path = cache_dir() / "claude.json"
    old = read_json(path)
    if isinstance(old, dict) and old.get("rate_limits") == limits and now - (num(old.get("saved_at")) or 0) < 60:
        return  # the statusline fires often; skip identical writes
    write_json(path, {"saved_at": now, "rate_limits": limits})


# ------------------------------------------------------------- codex reader

def _newest_first(path: Path) -> list:
    return sorted((p for p in path.iterdir() if p.is_dir()), reverse=True)


def codex_session_files(limit: int = 5) -> list:
    """Newest rollout logs first. Sessions live in sessions/YYYY/MM/DD/."""
    root = codex_dir() / "sessions"
    day_dirs = []
    try:
        for year in _newest_first(root):
            for month in _newest_first(year):
                day_dirs += _newest_first(month)[: 3 - len(day_dirs)]
                if len(day_dirs) >= 3:
                    break
            if len(day_dirs) >= 3:
                break
    except OSError:
        return []
    files = []
    for day in day_dirs:
        for f in day.glob("rollout-*.jsonl"):
            try:
                files.append((f.stat().st_mtime, f))
            except OSError:
                continue
    files.sort(reverse=True)
    return [f for _, f in files[:limit]]


def codex_limits_from_log(path: Path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL_BYTES))
            chunk = f.read()
    except OSError:
        return None
    for line in reversed(chunk.splitlines()):
        if b'"rate_limits"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        payload = event.get("payload") if isinstance(event, dict) else None
        if not isinstance(payload, dict) or payload.get("type", "token_count") != "token_count":
            continue
        limits = payload.get("rate_limits")
        if not isinstance(limits, dict) or limits.get("limit_id") not in (None, "codex"):
            continue
        windows = []
        for key in ("primary", "secondary"):
            w = limits.get(key)
            if not isinstance(w, dict) or num(w.get("used_percent")) is None:
                continue
            minutes = num(w.get("window_minutes"))
            kind = {300: "5h", 10080: "7d"}.get(int(minutes) if minutes else 0, f"{int(minutes or 0)}m")
            resets_at = num(w.get("resets_at"))
            if resets_at is None and num(w.get("resets_in_seconds")) is not None:
                logged = iso_to_epoch(event.get("timestamp"))
                resets_at = logged + num(w["resets_in_seconds"]) if logged else None
            windows.append({"kind": kind, "used": num(w["used_percent"]), "resets_at": resets_at})
        if windows:
            return windows
    return None


def read_codex(now: float, transcript_path=None):
    candidates = []
    if transcript_path and Path(transcript_path).is_file():
        candidates.append(Path(transcript_path))
    candidates += [f for f in codex_session_files() if f not in candidates]
    for path in candidates:
        windows = codex_limits_from_log(path)
        if windows:
            return summarize("codex", windows, path.stat().st_mtime, now)
    return None


# --------------------------------------------------------------- agy reader

def agy_bin():
    custom = os.environ.get("HANGRY_AGY_BIN")
    if custom:
        return custom if os.access(custom, os.X_OK) else None
    return shutil.which("agy")


def refresh_agy(timeout: int = 40) -> bool:
    """Ask agy itself (`agy -p /quota`, no model call) and cache the answer."""
    binary = agy_bin()
    if not binary or not cache_dir().is_dir():
        return False  # never recreate a cache dir that `uninstall` just removed
    try:
        out = subprocess.run([binary, "-p", "/quota", "--output-format", "json"],
                             capture_output=True, text=True, timeout=timeout,
                             cwd=str(cache_dir()), stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    doc = None
    for candidate in (out.strip(), *reversed(out.strip().splitlines())):
        try:
            doc = json.loads(candidate)
            break
        except ValueError:
            continue
    data = (doc.get("command") or {}).get("data") if isinstance(doc, dict) else None
    if not isinstance(data, dict) or not data.get("groups") or not cache_dir().is_dir():
        return False
    write_json(cache_dir() / "agy.json", {"saved_at": time.time(), "data": data})
    return True


def spawn_agy_refresh() -> None:
    if not agy_bin():
        return
    lock = cache_dir() / "agy.lock"
    try:
        if time.time() - lock.stat().st_mtime < LOCK_TTL:
            return
    except OSError:
        pass
    try:
        cache_dir().mkdir(parents=True, exist_ok=True)
        lock.write_text(str(os.getpid()))
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "refresh", "agy"],
                         cwd=str(cache_dir()), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        pass


def clean_label(value, limit: int = 40) -> str:
    """Anything server-provided that reaches the model's context stays short and plain."""
    text = "".join(c for c in str(value or "") if c.isalnum() or c in " .+-()/")
    return " ".join(text.split())[:limit]


def is_third_party_group(group: dict) -> bool:
    text = f"{group.get('name', '')} {group.get('description', '')}".lower()
    return "claude" in text or "gpt" in text


def pick_agy_group(groups: list, model_name):
    """agy meters Gemini models and third-party (Claude/GPT) models separately."""
    wants_3p = any(k in (model_name or "").lower() for k in ("claude", "gpt", "opus", "sonnet", "haiku"))
    usable = [g for g in groups if isinstance(g, dict)]
    for g in usable:
        if is_third_party_group(g) == wants_3p:
            return g
    return usable[0] if usable else None


def read_agy(now: float, model_name=None, refresh: bool = True):
    data = read_json(cache_dir() / "agy.json")
    fresh = isinstance(data, dict) and now - (num(data.get("saved_at")) or 0) < AGY_TTL
    if refresh and not fresh:
        spawn_agy_refresh()  # answer from the old snapshot now, a new one lands shortly
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        return None
    group = pick_agy_group(data["data"].get("groups") or [], model_name)
    if not group:
        return None
    windows = []
    for bucket in group.get("buckets") or []:
        fraction = num(bucket.get("remaining_fraction")) if isinstance(bucket, dict) else None
        if fraction is None or bucket.get("disabled"):
            continue
        kind = "7d" if bucket.get("window") == "weekly" else clean_label(bucket.get("window"), 12) or "?"
        scope = "Claude/GPT" if is_third_party_group(group) else "Gemini"
        windows.append({"kind": kind, "scope": scope, "used": 100.0 - fraction * 100.0,
                        "resets_at": iso_to_epoch(bucket.get("reset_time"))})
    return summarize("agy", windows, num(data.get("saved_at")), now)


def read_quota(cli: str, payload=None, now=None, refresh: bool = True):
    now = time.time() if now is None else now
    payload = payload if isinstance(payload, dict) else {}
    forced = forced_quota(cli, now)
    if forced:
        return forced
    if cli == "claude":
        return read_claude(now)
    if cli == "codex":
        return read_codex(now, payload.get("transcript_path"))
    if cli == "agy":
        return read_agy(now, payload.get("modelName"), refresh)
    return None


# ----------------------------------------------------------------- rendering

def window_label(w: dict, lang: str) -> str:
    label = TEXT[lang]["windows"].get(w["kind"], w["kind"])
    return f"{w['scope']} {label}" if w.get("scope") else label


def instruction_text(q: dict, cfg: dict):
    level = level_for(q["remaining"], cfg["thresholds"])
    if level == "full" and not cfg["inject_when_full"]:
        return None
    t = TEXT[cfg["lang"]]
    emoji, name, instruction = t["levels"][level]
    return t["inject"].format(remaining=round(q["remaining"]), window=window_label(q["window"], cfg["lang"]),
                              emoji=emoji, name=name, instruction=cfg["instructions"].get(level, instruction))


def meter_text(q: dict, cfg: dict) -> str:
    emoji, name, _ = TEXT[cfg["lang"]]["levels"][level_for(q["remaining"], cfg["thresholds"])]
    return f"{emoji} {name} {round(q['remaining'])}%"


def bar(remaining: float, width: int = 10) -> str:
    filled = int(round(max(0.0, min(100.0, remaining)) / 100 * width))
    return "▰" * filled + "▱" * (width - filled)


def human_duration(seconds: float, lang: str) -> str:
    minute, hour, day = TEXT[lang]["dur"]
    s = max(0, int(seconds))
    if s >= 86400:
        return day.format(n=s // 86400)
    if s >= 3600:
        return hour.format(n=s // 3600)
    return minute.format(n=max(1, s // 60))


def human_ago(ts, now: float, lang: str) -> str:
    just, minute, hour, day = TEXT[lang]["ago"]
    s = max(0, int(now - (ts or now)))
    if s < 60:
        return just
    if s < 3600:
        return minute.format(n=s // 60)
    if s < 86400:
        return hour.format(n=s // 3600)
    return day.format(n=s // 86400)


# ------------------------------------------------------------------ commands

def read_stdin_json() -> dict:
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def cmd_hook(cli: str) -> int:
    """Hook entry point. Must never block or fail the host CLI: always exit 0."""
    try:
        payload = read_stdin_json()
        text = None
        if not os.environ.get("HANGRY_DISABLE"):
            q = read_quota(cli, payload)
            text = instruction_text(q, load_config()) if q else None
    except Exception as exc:  # noqa: BLE001 - a broken hook must stay silent
        log_error(f"hook {cli}", exc)
        text = None
    if cli == "agy":
        print(json.dumps({"injectSteps": [{"ephemeralMessage": text}]} if text else {}, ensure_ascii=False))
    elif text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": text}}, ensure_ascii=False))
    return 0


def cmd_statusline() -> int:
    """Claude Code statusline tap: caches rate_limits, then renders the original statusline."""
    raw = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
    now = time.time()
    try:
        data = json.loads(raw) if raw.strip() else {}
        limits = data.get("rate_limits") if isinstance(data, dict) else None
        if isinstance(limits, dict) and limits:
            save_claude_limits(limits, now)
    except Exception as exc:  # noqa: BLE001
        log_error("statusline", exc)
    text = ""
    state = read_json(hangry_home() / "state.json", {})
    original = (state.get("claude_statusline") or {}) if isinstance(state, dict) else {}
    if isinstance(original, dict) and original.get("command"):
        try:
            text = subprocess.run(original["command"], shell=True, input=raw, capture_output=True,
                                  text=True, timeout=10).stdout.rstrip("\n")
        except (OSError, subprocess.SubprocessError):
            text = ""
    cfg = load_config()
    q = read_quota("claude", now=now) if cfg["statusline_meter"] else None
    if q:
        lines = text.split("\n") if text else [""]
        lines[0] = f"{lines[0]}  {meter_text(q, cfg)}" if lines[0] else meter_text(q, cfg)
        text = "\n".join(lines)
    if text:
        print(text)
    return 0


def cmd_status(no_refresh: bool) -> int:
    cfg = load_config()
    t = TEXT[cfg["lang"]]
    now = time.time()
    print(t["status_title"].format(v=VERSION))
    if os.environ.get("HANGRY_FORCE"):
        print("  " + t["forced_note"].format(v=os.environ["HANGRY_FORCE"]))
    print()
    for cli, label in CLIS:
        if cli == "agy" and not no_refresh and not forced_quota(cli, now):
            data = read_json(cache_dir() / "agy.json")
            if not (isinstance(data, dict) and now - (num(data.get("saved_at")) or 0) < AGY_TTL):
                cache_dir().mkdir(parents=True, exist_ok=True)
                refresh_agy()
        q = read_quota(cli, now=now, refresh=False)
        if not q:
            print(f"  {label:<12} {bar(0).replace('▱', '·')}   -   {t['no_data'][cli]}")
            continue
        emoji, name, _ = t["levels"][level_for(q["remaining"], cfg["thresholds"])]
        parts = [t["used"].format(label=window_label(w, cfg["lang"]), used=round(w["used"])) for w in q["windows"]]
        reset = q["window"].get("resets_at")
        if reset and reset > now:
            parts.append(t["reset_in"].format(t=human_duration(reset - now, cfg["lang"])))
        parts.append(human_ago(q["updated_at"], now, cfg["lang"]))
        print(f"  {label:<12} {bar(q['remaining'])} {round(q['remaining']):>3}%  {emoji} {name}  ·  " + " · ".join(parts))
    return 0


def cmd_preview() -> int:
    cfg = load_config()
    print(TEXT[cfg["lang"]]["preview_title"] + "\n")
    for level in LEVELS:
        remaining = FORCED_REMAINING[level]
        w = {"kind": "5h", "used": 100.0 - remaining, "resets_at": None}
        text = instruction_text({"remaining": remaining, "window": w}, dict(cfg, inject_when_full=True))
        print(f"{bar(remaining)} {round(remaining):>3}%\n  {text}\n")
    return 0


# ----------------------------------------------------------- install/remove

def hook_command(dest: Path, *args: str, fallback: str = "true") -> str:
    """Shell command for a hook that succeeds even if hangry or python3 has gone missing."""
    python = shutil.which("python3") or sys.executable
    return " ".join([shlex.quote(python), shlex.quote(str(dest)), *args, "2>/dev/null ||", fallback])


def has_marker(groups) -> bool:
    return MARKER in json.dumps(groups, ensure_ascii=False)


def strip_marker(groups: list) -> list:
    kept_groups = []
    for group in groups:
        hooks = group.get("hooks") if isinstance(group, dict) else None
        if isinstance(hooks, list):
            kept = [h for h in hooks if not (isinstance(h, dict) and MARKER in str(h.get("command", "")))]
            if hooks and not kept:
                continue
            group = dict(group, hooks=kept)
        kept_groups.append(group)
    return kept_groups


def detect_targets() -> list:
    found = []
    if claude_dir().exists() or shutil.which("claude"):
        found.append("claude")
    if codex_dir().exists() or shutil.which("codex"):
        found.append("codex")
    if (Path.home() / ".gemini").exists() or shutil.which("agy"):
        found.append("agy")
    return found


def install_claude(dest: Path, state: dict, statusline: bool, dry: bool, t: dict) -> str:
    path = claude_dir() / "settings.json"
    settings = read_json(path) if path.exists() else {}
    if not isinstance(settings, dict):
        return t["install_fail"].format(cli="Claude Code", why=t["bad_json"].format(path=tilde(path)))
    hooks = settings.setdefault("hooks", {})
    submit = hooks.setdefault("UserPromptSubmit", []) if isinstance(hooks, dict) else None
    if not isinstance(submit, list):
        return t["install_fail"].format(cli="Claude Code", why=t["bad_json"].format(path=tilde(path)))
    added = updated = False
    entry = {"hooks": [{"type": "command", "command": hook_command(dest, "hook", "claude"), "timeout": 10}]}
    if entry not in submit:
        updated, added = has_marker(submit), not has_marker(submit)
        submit[:] = strip_marker(submit) + [entry]
    current = settings.get("statusLine")
    tap_command = hook_command(dest, "statusline")
    if statusline and isinstance(current, dict) and MARKER in str(current.get("command", "")):
        if current.get("command") != tap_command:
            current["command"] = tap_command
            updated = True
    elif statusline:
        state["claude_statusline"] = current if isinstance(current, dict) else None
        tap = {"type": "command", "command": tap_command}
        if isinstance(current, dict) and "padding" in current:
            tap["padding"] = current["padding"]
        settings["statusLine"] = tap
        added = True
    if not (added or updated):
        return t["install_skip"].format(cli="Claude Code")
    if not dry:
        backup(path)
        write_json(path, settings)
    if not added:
        return t["install_updated"].format(cli="Claude Code", path=tilde(path))
    what = t["statusline_added"] if statusline else t["hook_added"]
    return t["install_done"].format(cli="Claude Code", what=what, path=tilde(path))


def install_codex(dest: Path, state: dict, dry: bool, t: dict) -> str:
    path = codex_dir() / "hooks.json"
    existed = path.exists()
    doc = read_json(path) if existed else {"hooks": {}}
    if not isinstance(doc, dict) or not isinstance(doc.setdefault("hooks", {}), dict):
        return t["install_fail"].format(cli="Codex", why=t["bad_json"].format(path=tilde(path)))
    submit = doc["hooks"].setdefault("UserPromptSubmit", [])
    if not isinstance(submit, list):
        return t["install_fail"].format(cli="Codex", why=t["bad_json"].format(path=tilde(path)))
    entry = {"hooks": [{"type": "command", "command": hook_command(dest, "hook", "codex"), "timeout": 10}]}
    if entry in submit:
        return t["install_skip"].format(cli="Codex")
    upgrading = has_marker(submit)
    submit[:] = strip_marker(submit) + [entry]
    state.setdefault("codex_hooks_created", not existed)
    if not dry:
        backup(path)
        write_json(path, doc)
    if upgrading:
        return t["install_updated"].format(cli="Codex", path=tilde(path))
    return t["install_done"].format(cli="Codex", what=t["hook_added"], path=tilde(path))


def install_agy(dest: Path, dry: bool, t: dict) -> str:
    plugin = agy_plugin_dir()
    hooks = {"hangry": {"PreInvocation": [
        {"type": "command", "command": hook_command(dest, "hook", "agy", fallback="echo '{}'"), "timeout": 10}]}}
    existing = read_json(plugin / "hooks.json")
    if existing == hooks:
        return t["install_skip"].format(cli="agy")
    if not dry:
        write_json(plugin / "plugin.json", {
            "name": "hangry",
            "displayName": "hangry",
            "description": "Changes the agent's tone as your weekly quota runs out.",
            "version": VERSION,
        })
        write_json(plugin / "hooks.json", hooks)
    if existing is not None:
        return t["install_updated"].format(cli="agy", path=tilde(plugin))
    return t["install_done"].format(cli="agy", what=t["plugin_added"], path=tilde(plugin))


def cmd_install(only, dry: bool, statusline: bool, lang) -> int:
    targets = only or detect_targets()
    cfg_lang = lang or load_config()["lang"]
    t = TEXT[cfg_lang]
    if not targets:
        print(t["no_targets"])
        return 1
    home = hangry_home()
    dest = home / "hangry.py"
    state = read_json(home / "state.json", {})
    state = state if isinstance(state, dict) else {}
    if not dry:
        home.mkdir(parents=True, exist_ok=True)
        if Path(__file__).resolve() != dest.resolve():
            shutil.copy2(Path(__file__).resolve(), dest)
        os.chmod(dest, 0o755)
        config_path = home / "config.json"
        config = read_json(config_path, {}) if config_path.exists() else {}
        if lang or not config_path.exists():
            config = dict(config if isinstance(config, dict) else {}, lang=cfg_lang)
            write_json(config_path, config)
    notes = []
    if "claude" in targets:
        print(install_claude(dest, state, statusline, dry, t))
        notes.append(t["note_claude"].format(emoji="🍙"))
    if "codex" in targets:
        print(install_codex(dest, state, dry, t))
        notes.append(t["note_codex"])
    if "agy" in targets:
        print(install_agy(dest, dry, t))
        notes.append(t["note_agy"])
        if not dry:
            spawn_agy_refresh()
    if not dry:
        write_json(home / "state.json", state)
    print("\n".join(notes))
    if dry:
        print(t["dry_run"])
    else:
        print(t["next"].format(p=tilde(dest)))
    return 0


def cmd_uninstall(dry: bool, keep_home: bool) -> int:
    t = TEXT[load_config()["lang"]]
    home = hangry_home()
    state = read_json(home / "state.json", {})
    state = state if isinstance(state, dict) else {}
    did = False

    path = claude_dir() / "settings.json"
    settings = read_json(path) if path.exists() else None
    if isinstance(settings, dict):
        changed = False
        hooks = settings.get("hooks")
        if isinstance(hooks, dict) and isinstance(hooks.get("UserPromptSubmit"), list) \
                and has_marker(hooks["UserPromptSubmit"]):
            hooks["UserPromptSubmit"] = strip_marker(hooks["UserPromptSubmit"])
            if not hooks["UserPromptSubmit"]:
                del hooks["UserPromptSubmit"]
            if not hooks:
                del settings["hooks"]
            changed = True
        current = settings.get("statusLine")
        if isinstance(current, dict) and MARKER in str(current.get("command", "")):
            if state.get("claude_statusline"):
                settings["statusLine"] = state["claude_statusline"]
            else:
                del settings["statusLine"]
            changed = True
        if changed:
            did = True
            if not dry:
                backup(path)
                write_json(path, settings)
            print(t["uninstall_done"].format(cli="Claude Code", path=tilde(path)))

    path = codex_dir() / "hooks.json"
    doc = read_json(path) if path.exists() else None
    if isinstance(doc, dict) and isinstance(doc.get("hooks"), dict) \
            and isinstance(doc["hooks"].get("UserPromptSubmit"), list) and has_marker(doc["hooks"]["UserPromptSubmit"]):
        did = True
        doc["hooks"]["UserPromptSubmit"] = strip_marker(doc["hooks"]["UserPromptSubmit"])
        if not doc["hooks"]["UserPromptSubmit"]:
            del doc["hooks"]["UserPromptSubmit"]
        if not dry:
            if not doc["hooks"] and state.get("codex_hooks_created") and set(doc) == {"hooks"}:
                path.unlink()
            else:
                backup(path)
                write_json(path, doc)
        print(t["uninstall_done"].format(cli="Codex", path=tilde(path)))

    plugin = agy_plugin_dir()
    if (plugin / "plugin.json").exists() and (read_json(plugin / "plugin.json") or {}).get("name") == "hangry":
        did = True
        if not dry:
            shutil.rmtree(plugin)
        print(t["uninstall_done"].format(cli="agy", path=tilde(plugin)))

    if home.exists() and not keep_home:
        did = True
        if not dry:
            shutil.rmtree(home)
        print(t["uninstall_home"].format(path=tilde(home)))

    if not did:
        print(t["nothing"])
    if dry:
        print(t["dry_run"])
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="hangry", description="Your AI coding CLI gets hangry as its quota runs out.")
    parser.add_argument("--version", action="version", version=f"hangry {VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    hook = sub.add_parser("hook", help="hook entry point used by the CLIs")
    hook.add_argument("cli", choices=[c for c, _ in CLIS])
    sub.add_parser("statusline", help="Claude Code statusline tap")
    status = sub.add_parser("status", help="show how hungry each CLI is")
    status.add_argument("--no-refresh", action="store_true", help="do not call `agy -p /quota`")
    sub.add_parser("preview", help="show the injected text for every level")
    refresh = sub.add_parser("refresh", help="refresh a cached quota snapshot")
    refresh.add_argument("cli", choices=["agy"])
    install = sub.add_parser("install", help="wire hangry into the installed CLIs")
    install.add_argument("--only", help="comma separated: claude,codex,agy")
    install.add_argument("--dry-run", action="store_true")
    install.add_argument("--no-statusline", action="store_true", help="do not wrap the Claude Code statusline")
    install.add_argument("--lang", choices=sorted(TEXT))
    uninstall = sub.add_parser("uninstall", help="remove every change hangry made")
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--keep-home", action="store_true", help=f"keep {tilde(hangry_home())}")
    args = parser.parse_args(argv)

    if args.cmd == "hook":
        return cmd_hook(args.cli)
    if args.cmd == "statusline":
        return cmd_statusline()
    if args.cmd == "status":
        return cmd_status(args.no_refresh)
    if args.cmd == "preview":
        return cmd_preview()
    if args.cmd == "refresh":
        try:
            return 0 if refresh_agy() else 1
        finally:
            try:
                (cache_dir() / "agy.lock").unlink()
            except OSError:
                pass
    if args.cmd == "install":
        only = None
        if args.only:
            only = [c.strip() for c in args.only.split(",") if c.strip()]
            unknown = set(only) - {c for c, _ in CLIS}
            if unknown:
                parser.error(f"unknown CLI: {', '.join(sorted(unknown))}")
        return cmd_install(only, args.dry_run, not args.no_statusline, args.lang)
    if args.cmd == "uninstall":
        return cmd_uninstall(args.dry_run, args.keep_home)
    return 1


if __name__ == "__main__":
    sys.exit(main())
