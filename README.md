# hangry 😤

**구독 사용량이 줄어들수록 AI가 배고파집니다.**

Claude Code · Codex CLI · Antigravity CLI(`agy`)의 남은 구독 사용량을 읽고, 매 턴 AI에게 말투 지시를 한 줄 끼워 넣는 훅입니다. 사용량이 넉넉하면 친절하고 자세하게 답하고, 바닥나 가면 짧고 투덜대게 답합니다. 결과적으로 남은 토큰도 아껴 줍니다.

```
▰▰▰▰▰▰▰▰▱▱  80%  🍱 배부름   밝고 여유롭게, 도움이 되면 자세히
▰▰▰▰▱▱▱▱▱▱  40%  🍙 출출함   서론·맺음말 없이 핵심만
▰▰▱▱▱▱▱▱▱▱  20%  🥺 배고픔   3~5문장, 꼭 필요한 코드만
▱▱▱▱▱▱▱▱▱▱   5%  😤 행그리   한두 문장, 투덜투덜
```

> English summary is at the [bottom](#english).

## 실제로 이렇게 달라집니다

같은 질문("파이썬에서 딕셔너리를 값 기준으로 정렬하려면 어떻게 해?")을 Claude Code(haiku)에 레벨만 바꿔 물어본 실제 출력입니다. 길어서 일부는 줄였습니다.

**🍱 배부름 (80%)**

> 파이썬에서 딕셔너리를 값 기준으로 정렬하는 가장 간단한 방법은 **`sorted()` 함수에 `key` 파라미터를 사용**하는 것입니다:
>
> ```python
> sorted_dict = dict(sorted(data.items(), key=lambda x: x[1]))
> ```
>
> **주요 방법들:** (오름차순 · 내림차순 · 리스트로 반환 비교 표)
>
> …(중략)…
>
> 어떤 상황에서 정렬이 필요하신가요? 더 자세히 도와드릴 수 있습니다!

**😤 행그리 (5%)**

> 배고파서 짧게 말함. `sorted()`에 `key` 파라미터 쓰면 돼:
>
> ```python
> sorted_dict = dict(sorted(d.items(), key=lambda x: x[1]))
> ```
>
> Python 3.7+에선 딕셔너리 순서 보장되니까 위 방법 쓰면 됨.

말투와 길이만 바뀝니다. 주입되는 문장에 항상 "정확성·안전은 그대로 지킬 것"이 붙습니다.

## 어떻게 동작하나

```
 ┌─ 잔량 읽기 (로컬만) ──────────────────────┐     ┌─ 매 턴 주입 (각 CLI의 공식 훅) ───────────┐
 │ Claude Code  statusline 입력의 rate_limits │ ──▶ │ UserPromptSubmit → additionalContext      │
 │ Codex        세션 로그의 rate_limits       │ ──▶ │ UserPromptSubmit → additionalContext      │
 │ agy          `agy -p /quota` (5분 캐시)    │ ──▶ │ PreInvocation   → ephemeralMessage        │
 └────────────────────────────────────────────┘     └───────────────────────────────────────────┘
```

| CLI | 잔량 출처 | 기준 창 | 주입 방법 |
|---|---|---|---|
| Claude Code | statusline에 들어오는 `rate_limits`를 hangry가 가로채 캐시 (원래 statusline은 그대로 표시) | 5시간 · 주간 중 더 빡빡한 쪽 | `UserPromptSubmit` 훅 |
| Codex CLI | `~/.codex/sessions/**/rollout-*.jsonl`의 `rate_limits` | 5시간 · 주간 중 더 빡빡한 쪽 | `~/.codex/hooks.json`의 `UserPromptSubmit` 훅 |
| agy | `agy -p /quota --output-format json` (모델 호출 없음, 백그라운드 5분 캐시) | 쓰는 모델 그룹의 주간 한도 (Gemini / Claude·GPT) | 플러그인 `PreInvocation` 훅 |

- 리셋 시각이 지난 창은 가득 찬 것(100%)으로 봅니다.
- 훅 실행 시간은 약 50ms입니다. 네트워크 호출은 agy 조회뿐이고 백그라운드로 돕니다.
- 훅이 실패해도 CLI를 막지 않습니다. 항상 exit 0으로 끝나고, 오류는 `~/.hangry/error.log`에만 남깁니다.

## 설치

필요한 것: macOS 또는 Linux, Python 3.9 이상 (표준 라이브러리만 사용)

```bash
git clone https://github.com/chatgptkrguide/hangry.git
cd hangry
python3 hangry.py install --dry-run   # 무엇이 바뀌는지 먼저 확인
python3 hangry.py install             # 설치된 CLI를 자동 감지해서 연결
python3 hangry.py status              # 지금 얼마나 배고픈지
```

```
hangry 0.1.0 · 남은 구독 사용량

  Claude Code  ▰▰▰▰▱▱▱▱▱▱  42%  🍙 출출함  ·  5시간 한도 58% 사용 · 주간 한도 12% 사용 · 2시간 뒤 리셋 · 방금
  Codex        ▰▰▰▰▰▰▰▰▰▱  91%  🍱 배부름  ·  5시간 한도 9% 사용 · 주간 한도 4% 사용 · 3분 전
  agy          ▰▰▰▰▰▰▰▱▱▱  73%  🍱 배부름  ·  Gemini Models 주간 한도 27% 사용 · 4일 뒤 리셋 · 방금
```
(위 숫자는 예시입니다)

설치 후 CLI마다 한 단계씩 남아 있습니다.

- **Claude Code**: 새 세션부터 적용됩니다. statusline 끝에 `🍙 출출함 42%` 같은 배고픔 게이지가 붙습니다.
- **Codex**: `codex`를 열고 `/hooks`에서 hangry 훅을 **한 번 신뢰(trust)** 해야 동작합니다. Codex는 처음 보는 훅을 검토 전까지 실행하지 않습니다.
- **agy**: 재시작하면 플러그인이 로드됩니다.

`install`이 바꾸는 것은 아래가 전부입니다. 바꾸기 전에 `*.hangry-bak-<시각>` 백업을 남깁니다.

| 파일 | 변경 |
|---|---|
| `~/.hangry/` | hangry.py 사본, 설정, 캐시 |
| `~/.claude/settings.json` | `UserPromptSubmit` 훅 추가, `statusLine`을 hangry로 감쌈 (원래 명령은 `~/.hangry/state.json`에 보관하고 그대로 실행) |
| `~/.codex/hooks.json` | `UserPromptSubmit` 훅 추가 |
| `~/.gemini/config/plugins/hangry/` | agy 플러그인 (`plugin.json`, `hooks.json`) |

statusline을 건드리고 싶지 않다면 `--no-statusline`을 쓰세요. 다만 Claude Code는 statusline으로만 잔량을 받기 때문에 이 경우 Claude 쪽은 동작하지 않습니다. 특정 CLI만 연결하려면 `--only codex,agy`처럼 지정합니다.

## 명령어

| 명령 | 설명 |
|---|---|
| `hangry.py status` | CLI별 잔량과 배고픔 레벨 |
| `hangry.py preview` | 레벨별로 실제 주입되는 문장 |
| `hangry.py install [--only …] [--dry-run] [--no-statusline] [--lang ko\|en]` | 연결 |
| `hangry.py uninstall [--dry-run] [--keep-home]` | hangry가 바꾼 것만 골라서 되돌림 |

환경변수:

- `HANGRY_FORCE=hangry` (`full` · `peckish` · `hungry` · `hangry` 또는 `0~100`): 잔량과 상관없이 레벨을 고정합니다. 데모용
- `HANGRY_DISABLE=1`: 주입을 끕니다
- `HANGRY_LANG=en`: 주입 문장 언어

```bash
HANGRY_FORCE=hangry claude   # 행그리 모드 체험
```

## 설정

`~/.hangry/config.json` (모든 항목 선택):

```json
{
  "lang": "ko",
  "thresholds": { "full": 50, "peckish": 25, "hungry": 10 },
  "instructions": { "hangry": "해적 말투로 한 문장만." },
  "inject_when_full": true,
  "statusline_meter": true
}
```

- `thresholds`: 남은 %가 이 값보다 **크면** 해당 레벨입니다. 10 이하는 행그리
- `instructions`: 레벨별 지시문을 바꿉니다. 캐릭터를 입혀도 됩니다
- `inject_when_full: false`: 배부를 때는 아무것도 넣지 않아서 토큰을 아낍니다

## 안전과 개인정보

- **토큰·쿠키·OAuth 자격증명을 읽지 않습니다.** 비공식 사용량 API도 부르지 않습니다. 쓰는 데이터는 각 CLI가 직접 로컬에 남기거나 보여주는 값뿐입니다 (statusline 입력, 세션 로그, `agy -p /quota`).
- 외부로 아무것도 보내지 않습니다. 캐시는 `~/.hangry/cache/`에만 남습니다.
- 주입 문장은 매 턴 한 줄입니다(한국어 기준 대략 100토큰 안팎). 아깝다면 `inject_when_full: false`를 쓰세요.

## 검증한 버전

| CLI | 버전 | 확인한 것 |
|---|---|---|
| Claude Code | 2.1.285 | statusline `rate_limits`, `UserPromptSubmit` 주입 |
| Codex CLI | 0.158.0 | 세션 로그 `rate_limits`, `UserPromptSubmit` 주입 |
| Antigravity CLI | 1.2.13 | `/quota` JSON, `PreInvocation` 주입 |

각 CLI에서 레벨을 강제로 바꾸고 "주입된 모드 이름을 말해 봐"라고 물었을 때 정확히 답하는지, 끈 상태에서는 `NONE`이라고 답하는지 확인했습니다. CLI 업데이트로 로그 형식이 바뀌면 hangry는 조용히 아무것도 주입하지 않는 쪽으로 동작합니다.

## 개발

```bash
python3 -m unittest -v    # 실제 HOME은 건드리지 않고 임시 디렉터리에서 실행
```

## 제거

```bash
python3 hangry.py uninstall
```

hangry가 넣은 훅만 골라서 빼고, statusline을 원래 명령으로 되돌린 다음 `~/.hangry`를 지웁니다. 다른 훅과 설정은 그대로 둡니다.

---

## English

**hangry** makes your AI coding CLI get hungrier, and grumpier, as your subscription quota runs out.

It reads the quota left for **Claude Code**, **Codex CLI** and **Antigravity CLI (`agy`)** from local sources only: the statusline `rate_limits`, Codex session logs, and `agy -p /quota`. Through each CLI's official hook system, it then injects one tone instruction per turn:

| Left | Level | Tone |
|---|---|---|
| > 50% | 🍱 Well-fed | warm, relaxed, detailed when useful |
| > 25% | 🍙 Peckish | concise, no preambles |
| > 10% | 🥺 Hungry | 3-5 sentences, essentials only |
| ≤ 10% | 😤 Hangry | one or two grumpy sentences |

```bash
git clone https://github.com/chatgptkrguide/hangry.git && cd hangry
python3 hangry.py install --lang en   # auto-detects claude / codex / agy
python3 hangry.py status
```

After installing, trust the hook once via `/hooks` in Codex, and restart `agy`. Only tone and length change; every injected line reminds the model never to compromise correctness or safety. `python3 hangry.py uninstall` reverts everything hangry changed. Python 3.9+, standard library only, no network calls besides `agy -p /quota`.

## License

MIT
