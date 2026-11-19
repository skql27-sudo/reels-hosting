# 유튜브 쇼츠 매일 업로드 런북 (@hpsiawa)

매일 07:30 KST 공개. 채널: https://www.youtube.com/@hpsiawa (구글 계정 skql27@gmail.com)
컨셉: 어르신 대상 좋은 글귀 / 건강 글귀 / 오늘 하루 행복 인사. 20~30초, 반짝이고 화려한 짤 3장이 이어지는 영상.

## 0. 준비
1. `add_repo` skql27-sudo/reels-hosting (push) → `/home/claude/reels-hosting`에 clone.
2. `mkdir -p /home/claude/shorts/fonts && cp shorts/tools/make_short.py /home/claude/shorts/`
   폰트는 `https://raw.githubusercontent.com/google/fonts/main/` 에서 받기:
   `ofl/gowunbatang/GowunBatang-Bold.ttf`, `ofl/blackhansans/BlackHanSans-Regular.ttf`,
   `ofl/nanumpenscript/NanumPenScript-Regular.ttf` → `/home/claude/shorts/fonts/`
3. `shorts/posted.json`을 읽고 **최근 30일 안에 쓴 글귀·건강 팁은 다시 쓰지 않는다.**

## 1. 글 쓰기 (spec.json)
짤 3장, 순서 고정:
1. **좋은 글** (heading 예: "오늘의 좋은 글", "마음에 새기는 글") — 인생·마음·사람에 대한 따뜻한 글
2. **건강 한마디** (heading 예: "건강 한마디", "건강 습관") — 일반적이고 안전한 생활 습관만
   (물, 걷기, 스트레칭, 수면, 웃음, 제철 음식, 계절 건강 주의 등). 약·질병 치료·수치 처방은 쓰지 않는다.
3. **오늘 하루 인사** (heading 예: "오늘 하루도", "좋은 아침입니다", 요일 인사 "행복한 금요일") + footer 한 줄

규칙
- **직접 쓴 글만** 사용. 다른 사람의 시·노래 가사·책 문장을 옮기지 않는다. 출처가 있는 명언을 쓰지 않는다.
- 어르신이 읽기 쉽게: 한 장에 4~5줄(빈 줄 포함 최대 6), 한 줄 15자 이내, 쉬운 말, 존댓말.
- `[단어]` = 크게 강조(빨강 계열), 한 장에 1~2곳. `""` = 빈 줄.
- 계절·날씨·요일을 반영 (예: 11월 → 환절기 감기, 따뜻한 차, 첫눈, 김장).
- theme: gold, rose, sky, green, lavender, red 중 3장이 서로 다르게. 건강 장은 주로 green/sky.
- 이모지·특수기호 쓰지 않는다.

```json
{"scenes":[
 {"theme":"gold","heading":"오늘의 좋은 글","lines":["좋은 사람을 만나는 것은","[행운]이지만","","좋은 사람이 되는 것은","[나의 선택]입니다"]},
 {"theme":"green","heading":"건강 한마디","lines":["하루 [물 여덟 잔]","하루 [삼십 분] 걷기","하루 [한 번] 크게 웃기","","이것이 최고의 보약입니다"]},
 {"theme":"rose","heading":"오늘 하루도","lines":["웃는 얼굴에","[복]이 들어옵니다","","오늘 하루도","[행복]하세요"],"footer":"건강하고 행복한 하루 되세요"}
]}
```

## 2. 영상 만들기
- `PREVIEW_ONLY=1 python3 make_short.py spec.json out/short.mp4` → `out/short_preview_{1,2,3}.png`를
  **직접 열어 확인** (글자 잘림, 겹침, 오타). 문제 있으면 줄을 고치고 다시.
- `python3 make_short.py spec.json out/short.mp4` → 1080x1920, 25초, 자체 합성 배경음 (약 30초 소요).
- `shorts/videos/YYYY-MM-DD.mp4`로 복사 → 커밋·푸시 →
  `https://raw.githubusercontent.com/skql27-sudo/reels-hosting/main/shorts/videos/YYYY-MM-DD.mp4` 200 확인.

## 3. 제목·설명·태그
- 제목(40자 이내, 끝에 `#shorts`): 예 `좋은 사람이 되는 것은 나의 선택입니다 | 오늘의 좋은글 #shorts`
  검색어 섞기: 좋은글, 좋은글귀, 아침인사, 건강정보, 명언 아님(직접 쓴 글이므로 "명언" 대신 "좋은글").
- 설명: 3장의 글 전문 → "오늘도 건강하고 행복한 하루 보내세요" → "구독과 좋아요는 큰 힘이 됩니다"
  → 해시태그 3~5개 (#좋은글 #아침인사 #건강정보 #오늘의글 #shorts).
- 태그: 좋은글, 좋은글귀, 아침인사, 건강, 행복, 인생글, 어르신, 시니어.

## 4. 업로드 (사용자 컴퓨터의 내장 브라우저, `mcp__remote-devices__Claude_Browser__*`)
YouTube Data API 업로드는 앱 심사 전에는 비공개로 잠기고, Windsor.ai youtube 커넥터에는 업로드 기능이 없어
YouTube Studio 웹 업로드를 쓴다.
1. `preview_start` https://studio.youtube.com → 로그인 상태(채널 @hpsiawa) 확인.
   구글 로그인 화면이 나오면 **비밀번호를 입력하지 말고** 건너뛰고 사용자에게 알린다.
2. "만들기(Create)" → "동영상 업로드" 대화상자를 연다 (또는 `https://studio.youtube.com/channel/<채널ID>/videos/upload?d=ud`).
3. 파일 넣기 — 대화상자의 `input[type=file]`에 JS로 주입:
   ```js
   const r = await fetch(RAW_URL); const b = await r.blob();
   const f = new File([b], 'YYYY-MM-DD.mp4', {type:'video/mp4'});
   const dt = new DataTransfer(); dt.items.add(f);
   const inp = document.querySelector('ytcp-uploads-file-picker input[type=file]') || document.querySelector('input[type=file]');
   inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles:true})); f.size
   ```
   CSP로 fetch가 막히면: 클라우드에서 mp4를 base64로 나눠 (조각당 ~400KB) `window.__chunks.push(...)`로
   여러 번 넣은 뒤 `atob`로 합쳐 같은 방식으로 주입.
   (성공한 방법은 아래 "검증된 방법"에 기록해 둔다.)
4. 세부정보: 제목·설명 입력(제목 칸·설명 칸은 contenteditable → 전체 선택 후 type),
   "아니요, 아동용이 아닙니다" 선택, "자세히 보기"에서 태그 입력.
5. 다음 → 다음 → 공개 상태: 지금이 07:25 이전이면 **"예약" → 오늘 07:30**, 이후면 **"공개"** 로 즉시 게시.
6. 업로드·처리 완료 후 영상 링크(https://youtube.com/shorts/<id>)를 확인.
7. `shorts/posted.json`에 `{date, video_id, title, lines(3장 전문), themes}` 추가 → 커밋·푸시.

## 실패 시
- 내장 브라우저 연결 안 됨(컴퓨터 꺼짐, 앱 꺼짐) 또는 로그아웃 상태: 영상은 만들어 저장소에 푸시하고,
  링크와 제목·설명을 남긴 뒤 "업로드 못 함 + 이유"를 알린다.
- 업로드 단계 실패 시 한 번만 재시도.

## 검증된 방법
(첫 성공 업로드 후 여기에 실제로 통한 선택자·순서를 적는다)
