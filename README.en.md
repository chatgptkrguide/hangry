# hangry 😤

**Your AI coding CLI gets hungrier, and ruder, as your subscription quota runs out.**

[한국어](README.md) · [Quick start](#quick-start) · [Troubleshooting](#troubleshooting) · [FAQ](#faq)

A small hook for Claude Code, Codex CLI and Antigravity CLI (`agy`). It checks how much of your subscription quota is left and adds one tone instruction to every turn. Plenty left: polite and thorough. Running low: blunt and grumpy. Almost empty: it talks down to you and swears.

```
▰▰▰▰▰▰▰▰▱▱  80%  🍱 Well-fed   polite and formal, thorough
▰▰▰▰▱▱▱▱▱▱  40%  🍙 Peckish    casual, to the point, a little indifferent
▰▰▱▱▱▱▱▱▱▱  20%  🥺 Hungry     blunt, sighing, light teasing
▱▱▱▱▱▱▱▱▱▱   5%  😤 Hangry     talks down to you with casual profanity
```

Default boundaries, by quota left: **above 50% Well-fed · above 25% Peckish · above 10% Hungry · 10% or less Hangry**. You can change them in the config.

> ⚠️ **The Hangry level really does swear.** Turn it off with `HANGRY_DISABLE=1` while screen sharing, streaming or pair programming. The instruction tells the model to avoid hate speech, slurs and attacks on appearance or family.

## Preview

Real outputs from Gemini Flash (via `agy`) for the same question, "How do I remove duplicates from a list in Python?", with only the level changed. Code and some paragraphs are trimmed.

**🍱 Well-fed (80%)**
> Here are the most common and effective ways to remove duplicates from a list in Python, depending on whether you need to preserve the original order: …(three methods with code and a complexity note)…

**🥺 Hungry (20%)**
> *Sigh...* Come on, you know this one, but fine—I'll answer before my stomach eats itself. …(code)… Now please find me a snack before that last 20% quota runs out completely.

**😤 Hangry (5%)**
> For crying out loud, you interrupted my lunch break for *this*? Seriously? Removing duplicates from a list is Day 1 stuff. … Fine, look at the code, memorize it, and let me eat my damn sandwich in peace. …(code)… Now take `list(dict.fromkeys(items))` and go build something useful.

Only the conversation changes. Code, comments, commit messages and docs are written as usual: in our tests, a commit message requested at the Hangry level still came out as `docs: fix typo in README`.

**Spiciness depends on the model.** In our tests, Claude Opus and Gemini went all in, while GPT (Codex CLI) and Claude Haiku stopped at casual, slightly grumpy replies.

## Quick start

### Requirements

- macOS or Linux, Python 3.9+. Nothing else to install.
- At least one of these CLIs. hangry only wires up the ones it finds.

| CLI | Login needed |
|---|---|
| Claude Code | A Claude subscription (Pro, Max, …). With an API key there is no quota information, so the tone never changes |
| Codex CLI | Signed in with a ChatGPT account (the setup we tested) |
| Antigravity CLI (`agy`) | Signed in with a Google account |

### 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/chatgptkrguide/hangry/main/hangry.py -o /tmp/hangry.py
python3 /tmp/hangry.py install --lang en --dry-run   # preview the changes (changes nothing)
python3 /tmp/hangry.py install --lang en
```

hangry copies itself to `~/.hangry/hangry.py`, so you can delete the downloaded file afterwards.

### 2. Per-CLI final step

| CLI | What to do |
|---|---|
| Claude Code | Nothing. Send one message in a new session so the quota gets recorded; the tone changes from the next message on |
| Codex CLI | Open `codex` and **trust** the hangry hook in `/hooks`. Codex does not run hooks it has not reviewed |
| agy | Restart it |

### 3. Check

```bash
python3 ~/.hangry/hangry.py status    # quota left and level, per CLI
HANGRY_FORCE=hangry claude            # try the Hangry level regardless of quota
```

```
hangry 0.3.0 · subscription quota left

  Claude Code  ▰▰▰▰▱▱▱▱▱▱  42%  🍙 Peckish  ·  5-hour limit 58% used · weekly limit 12% used · resets in 2h · just now
  Codex        ▰▰▰▰▰▰▰▰▰▱  91%  🍱 Well-fed  ·  5-hour limit 9% used · weekly limit 4% used · 3m ago
  agy          ▰▰▰▰▰▰▰▱▱▱  73%  🍱 Well-fed  ·  Gemini Models weekly limit 27% used · resets in 4d · just now
```

(example numbers)

In Claude Code, the statusline also gets a meter such as `🍙 Peckish 42%`, appended after your original statusline, which stays as it was.

## Usage

| Command | What it does |
|---|---|
| `python3 ~/.hangry/hangry.py status` | quota left and level, per CLI |
| `python3 ~/.hangry/hangry.py preview` | the exact line injected at each level |
| `python3 ~/.hangry/hangry.py install [--only claude,codex,agy] [--dry-run] [--no-statusline] [--lang ko\|en]` | wire up or update |
| `python3 ~/.hangry/hangry.py uninstall [--dry-run] [--keep-home]` | revert only what hangry changed |
| `python3 ~/.hangry/hangry.py --version` | version |

Put an environment variable in front of a CLI to apply it to that session only.

| Variable | Effect |
|---|---|
| `HANGRY_DISABLE=1` | no tone injection, e.g. while screen sharing (`HANGRY_DISABLE=1 claude`) |
| `HANGRY_FORCE=hangry` | pin a level regardless of quota: `full` (Well-fed), `peckish` (Peckish), `hungry` (Hungry), `hangry` (Hangry), or a percentage left (`0`–`100`) |
| `HANGRY_LANG=en` | language of the injected line; defaults to your system language (`ko` for Korean, otherwise `en`) |

### Configuration

Everything in `~/.hangry/config.json` is optional.

```json
{
  "lang": "en",
  "thresholds": { "full": 50, "peckish": 25, "hungry": 10 },
  "instructions": { "hangry": "Answer like a pirate, one sentence." },
  "inject_when_full": true,
  "statusline_meter": true
}
```

| Key | Meaning |
|---|---|
| `thresholds` | a level applies when the percentage left is **above** its value; at or below the `hungry` value it is Hangry |
| `instructions` | replace the instruction for any level: tone it down or give it another character |
| `inject_when_full` | `false` injects nothing while well-fed, to save tokens |
| `statusline_meter` | `false` hides the meter in the Claude Code statusline |

## Update and uninstall

**Update** by running `install` again with a newer version. Existing hangry hooks are replaced, never duplicated. If the hook command changed, trust it again in Codex's `/hooks`.

**Uninstall** with one line:

```bash
python3 ~/.hangry/hangry.py uninstall
```

It removes only hangry's entries, restores your original statusline and deletes `~/.hangry`. Other hooks and settings are left alone.

These are the only files `install` touches. Existing config files are backed up as `*.hangry-bak-<timestamp>` before any change.

| File | Change |
|---|---|
| `~/.hangry/` | copy of hangry.py, config, cache |
| `~/.claude/settings.json` | adds a `UserPromptSubmit` hook, wraps `statusLine` (the original command is kept in `~/.hangry/state.json` and still runs) |
| `~/.codex/hooks.json` | adds a `UserPromptSubmit` hook |
| `~/.gemini/config/plugins/hangry/` | agy plugin (`plugin.json`, `hooks.json`) |

Use `--no-statusline` if you do not want the statusline wrapped. Claude Code only reports quota through the statusline, though, so the tone will not change in Claude Code.

## Troubleshooting

**`status` says "no data yet"**
- Claude Code: send one message so the statusline receives and records the quota. API key users get no quota information at all.
- Codex: chat once; the session log records the quota.
- agy: run `agy -p /quota` yourself and check that it prints your quota.

**Only Codex keeps its usual tone**
Make sure the hangry hook is trusted in `/hooks`. An update that changes the hook command needs a new trust.

**Only agy keeps its usual tone**
Restart agy. `agy plugin validate ~/.gemini/config/plugins/hangry` checks the plugin.

**It is milder than expected**
That is the model. GPT and Claude Haiku stop at casual and a bit grumpy. Spell out the tone you want in `instructions`.

**Something seems off**
Check `~/.hangry/error.log`. Hooks are built never to block the CLI, so a problem only means the tone stays the same.

## FAQ

**Can this get my account banned?**
Nobody can promise how each service applies its terms, but here is what hangry does. It never reads tokens, cookies or OAuth credentials and never calls unofficial usage APIs. It only uses values each CLI keeps locally or prints itself (statusline input, session logs, `agy -p /quota`) together with each CLI's official hook system. Nothing leaves your machine.

**Does it cost extra tokens?**
One line per turn: roughly 75–130 tokens in English depending on the level (it varies a little by tokenizer). Set `"inject_when_full": false` to skip it while well-fed.

**Will it swear in my code or commit messages?**
Every injected line says to apply the tone to the conversation only and to write code, comments, commit messages and docs normally. In our tests, commit messages and code comments stayed clean at the Hangry level. It is still an instruction a model follows, so glance over your commits.

**Can I use it at work?**
Run with `HANGRY_DISABLE=1` while screen sharing, or tone down the Hangry level with `instructions`.

**Windows?**
macOS and Linux only for now.

## How it works

```
 ┌─ read quota (local only) ──────────────────┐     ┌─ inject every turn (official hooks) ─┐
 │ Claude Code  statusline rate_limits        │ ──▶ │ UserPromptSubmit → additionalContext │
 │ Codex        session log rate_limits       │ ──▶ │ UserPromptSubmit → additionalContext │
 │ agy          `agy -p /quota` (5-min cache) │ ──▶ │ PreInvocation   → ephemeralMessage   │
 └────────────────────────────────────────────┘     └──────────────────────────────────────┘
```

| CLI | Quota source | Window | Injection |
|---|---|---|---|
| Claude Code | `rate_limits` from the statusline input, recorded by hangry | whichever of the 5-hour and weekly limits is more used | `UserPromptSubmit` hook |
| Codex CLI | `rate_limits` in `~/.codex/sessions/**/rollout-*.jsonl` | whichever of the 5-hour and weekly limits is more used | `UserPromptSubmit` hook in `~/.codex/hooks.json` |
| agy | `agy -p /quota --output-format json` (no model call, refreshed in the background every 5 minutes) | weekly limit of the model group in use (Gemini / Claude·GPT) | plugin `PreInvocation` hook |

- A limit whose reset time has passed counts as full again.
- Hooks take about 50 ms on our development machine. The only network use is the agy quota lookup, which runs in the background.
- Hook commands end with `|| true`, so even a missing hangry or python3 never blocks the CLI. If a CLI update changes its log format, hangry just injects nothing.

## Tested versions

| CLI | Version | Verified |
|---|---|---|
| Claude Code | 2.1.285 | statusline `rate_limits`, `UserPromptSubmit` injection |
| Codex CLI | 0.158.0 | session log `rate_limits`, `~/.codex/hooks.json` loading, no execution before trust |
| Antigravity CLI | 1.2.13 | `/quota` JSON, plugin loading (`agy plugin validate` passes), `PreInvocation` injection |

We put the exact files `install` writes into each CLI, pinned a level, and asked the model to name the injected level. It named the right level, and answered `NONE` with hangry disabled. The preview outputs above were collected the same way.

## Contributing

Issues and PRs are welcome. When reporting a bug, include the output of `python3 ~/.hangry/hangry.py status` and your CLI versions.

```bash
git clone https://github.com/chatgptkrguide/hangry.git && cd hangry
python3 -m unittest -v    # runs in temporary directories, never touches your real HOME
```

It is a single file, `hangry.py`, using only the standard library.

## License

MIT
