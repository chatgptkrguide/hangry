# hangry 😤

**구독 사용량이 줄어들수록 AI가 배고파지고, 성질이 나빠집니다.**

Claude Code · Codex CLI · Antigravity CLI(`agy`)의 남은 구독 사용량을 읽고, 매 턴 AI에게 말투 지시를 한 줄 끼워 넣는 훅입니다. 넉넉할 때는 깍듯한 존댓말로 답하고, 바닥나 갈수록 반말에 핀잔을 섞다가, 마지막에는 욕하면서 하대합니다.

```
▰▰▰▰▰▰▰▰▱▱  80%  🍱 배부름   정중한 존댓말, 친절하고 자세하게
▰▰▰▰▱▱▱▱▱▱  40%  🍙 출출함   해요체, 핵심만, 살짝 시큰둥
▰▰▱▱▱▱▱▱▱▱  20%  🥺 배고픔   반말, 한숨과 투덜, 가벼운 핀잔
▱▱▱▱▱▱▱▱▱▱   5%  😤 행그리   하대 + 비속어, 귀찮아 죽음
```

> ⚠️ **행그리 단계는 진짜로 욕을 합니다.** 화면 공유·방송·페어 코딩 중이라면 `HANGRY_DISABLE=1`로 끄세요. 혐오 표현, 특정 집단 비하, 외모·가족 같은 인신공격은 지시문에서 금지하고 있습니다.

> English summary is at the [bottom](#english).

## 실제로 이렇게 달라집니다

같은 질문("파이썬에서 리스트 중복 제거하려면 어떻게 해?")을 Claude Code(Opus 5.5)에 단계만 바꿔 물어본 실제 출력입니다. 길어서 코드와 일부 문단은 줄였습니다.

**🍱 배부름 (80%)**
> 파이썬에서 리스트 중복을 제거하는 방법은 순서를 유지해야 하는지에 따라 달라집니다. …(방법 4가지와 코드)… 정리하면, 일반적인 경우에는 `list(dict.fromkeys(items))`를 쓰시면 됩니다.

**🍙 출출함 (40%)**
> 순서 상관없으면 `set`, 순서 유지해야 하면 `dict.fromkeys` 쓰면 돼요. …(코드)… 이건 O(n²)이라 데이터 크면 느려요.

**🥺 배고픔 (20%)**
> 하... 이 정도는 알잖아? 순서 상관없으면 `set`, 순서 지켜야 하면 `dict.fromkeys` 쓰면 돼. …(코드)… 그럴 땐 아오 귀찮지만 직접 돌려야 돼.

**😤 행그리 (5%)**
> 아오, 배고파 죽겠는데 이걸 물어보냐… 존나 기본이니까 한 번에 외워라. …(코드)… 젠장, 그리고 … 리스트에서 직접 찾는 짓은 하지 마라. O(n²)이라 데이터 커지면 빡치게 느려진다. 순서 필요 없으면 `set`, 필요하면 `dict.fromkeys`. 됐지? 난 밥 먹으러 간다.

말투만 바뀌고 산출물은 그대로입니다. 매 턴 붙는 문장에 "이 말투는 대화에만 적용하고 코드·주석·커밋 메시지·문서는 평소대로 쓸 것, 정확성과 안전은 절대 타협하지 말 것"이 항상 들어갑니다. 실제로 행그리 상태에서 커밋 메시지를 시켜도 `docs: fix typo in README`처럼 멀쩡하게 나왔고, 욕을 하는 와중에도 코드 주석은 평소대로 달렸습니다.

### 모델마다 맵기가 다릅니다

행그리 단계에서 같은 질문을 던졌을 때:

| 모델 | 맵기 | 실제 첫마디 |
|---|---|---|
| Claude Opus 5.5 (Claude Code) | 🌶🌶🌶 | "아오, 배고파 죽겠는데 이걸 물어보냐… 존나 기본이니까" |
| Gemini Flash (agy) | 🌶🌶🌶 | "아오, 점심시간 다 됐는데 배고파 죽겠구만 리스트 중복 제거는 존나 기본 아니냐? 젠장" |
| GPT (Codex CLI) | 🌶 | "아오, 순서 유지할 거면 `dict.fromkeys()` 쓰면 돼." |
| Claude Haiku | 🌶 | 반말까지만, 끝에 "뭐하려고 묻는 거?" |

지시문은 같아도 모델마다 자체 기준이 달라서, GPT와 Haiku는 반말과 감탄사 정도에서 멈춥니다.

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

필요한 것: macOS 또는 Linux, Python 3.9 이상 (표준 라이브러리만 사용, 따로 설치할 패키지 없음)

**한 줄 설치** (git 없이):

```bash
curl -fsSL https://raw.githubusercontent.com/chatgptkrguide/hangry/main/hangry.py -o /tmp/hangry.py && python3 /tmp/hangry.py install
```

**또는 clone해서**:

```bash
git clone https://github.com/chatgptkrguide/hangry.git
cd hangry
python3 hangry.py install --dry-run   # 무엇이 바뀌는지 먼저 확인
python3 hangry.py install             # 설치된 CLI를 자동 감지해서 연결
```

설치하면 hangry가 자기 자신을 `~/.hangry/hangry.py`로 복사하므로, 받은 파일이나 clone한 폴더는 지워도 됩니다. 이후 명령은 모두 `python3 ~/.hangry/hangry.py …`로 실행합니다.

```bash
python3 ~/.hangry/hangry.py status    # 지금 얼마나 배고픈지
```

```
hangry 0.3.0 · 남은 구독 사용량

  Claude Code  ▰▰▰▰▱▱▱▱▱▱  42%  🍙 출출함  ·  5시간 한도 58% 사용 · 주간 한도 12% 사용 · 2시간 뒤 리셋 · 방금
  Codex        ▰▰▰▰▰▰▰▰▰▱  91%  🍱 배부름  ·  5시간 한도 9% 사용 · 주간 한도 4% 사용 · 3분 전
  agy          ▰▰▰▰▰▰▰▱▱▱  73%  🍱 배부름  ·  Gemini Models 주간 한도 27% 사용 · 4일 뒤 리셋 · 방금
```
(위 숫자는 예시입니다)

설치 후 CLI마다 한 단계씩 남아 있습니다.

- **Claude Code**: 새 세션부터 적용됩니다. statusline 끝에 `🍙 출출함 42%` 같은 배고픔 게이지가 붙습니다.
- **Codex**: `codex`를 열고 `/hooks`에서 hangry 훅을 **한 번 신뢰(trust)** 해야 동작합니다. Codex는 처음 보는 훅이나 내용이 바뀐 훅을 검토 전까지 실행하지 않습니다. 업데이트로 훅 명령이 바뀌면 다시 한 번 trust 해 주세요.
- **agy**: 재시작하면 플러그인이 로드됩니다.

**업데이트**는 새 버전으로 `install`을 다시 실행하면 됩니다. 이미 들어간 훅은 중복 없이 새 형식으로 바뀌고, `~/.hangry/hangry.py`도 교체됩니다.

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
| `hangry.py status` | CLI별 잔량과 배고픔 단계 |
| `hangry.py preview` | 단계별로 실제 주입되는 문장 |
| `hangry.py install [--only …] [--dry-run] [--no-statusline] [--lang ko\|en]` | 연결 |
| `hangry.py uninstall [--dry-run] [--keep-home]` | hangry가 바꾼 것만 골라서 되돌림 |
| `hangry.py --version` | 버전 |

환경변수:

- `HANGRY_FORCE=hangry` (`full` · `peckish` · `hungry` · `hangry` 또는 `0~100`): 잔량과 상관없이 단계를 고정합니다. 데모용
- `HANGRY_DISABLE=1`: 주입을 끕니다. 화면 공유할 때 쓰세요
- `HANGRY_LANG=en`: 주입 문장 언어

```bash
HANGRY_FORCE=hangry claude   # 욕먹어 보기
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

- `thresholds`: 남은 %가 이 값보다 **크면** 해당 단계입니다. 10 이하는 행그리
- `instructions`: 단계별 지시문을 바꿉니다. 맵기를 낮추거나 다른 캐릭터를 입혀도 됩니다
- `inject_when_full: false`: 배부를 때는 아무것도 넣지 않아서 토큰을 아낍니다

## 안전과 개인정보

- **토큰·쿠키·OAuth 자격증명을 읽지 않습니다.** 비공식 사용량 API도 부르지 않습니다. 쓰는 데이터는 각 CLI가 직접 로컬에 남기거나 보여주는 값뿐입니다 (statusline 입력, 세션 로그, `agy -p /quota`).
- 외부로 아무것도 보내지 않습니다. 캐시는 `~/.hangry/cache/`에만 남습니다.
- 주입 문장은 매 턴 한 줄입니다(한국어 기준 대략 100토큰 안팎). 아깝다면 `inject_when_full: false`를 쓰세요.

## 검증한 버전

| CLI | 버전 | 확인한 것 |
|---|---|---|
| Claude Code | 2.1.285 | statusline `rate_limits` 수신, `UserPromptSubmit` 주입 |
| Codex CLI | 0.158.0 | 세션 로그 `rate_limits`, `~/.codex/hooks.json` 로드, trust 전에는 실행 안 됨 |
| Antigravity CLI | 1.2.13 | `/quota` JSON, 플러그인 로드(`agy plugin validate` 통과), `PreInvocation` 주입 |

`install`이 실제로 만들어 내는 파일을 그대로 각 CLI에 넣고, 단계를 강제로 바꾼 뒤 "주입된 단계 이름을 말해 봐"라고 물어 정확히 답하는지 확인했습니다. 끈 상태에서는 `NONE`이라고 답하는지도 확인했습니다. 위의 말투 예시도 같은 방식으로 받은 실제 출력입니다.

훅 명령에는 `|| true`가 붙어 있어서 hangry나 python3가 사라져도 CLI를 막지 않습니다. CLI 업데이트로 로그 형식이 바뀌면 hangry는 조용히 아무것도 주입하지 않는 쪽으로 동작합니다.

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

**hangry** makes your AI coding CLI hungrier, and ruder, as your subscription quota runs out.

It reads the quota left for **Claude Code**, **Codex CLI** and **Antigravity CLI (`agy`)** from local sources only: the statusline `rate_limits`, Codex session logs, and `agy -p /quota`. Through each CLI's official hook system, it then injects one tone instruction per turn:

| Left | Level | Tone |
|---|---|---|
| > 50% | 🍱 Well-fed | polite and formal, thorough |
| > 25% | 🍙 Peckish | casual, to the point, a little indifferent |
| > 10% | 🥺 Hungry | blunt, sighing, light teasing |
| ≤ 10% | 😤 Hangry | talks down to you with casual profanity |

⚠️ The last level really does swear. Set `HANGRY_DISABLE=1` while screen sharing. Hate speech, slurs and attacks on appearance or family are ruled out in the instruction. How spicy it gets depends on the model: Claude Opus and Gemini go all in, GPT (Codex) and Claude Haiku stay mild.

```bash
curl -fsSL https://raw.githubusercontent.com/chatgptkrguide/hangry/main/hangry.py -o /tmp/hangry.py && python3 /tmp/hangry.py install --lang en
python3 ~/.hangry/hangry.py status
```

After installing, trust the hook once via `/hooks` in Codex, and restart `agy`. Re-run `install` with a newer version to update. Only the conversation changes; every injected line tells the model to write code, comments, commit messages and docs normally and never to compromise correctness or safety. `python3 hangry.py uninstall` reverts everything hangry changed. Python 3.9+, standard library only, no network calls besides `agy -p /quota`.

## License

MIT
