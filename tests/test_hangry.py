"""Tests for hangry. Every test runs against a throwaway HOME; all quota data is synthetic."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "hangry.py"

spec = importlib.util.spec_from_file_location("hangry", SCRIPT)
hangry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hangry)

ENV_KEYS = ("HOME", "HANGRY_HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "HANGRY_FORCE",
            "HANGRY_LANG", "HANGRY_AGY_BIN", "HANGRY_DISABLE", "LANG", "LC_ALL", "LC_MESSAGES")

AGY_QUOTA = {
    "status": "SUCCESS",
    "command": {"name": "usage", "data": {"groups": [
        {"name": "Gemini Models", "description": "Models within this group: Gemini Flash, Gemini Pro",
         "buckets": [{"id": "gemini-weekly", "window": "weekly", "remaining_fraction": 0.3,
                      "reset_time": "2099-01-01T00:00:00Z"}]},
        {"name": "Claude and GPT models", "description": "Models within this group: Claude Opus, GPT-OSS",
         "buckets": [{"id": "3p-weekly", "window": "weekly", "remaining_fraction": 0.9,
                      "reset_time": "2099-01-01T00:00:00Z"}]},
    ]}},
}


def codex_event(primary_used, secondary_used, resets_at, limit_id="codex"):
    return {"timestamp": "2026-01-02T03:04:05.000Z", "type": "event_msg", "payload": {
        "type": "token_count", "info": None, "rate_limits": {
            "limit_id": limit_id,
            "primary": {"used_percent": primary_used, "window_minutes": 300, "resets_at": resets_at},
            "secondary": {"used_percent": secondary_used, "window_minutes": 10080, "resets_at": resets_at},
        }}}


class Sandbox(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        os.environ["HOME"] = str(self.home)
        os.environ["LANG"] = "en_US.UTF-8"
        os.environ["HANGRY_AGY_BIN"] = str(self.home / "no-agy-here")
        self.now = time.time()

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def run_cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True,
                              text=True, env=dict(os.environ), timeout=30)

    def write(self, rel, data):
        path = self.home / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return path


class LevelTests(Sandbox):
    def test_thresholds(self):
        th = hangry.DEFAULT_THRESHOLDS
        self.assertEqual(hangry.level_for(100, th), "full")
        self.assertEqual(hangry.level_for(50.1, th), "full")
        self.assertEqual(hangry.level_for(50, th), "peckish")
        self.assertEqual(hangry.level_for(25, th), "hungry")
        self.assertEqual(hangry.level_for(10, th), "hangry")
        self.assertEqual(hangry.level_for(0, th), "hangry")

    def test_expired_window_counts_as_refilled(self):
        windows = [{"kind": "5h", "used": 95, "resets_at": self.now - 1},
                   {"kind": "7d", "used": 30, "resets_at": self.now + 3600}]
        q = hangry.summarize("x", windows, self.now, self.now)
        self.assertEqual(q["remaining"], 70)
        self.assertEqual(q["window"]["kind"], "7d")

    def test_force(self):
        os.environ["HANGRY_FORCE"] = "hangry"
        self.assertEqual(hangry.read_quota("codex")["remaining"], 5)
        os.environ["HANGRY_FORCE"] = "33"
        self.assertEqual(hangry.read_quota("claude")["remaining"], 33)
        os.environ["HANGRY_FORCE"] = "nonsense"
        self.assertIsNone(hangry.forced_quota("claude", self.now))

    def test_config_overrides(self):
        self.write(".hangry/config.json", {"lang": "ko", "thresholds": {"full": 90},
                                           "instructions": {"full": "custom!"}, "inject_when_full": False})
        cfg = hangry.load_config()
        self.assertEqual(cfg["lang"], "ko")
        self.assertEqual(hangry.level_for(80, cfg["thresholds"]), "peckish")
        self.assertIsNone(hangry.instruction_text({"remaining": 95, "window": {"kind": "5h"}}, cfg))
        os.environ["HANGRY_LANG"] = "en"
        self.assertEqual(hangry.load_config()["lang"], "en")


class ReaderTests(Sandbox):
    def test_claude_cache(self):
        self.write(".hangry/cache/claude.json", {"saved_at": self.now, "rate_limits": {
            "five_hour": {"used_percentage": 58, "resets_at": self.now + 600},
            "seven_day": {"used_percentage": 12, "resets_at": self.now + 86400}}})
        q = hangry.read_claude(self.now)
        self.assertEqual(q["remaining"], 42)
        self.assertEqual(q["window"]["kind"], "5h")

    def test_codex_log_ignores_decoys(self):
        good = codex_event(20, 70, self.now + 3600)
        decoy_text = {"type": "response_item", "payload": {"type": "message", "content": 'talking about "rate_limits"'}}
        other_limit = codex_event(99, 99, self.now + 3600, limit_id="some_other_model")
        lines = [json.dumps(good), json.dumps(other_limit), json.dumps(decoy_text), "not json {"]
        self.write(".codex/sessions/2026/01/02/rollout-a.jsonl", "\n".join(lines) + "\n")
        q = hangry.read_codex(self.now)
        self.assertEqual(q["remaining"], 30)
        self.assertEqual(q["window"]["kind"], "7d")

    def test_codex_prefers_transcript_path_and_newest(self):
        old = self.write(".codex/sessions/2026/01/01/rollout-old.jsonl", json.dumps(codex_event(90, 90, self.now + 99)))
        os.utime(old, (self.now - 5000, self.now - 5000))
        self.write(".codex/sessions/2026/01/02/rollout-new.jsonl", json.dumps(codex_event(10, 10, self.now + 99)))
        self.assertEqual(hangry.read_codex(self.now)["remaining"], 90)
        self.assertEqual(hangry.read_codex(self.now, str(old))["remaining"], 10)

    def test_codex_missing(self):
        self.assertIsNone(hangry.read_codex(self.now))

    def test_agy_group_by_model(self):
        self.write(".hangry/cache/agy.json", {"saved_at": self.now, "data": AGY_QUOTA["command"]["data"]})
        self.assertAlmostEqual(hangry.read_agy(self.now, "auto", refresh=False)["remaining"], 30)
        self.assertAlmostEqual(hangry.read_agy(self.now, "claude-opus-4", refresh=False)["remaining"], 90)
        self.assertEqual(hangry.read_agy(self.now, None, refresh=False)["window"]["scope"], "Gemini Models")

    def test_agy_refresh_uses_cli_output(self):
        fake = self.write("bin/agy", "#!/bin/sh\ncat <<'EOF'\n" + json.dumps(AGY_QUOTA) + "\nEOF\n")
        fake.chmod(0o755)
        os.environ["HANGRY_AGY_BIN"] = str(fake)
        self.assertFalse(hangry.refresh_agy())  # no cache dir yet: refuses to create one
        hangry.cache_dir().mkdir(parents=True)
        self.assertTrue(hangry.refresh_agy())
        self.assertAlmostEqual(hangry.read_agy(time.time(), "auto", refresh=False)["remaining"], 30)


class HookTests(Sandbox):
    def test_claude_and_codex_output(self):
        os.environ["HANGRY_FORCE"] = "hungry"
        for cli in ("claude", "codex"):
            out = json.loads(self.run_cli("hook", cli, stdin="{}").stdout)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
            self.assertIn("Hungry", out["hookSpecificOutput"]["additionalContext"])

    def test_agy_output(self):
        os.environ["HANGRY_FORCE"] = "peckish"
        out = json.loads(self.run_cli("hook", "agy", stdin='{"modelName": "auto"}').stdout)
        self.assertIn("Peckish", out["injectSteps"][0]["ephemeralMessage"])

    def test_silent_without_data_or_on_garbage(self):
        for stdin in ("", "{}", "garbage", "[1,2]"):
            for cli in ("claude", "codex"):
                r = self.run_cli("hook", cli, stdin=stdin)
                self.assertEqual((r.returncode, r.stdout), (0, ""))
            r = self.run_cli("hook", "agy", stdin=stdin)
            self.assertEqual((r.returncode, json.loads(r.stdout)), (0, {}))

    def test_disable(self):
        os.environ["HANGRY_FORCE"] = "hangry"
        os.environ["HANGRY_DISABLE"] = "1"
        self.assertEqual(self.run_cli("hook", "claude", stdin="{}").stdout, "")


class StatuslineTests(Sandbox):
    def test_tap_caches_and_wraps_original(self):
        self.write(".hangry/state.json", {"claude_statusline": {"type": "command", "command": "cat >/dev/null; echo main line; echo second"}})
        payload = {"model": {"display_name": "X"}, "rate_limits": {
            "five_hour": {"used_percentage": 80, "resets_at": int(self.now) + 600}}}
        r = self.run_cli("statusline", stdin=json.dumps(payload))
        self.assertEqual(r.stdout.splitlines(), ["main line  🥺 Hungry 20%", "second"])
        cached = json.loads((self.home / ".hangry/cache/claude.json").read_text())
        self.assertEqual(cached["rate_limits"], payload["rate_limits"])

    def test_meter_only_and_no_limits(self):
        self.assertEqual(self.run_cli("statusline", stdin='{"model": {}}').stdout, "")
        r = self.run_cli("statusline", stdin=json.dumps({"rate_limits": {"seven_day": {"used_percentage": 3}}}))
        self.assertEqual(r.stdout.strip(), "🍱 Well-fed 97%")


class InstallTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.original_settings = {
            "model": "opus",
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "guard.sh"}]}],
                      "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "mine.sh"}]}]},
            "statusLine": {"type": "command", "command": "my-statusline.sh", "padding": 0},
        }
        self.write(".claude/settings.json", self.original_settings)
        (self.home / ".codex").mkdir()
        (self.home / ".gemini").mkdir()

    def settings(self):
        return json.loads((self.home / ".claude/settings.json").read_text())

    def test_dry_run_changes_nothing(self):
        r = self.run_cli("install", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.settings(), self.original_settings)
        self.assertFalse((self.home / ".codex/hooks.json").exists())
        self.assertFalse((self.home / ".hangry").exists())

    def test_install_is_idempotent_and_uninstall_restores(self):
        for _ in range(2):
            r = self.run_cli("install")
            self.assertEqual(r.returncode, 0, r.stderr)
        s = self.settings()
        self.assertEqual(len(s["hooks"]["UserPromptSubmit"]), 2)
        self.assertIn("hangry.py", s["hooks"]["UserPromptSubmit"][1]["hooks"][0]["command"])
        self.assertIn("hangry.py", s["statusLine"]["command"])
        self.assertEqual(s["statusLine"]["padding"], 0)
        state = json.loads((self.home / ".hangry/state.json").read_text())
        self.assertEqual(state["claude_statusline"]["command"], "my-statusline.sh")
        codex = json.loads((self.home / ".codex/hooks.json").read_text())
        self.assertEqual(len(codex["hooks"]["UserPromptSubmit"]), 1)
        agy_hooks = json.loads((self.home / ".gemini/config/plugins/hangry/hooks.json").read_text())
        self.assertIn("PreInvocation", agy_hooks["hangry"])
        self.assertTrue((self.home / ".hangry/hangry.py").exists())

        r = self.run_cli("uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.settings(), self.original_settings)
        self.assertFalse((self.home / ".codex/hooks.json").exists())
        self.assertFalse((self.home / ".gemini/config/plugins/hangry").exists())
        self.assertFalse((self.home / ".hangry").exists())

    def test_codex_existing_hooks_are_kept(self):
        existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "done.sh"}]}]}}
        self.write(".codex/hooks.json", existing)
        self.run_cli("install", "--only", "codex")
        self.run_cli("uninstall")
        self.assertEqual(json.loads((self.home / ".codex/hooks.json").read_text()), existing)

    def test_broken_settings_are_left_alone(self):
        self.write(".claude/settings.json", "{ not json")
        r = self.run_cli("install", "--only", "claude")
        self.assertIn("✗", r.stdout)
        self.assertEqual((self.home / ".claude/settings.json").read_text(), "{ not json")

    def test_symlinked_settings_stay_symlinked(self):
        real = self.write("dotfiles/settings.json", self.original_settings)
        link = self.home / ".claude/settings.json"
        link.unlink()
        link.symlink_to(real)
        self.run_cli("install", "--only", "claude")
        self.assertTrue(link.is_symlink())
        self.assertIn("hangry.py", real.read_text())


if __name__ == "__main__":
    unittest.main()
