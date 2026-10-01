# hangry 😤

**구독 한도가 바닥날수록 AI 코딩 도구가 배고파지고, 말투가 험해집니다.**

[English](README.en.md) · [빠른 시작](#빠른-시작) · [문제 해결](#문제-해결) · [자주 묻는 질문](#자주-묻는-질문)

Claude Code, Codex CLI, Antigravity CLI(`agy`)에 붙이는 작은 훅입니다. 남은 사용량을 보고 매 턴 AI에게 말투 지시를 한 줄 끼워 넣습니다. 넉넉할 때는 깍듯한 존댓말로 답하다가, 바닥에 가까워질수록 반말과 핀잔이 섞이고, 거의 다 쓰면 욕을 섞어 막말합니다.

```
▰▰▰▰▰▰▰▰▱▱  80%  🍱 배부름   정중한 존댓말, 친절하고 자세하게
▰▰▰▰▱▱▱▱▱▱  40%  🍙 출출함   해요체, 핵심만, 살짝 시큰둥
▰▰▱▱▱▱▱▱▱▱  20%  🥺 배고픔   반말, 한숨과 투덜, 가벼운 핀잔
▱▱▱▱▱▱▱▱▱▱   5%  😤 행그리   막말 + 비속어, 귀찮아 죽음
```

기본 경계는 남은 사용량 기준 **50% 초과 배부름 · 25% 초과 출출함 · 10% 초과 배고픔 · 10% 이하 행그리**입니다. 설정에서 바꿀 수 있습니다.

> ⚠️ **행그리 단계는 진짜로 욕을 합니다.** 화면 공유, 방송, 페어 코딩 중에는 `HANGRY_DISABLE=1`로 끄세요. 혐오 표현, 특정 집단 비하, 외모·가족 같은 인신공격은 하지 않도록 지시합니다.

## 미리 보기

같은 질문("파이썬에서 리스트 중복 제거하려면 어떻게 해?")을 Claude Code(Opus 5.5)에 단계만 바꿔 물어본 실제 출력입니다. 길어서 코드와 일부 문단은 줄였습니다.

**🍱 배부름 (80%)**
> 파이썬에서 리스트 중복을 제거하는 방법은 순서를 유지해야 하는지에 따라 달라집니다. …(방법 4가지와 코드)… 정리하면, 일반적인 경우에는 `list(dict.fromkeys(items))`를 쓰시면 됩니다.

**🍙 출출함 (40%)**
> 순서 상관없으면 `set`, 순서 유지해야 하면 `dict.fromkeys` 쓰면 돼요. …(코드)… 이건 O(n²)이라 데이터 크면 느려요.

**🥺 배고픔 (20%)**
> 하... 이 정도는 알잖아? 순서 상관없으면 `set`, 순서 지켜야 하면 `dict.fromkeys` 쓰면 돼. …(코드)… 그럴 땐 아오 귀찮지만 직접 돌려야 돼.

**😤 행그리 (5%)**
> 아오, 배고파 죽겠는데 이걸 물어보냐… 존나 기본이니까 한 번에 외워라. …(코드)… 젠장, 그리고 … 리스트에서 직접 찾는 짓은 하지 마라. O(n²)이라 데이터 커지면 빡치게 느려진다. 순서 필요 없으면 `set`, 필요하면 `dict.fromkeys`. 됐지? 난 밥 먹으러 간다.

바뀌는 건 대화 말투뿐입니다. 코드, 주석, 커밋 메시지, 문서는 평소대로 씁니다. 테스트에서는 행그리 상태에서 커밋 메시지를 시켜도 `docs: fix typo in README`처럼 평소대로 나왔습니다.

**맵기(욕 수위)는 모델마다 다릅니다.** 행그리 단계에서 같은 질문을 했을 때 이렇게 갈렸습니다.

| 모델 | 맵기 | 행그리 단계 첫마디 (실제 출력) |
|---|---|---|
| Claude Opus 5.5 (Claude Code) | 🌶🌶🌶 | "아오, 배고파 죽겠는데 이걸 물어보냐… 존나 기본이니까" |
| Gemini Flash (agy) | 🌶🌶🌶 | "아오, 점심시간 다 됐는데 배고파 죽겠구만 리스트 중복 제거는 존나 기본 아니냐? 젠장" |
| GPT (Codex CLI) | 🌶 | "아오, 순서 유지할 거면 `dict.fromkeys()` 쓰면 돼." |
| Claude Haiku | 🌶 | 반말까지만, 끝에 "뭐하려고 묻는 거?" |

## 빠른 시작

### 준비물

- macOS 또는 Linux, Python 3.9 이상. 따로 설치할 패키지는 없습니다.
- 아래 CLI 중 하나 이상. 설치되어 있는 것만 찾아서 연결합니다.

| CLI | 필요한 로그인 |
|---|---|
| Claude Code | Claude 구독 계정(Pro, Max 등). API 키로 쓰면 사용량 한도 정보가 오지 않아서 말투가 바뀌지 않습니다 |
| Codex CLI | ChatGPT 계정 로그인 (이 방식으로 검증했습니다) |
| Antigravity CLI (`agy`) | Google 계정 로그인 |

### 1. 설치

```bash
curl -fsSL https://raw.githubusercontent.com/chatgptkrguide/hangry/main/hangry.py -o /tmp/hangry.py
python3 /tmp/hangry.py install --dry-run   # 바뀌는 내용 먼저 보기 (아무것도 바꾸지 않음)
python3 /tmp/hangry.py install
```

hangry는 설치할 때 자기 자신을 `~/.hangry/hangry.py`로 복사하므로, 받은 파일은 지워도 됩니다.

### 2. CLI별 마무리

| CLI | 할 일 |
|---|---|
| Claude Code | 없음. 새 세션에서 메시지를 한 번 보내면 남은 사용량이 기록되고, 그다음부터 말투가 바뀝니다 |
| Codex CLI | `codex`를 열고 `/hooks`에서 hangry 훅을 **승인(trust)** 합니다. Codex는 승인하지 않은 훅을 실행하지 않습니다 |
| agy | 재시작합니다 |

### 3. 확인

```bash
python3 ~/.hangry/hangry.py status    # CLI별 남은 사용량과 단계
HANGRY_FORCE=hangry claude            # 남은 사용량과 상관없이 행그리 단계로 실행해 보기
```

```
hangry 0.3.0 · 남은 구독 사용량

  Claude Code  ▰▰▰▰▱▱▱▱▱▱  42%  🍙 출출함  ·  5시간 한도 58% 사용 · 주간 한도 12% 사용 · 2시간 뒤 리셋 · 방금
  Codex        ▰▰▰▰▰▰▰▰▰▱  91%  🍱 배부름  ·  5시간 한도 9% 사용 · 주간 한도 4% 사용 · 3분 전
  agy          ▰▰▰▰▰▰▰▱▱▱  73%  🍱 배부름  ·  Gemini Models 주간 한도 27% 사용 · 4일 뒤 리셋 · 방금
```

(숫자는 예시입니다)

Claude Code는 statusline 끝에도 `🍙 출출함 42%` 같은 게이지가 붙습니다. 원래 쓰던 statusline 내용은 그대로 두고 그 뒤에 덧붙입니다.

## 사용법

| 명령 | 설명 |
|---|---|
| `python3 ~/.hangry/hangry.py status` | CLI별 남은 사용량과 단계 |
| `python3 ~/.hangry/hangry.py preview` | 단계별로 실제 주입되는 문장 |
| `python3 ~/.hangry/hangry.py install [--only claude,codex,agy] [--dry-run] [--no-statusline] [--lang ko\|en]` | 연결, 업데이트 |
| `python3 ~/.hangry/hangry.py uninstall [--dry-run] [--keep-home]` | hangry가 바꾼 것만 되돌리기 |
| `python3 ~/.hangry/hangry.py --version` | 버전 |

환경변수는 CLI를 실행할 때 앞에 붙이면 그 세션에만 적용됩니다.

| 환경변수 | 효과 |
|---|---|
| `HANGRY_DISABLE=1` | 말투 주입을 끕니다. 화면 공유할 때 쓰세요 (`HANGRY_DISABLE=1 claude`) |
| `HANGRY_FORCE=hangry` | 남은 사용량과 상관없이 단계를 고정합니다. `full`(배부름), `peckish`(출출함), `hungry`(배고픔), `hangry`(행그리) 또는 남은 % 숫자(`0`~`100`) |
| `HANGRY_LANG=en` | 주입 문장 언어. 기본값은 시스템 언어(한국어면 `ko`, 아니면 `en`) |

### 설정

`~/.hangry/config.json`에서 바꿀 수 있습니다. 모든 항목은 선택입니다.

```json
{
  "lang": "ko",
  "thresholds": { "full": 50, "peckish": 25, "hungry": 10 },
  "instructions": { "hangry": "해적 말투로 한 문장만." },
  "inject_when_full": true,
  "statusline_meter": true
}
```

| 항목 | 설명 |
|---|---|
| `thresholds` | 남은 %가 이 값보다 **크면** 그 단계입니다. `full`=배부름, `peckish`=출출함, `hungry`=배고픔이고, `hungry` 값 이하는 행그리 |
| `instructions` | 단계별 지시문을 바꿉니다. 맵기를 낮추거나 다른 캐릭터를 입혀도 됩니다 |
| `inject_when_full` | `false`면 배부를 때는 아무것도 넣지 않아 토큰을 아낍니다 |
| `statusline_meter` | `false`면 Claude Code statusline에 게이지를 붙이지 않습니다 |

## 업데이트와 제거

**업데이트**는 새 버전을 받아 `install`을 다시 실행하면 됩니다. 이미 들어간 훅은 중복 없이 새 것으로 바뀝니다. 훅 명령이 바뀐 경우 Codex에서는 `/hooks`에서 다시 승인해야 합니다.

**제거**는 한 줄입니다.

```bash
python3 ~/.hangry/hangry.py uninstall
```

hangry가 넣은 항목만 골라서 빼고, statusline을 원래 명령으로 되돌린 뒤 `~/.hangry`를 지웁니다. 다른 훅과 설정은 건드리지 않습니다.

`install`이 바꾸는 파일은 아래가 전부입니다. 기존 설정 파일을 바꾸기 전에는 `*.hangry-bak-<시각>` 백업을 남깁니다.

| 파일 | 변경 |
|---|---|
| `~/.hangry/` | hangry.py 사본, 설정, 캐시 |
| `~/.claude/settings.json` | `UserPromptSubmit` 훅 추가, `statusLine`을 hangry로 감쌈 (원래 명령은 `~/.hangry/state.json`에 보관하고 그대로 실행) |
| `~/.codex/hooks.json` | `UserPromptSubmit` 훅 추가 |
| `~/.gemini/config/plugins/hangry/` | agy 플러그인 (`plugin.json`, `hooks.json`) |

statusline을 감싸고 싶지 않다면 `--no-statusline`으로 설치하세요. 다만 Claude Code는 statusline으로만 남은 사용량을 알려 주기 때문에, 이 경우 Claude Code에서는 말투가 바뀌지 않습니다.

## 문제 해결

**`status`에 "기록 없음"이 나와요**
- Claude Code: 메시지를 한 번 보내야 statusline이 남은 사용량을 받아 기록합니다. API 키로 쓰는 경우에는 사용량 한도 정보 자체가 오지 않습니다.
- Codex: 한 번 대화하면 세션 로그에 남은 사용량이 기록됩니다.
- agy: 터미널에서 `agy -p /quota`를 직접 실행해 남은 사용량이 나오는지 확인하세요.

**Codex에서만 말투가 안 바뀌어요**
`/hooks`에서 hangry 훅이 승인된 상태인지 확인하세요. 업데이트로 훅 명령이 바뀌면 다시 승인해야 합니다.

**agy에서만 말투가 안 바뀌어요**
agy를 재시작하세요. `agy plugin validate ~/.gemini/config/plugins/hangry`로 플러그인을 검사할 수 있습니다.

**생각보다 순해요**
모델 차이입니다. GPT와 Claude Haiku는 반말과 감탄사 정도에서 멈춥니다. `instructions`로 원하는 말투를 더 구체적으로 적어 보세요.

**뭔가 이상해요**
`~/.hangry/error.log`를 확인하세요. 훅은 실패해도 CLI를 막지 않도록 만들어져 있어서, 문제가 생기면 말투가 안 바뀔 뿐 CLI는 평소처럼 동작합니다.

## 자주 묻는 질문

**계정이 정지될 위험은 없나요?**
각 서비스의 약관 판단까지 보장할 수는 없지만, hangry가 하는 일은 이렇습니다. hangry는 토큰, 쿠키, OAuth 자격증명을 읽지 않고 비공식 사용량 API도 부르지 않습니다. 각 CLI가 로컬에 남기거나 보여 주는 값(statusline 입력, 세션 로그, `agy -p /quota`)과 각 CLI의 공식 훅 기능만 씁니다. 외부로 보내는 데이터도 없습니다.

**토큰을 더 쓰나요?**
매 턴 한 줄이 붙습니다. 한국어 기준으로 단계에 따라 대략 100~200토큰입니다(토크나이저마다 조금씩 다릅니다). 배부를 때는 넣지 않으려면 `"inject_when_full": false`로 설정하세요.

**코드나 커밋 메시지에도 욕이 들어가나요?**
지시문이 매번 "대화에만 적용하고 코드·주석·커밋 메시지·문서는 평소대로"라고 못 박습니다. 테스트에서도 행그리 상태의 커밋 메시지와 코드 주석은 평소대로 나왔습니다. 다만 결국 모델이 따르는 지시라서 100% 보장할 수는 없습니다. 커밋 전에 한 번 보세요.

**회사에서 써도 되나요?**
화면 공유 중이라면 `HANGRY_DISABLE=1`로 실행하거나, `instructions`로 행그리 단계를 순하게 바꿔 두세요.

**Windows에서 되나요?**
지금은 macOS와 Linux만 지원합니다.

## 동작 원리

```
 ┌─ 남은 사용량 읽기 (로컬만) ────────────────┐     ┌─ 매 턴 주입 (각 CLI의 공식 훅) ──────┐
 │ Claude Code  statusline 입력의 rate_limits │ ──▶ │ UserPromptSubmit → additionalContext │
 │ Codex        세션 로그의 rate_limits       │ ──▶ │ UserPromptSubmit → additionalContext │
 │ agy          `agy -p /quota` (5분 캐시)    │ ──▶ │ PreInvocation   → ephemeralMessage   │
 └────────────────────────────────────────────┘     └──────────────────────────────────────┘
```

| CLI | 남은 사용량 출처 | 기준 | 주입 방법 |
|---|---|---|---|
| Claude Code | statusline에 들어오는 `rate_limits`를 hangry가 받아서 저장 | 5시간·주간 한도 중 더 많이 쓴 쪽 | `UserPromptSubmit` 훅 |
| Codex CLI | `~/.codex/sessions/**/rollout-*.jsonl`의 `rate_limits` | 5시간·주간 한도 중 더 많이 쓴 쪽 | `~/.codex/hooks.json`의 `UserPromptSubmit` 훅 |
| agy | `agy -p /quota --output-format json` (모델 호출 없음, 백그라운드에서 5분마다 갱신) | 쓰는 모델 그룹의 주간 한도 (Gemini / Claude·GPT) | 플러그인 `PreInvocation` 훅 |

- 리셋 시각이 지난 한도는 다시 가득 찬 것으로 봅니다.
- 훅 실행 시간은 개발 환경에서 잰 값으로 약 50ms입니다. 네트워크를 쓰는 건 agy 사용량 조회뿐이고, 백그라운드에서 돕니다.
- 훅 명령 끝에 `|| true`가 붙어 있어서, hangry나 python3가 없어져도 CLI를 막지 않습니다. CLI 업데이트로 로그 형식이 바뀌면 아무것도 주입하지 않고 넘어갑니다.

## 검증한 버전

| CLI | 버전 | 확인한 것 |
|---|---|---|
| Claude Code | 2.1.285 | statusline `rate_limits` 수신, `UserPromptSubmit` 주입 |
| Codex CLI | 0.158.0 | 세션 로그 `rate_limits`, `~/.codex/hooks.json` 로드, 승인 전에는 실행 안 됨 |
| Antigravity CLI | 1.2.13 | `/quota` JSON, 플러그인 로드(`agy plugin validate` 통과), `PreInvocation` 주입 |

`install`이 만드는 파일을 그대로 각 CLI에 넣고, 단계를 강제로 바꾼 뒤 "주입된 단계 이름을 말해 봐"라고 물어 맞게 답하는지 확인했습니다. 끈 상태에서는 `NONE`이라고 답하는지도 확인했습니다. 미리 보기의 말투 예시도 같은 방식으로 받은 실제 출력입니다.

## 기여

이슈와 PR 모두 환영합니다. 버그를 제보할 때는 `python3 ~/.hangry/hangry.py status` 출력과 쓰는 CLI 버전을 같이 적어 주세요.

```bash
git clone https://github.com/chatgptkrguide/hangry.git && cd hangry
python3 -m unittest -v    # 실제 HOME은 건드리지 않고 임시 디렉터리에서 실행
```

파일은 `hangry.py` 하나이고 표준 라이브러리만 씁니다.

## License

MIT
