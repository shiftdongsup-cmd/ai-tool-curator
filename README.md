# AI News Daily Feed (Slack)

매일 오후 5시에 AI 관련 RSS 소스를 수집해 슬랙 Webhook으로 요약 피드를 보내는 앱입니다.

## 1) 실행 준비 (가상환경 없이)

```bash
python --version
```

의존성(`feedparser`, `requests`)은 실행 시 자동 설치됩니다.
원하면 수동으로 아래 명령으로 먼저 설치해도 됩니다.

```bash
pip install -r requirements.txt
```

## 2) 설정

1. `.env.example`을 복사해서 `.env` 생성
2. `SLACK_WEBHOOK_URL` 입력
3. 필요하면 `sources.json`에서 수집 사이트 수정

```bash
copy .env.example .env
```

## 3) 테스트 실행 (즉시 1회)

```bash
python crawling.py --once
```

최초 실행 시 필요한 패키지가 없으면 자동으로 설치 후 계속 진행합니다.
`SLACK_WEBHOOK_URL`이 없으면 자동으로 dry-run 모드로 전환되어, 슬랙 전송 대신 콘솔에 결과를 출력합니다.

## 4) 상시 실행 (내부 스케줄러)

```bash
python crawling.py
```

기본값은 매일 `17:00` 실행이며, `.env`의 `SCHEDULE_TIME`으로 변경할 수 있습니다.

기본 타임존은 `Asia/Seoul`이며 `.env`의 `SCHEDULE_TIMEZONE`으로 변경할 수 있습니다.

슬랙 채널은 `.env`의 `SLACK_CHANNEL`로 지정할 수 있고 기본값은 `#ai-tool-news`입니다.
메시지 본문은 링크 중심으로 보내며, 각 항목의 요약 문구는 한글 한 줄 형태로 전송됩니다.

## 5) Windows 작업 스케줄러 추천 방식

내부 무한루프 대신 작업 스케줄러에서 매일 17:00에 1회 실행하도록 설정하는 방법도 안정적입니다.

- 프로그램: `python`
- 인수: `crawling.py --once`
- 시작 위치: 프로젝트 폴더

## 파일 설명

- `crawling.py`: 수집/필터링/슬랙 전송/스케줄링
- `sources.json`: 수집 사이트 목록
- `.env`: 환경변수 (직접 생성)
- `requirements.txt`: 의존성
- `.github/workflows/daily-ai-news.yml`: GitHub Actions 매일 17:00(KST) 자동 실행

## GitHub Actions(권장)

PC를 켜두지 않아도 GitHub에서 매일 자동 실행하려면:

1. 저장소 `Settings` -> `Secrets and variables` -> `Actions`에서 `SLACK_WEBHOOK_URL` 추가
2. 워크플로우 파일이 포함된 커밋을 `main` 브랜치에 푸시
3. `Actions` 탭에서 `Daily AI Tool News`가 매일 17:00(KST)에 동작하는지 확인
