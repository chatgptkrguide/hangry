# Security Policy / 보안 정책

## Reporting a vulnerability / 취약점 제보

Please report security issues privately through GitHub: **Security → Report a vulnerability** on this repository. Do not open a public issue for them.

보안 문제는 공개 이슈 대신 이 저장소의 **Security → Report a vulnerability**로 비공개 제보해 주세요.

Only the latest release is supported. / 최신 릴리스만 지원합니다.

## What hangry touches / hangry가 다루는 것

- Reads: Claude Code statusline input (`rate_limits`), Codex session logs (`~/.codex/sessions`), the output of `agy -p /quota`. It never reads tokens, cookies or OAuth credentials.
- Writes: `~/.hangry/`, plus its own entries in `~/.claude/settings.json`, `~/.codex/hooks.json` and `~/.gemini/config/plugins/hangry/` (with backups of existing files).
- Network: none, except running the official `agy -p /quota` command.

- 읽는 것: Claude Code statusline 입력(`rate_limits`), Codex 세션 로그(`~/.codex/sessions`), `agy -p /quota` 출력. 토큰·쿠키·OAuth 자격증명은 읽지 않습니다.
- 쓰는 것: `~/.hangry/`와 `~/.claude/settings.json`, `~/.codex/hooks.json`, `~/.gemini/config/plugins/hangry/` 안의 hangry 항목(기존 파일은 백업).
- 네트워크: 공식 `agy -p /quota` 명령 실행 외에는 없습니다.
