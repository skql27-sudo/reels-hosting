# 릴스 자동 게시 런북 (self_diy_2v)

매일 08:00(오전, `cute` 아기자기) / 17:00(오후, `modern` 모던) KST에 실행.
주제: 다이소·무인양품·모던하우스의 자취/살림/인테리어 꿀템, 20초 내외, 가격 표시, 시즌 상품 우선.

## 0. 준비
1. `add_repo` skql27-sudo/reels-hosting (push) → `/home/claude/reels-hosting`에 clone.
2. 폰트: `mkdir -p /home/claude/work/fonts` 후 GitHub google/fonts에서
   `ofl/jua/Jua-Regular.ttf` 다운로드. `tools/make_reel.py`를 `/home/claude/work/`에 복사
   (스크립트는 자기 폴더의 `fonts/`를 씀). ffmpeg, Pillow, numpy 필요.
3. `posted.json`을 읽고 **최근 14일 안에 올린 상품은 다시 고르지 않는다.**

## 1. 상품 조사 (사용자 컴퓨터의 내장 브라우저, `mcp__remote-devices__Claude_Browser__*`)
클라우드 셸에서는 세 쇼핑몰 접속이 막혀 있음. 브라우저 탭에서 `javascript_tool`로 조회.
- 다이소몰 (https://www.daisomall.co.kr/ds/rank/C105 탭에서 실행)
  - 판매 랭킹: `fetch('/ssn/search/GoodsBestSale?period=R&pageNum=1&cntPerPage=200&largeExhCtgrNo=&isCategory=0&soldOutYn=N')`
  - 검색: `fetch('/ssn/search/SearchGoods?searchTerm=<키워드>&pageNum=1&cntPerPage=40')`
    → `resultSet.result.find(x=>x.resultDocuments).resultDocuments`
    (pdNo, pdNm, pdPrc, newPdYn, revwCnt, pdImgUrl → `https://cdn.daisomall.co.kr`+pdImgUrl)
  - 시즌 키워드 예: 크리스마스마켓, 무드등, 수면양말, 극세사 담요, 문풍지, 가습기, 신학기/봄이면 수납 등.
- 무인양품 (https://www.mujikorea.co.kr): `get_page_text`로 메인/기획전 상품명·가격, 이미지는 DOM에서
  `product.mujikorea.co.kr/images/...?w=1000`.
- 모던하우스 (https://modernhouse.elandmall.co.kr): 메인 스크롤 후 이미지 `data-src`/`data-srcset`
  (`item.elandrs.com/...?h=1000&q=95`). 가격은 "최종할인가" → 영상·캡션에 "할인가" 표기.
- 구성: 상품 5~6개, 세 브랜드가 모두 들어가게, 가격대 섞기. 시즌/신상(newPdYn=Y)·리뷰 많은 상품 우선.
- 오전(cute): 귀엽고 아기자기한 소품·캐릭터·크리스마스/계절 소품.
  오후(modern): 무채색·심플한 수납·주방·인테리어·생활 가전 소품.
- **사람(모델)이 나오는 상품 사진은 쓰지 않는다.** 이미지가 사람 위주면 다른 상품으로 교체.

## 2. 상품 이미지 가져오기
1. 이미지와 같은 출처의 페이지로 이동(다이소는 daisomall 페이지에서 CDN fetch 가능,
   모던하우스/무인양품은 이미지 URL 자체로 navigate).
2. JS: `fetch(url)` → blob → `<a download>` 클릭. 다이소 원본은 크므로 OffscreenCanvas로 1200px JPEG 변환.
3. 탭을 떠나기 전에 `device_list_dir C:\Users\smedi_ohcxjq\Downloads`에서 새 `.tmp` 파일(크기로 매칭)을
   찾아 즉시 `device_stage_files` → `/mnt/user-data/uploads/Downloads/`에서 복사해 이름 붙이기.
   (탭을 옮기면 .tmp가 사라짐)
4. **다운로드 폴더가 연결 안 된 경우(대체 경로)**: 이미지와 같은 출처 페이지에서 JS로 `fetch`→OffscreenCanvas(최대 1000px)
   →webp q0.9→base64를 `JSON.stringify({key:b64,...})`로 반환. 결과가 커서 툴 결과가 클라우드의
   `tool-results/*.txt` 파일로 저장되면, 그 JSON의 `[0].text`(JSON 문자열)를 두 번 json.loads 해서 디코드.

## 3. 영상 만들기
`/home/claude/work/spec.json`:
```json
{"style":"cute 또는 modern","title":"두 줄\n제목","subtitle":"다이소 / 무인양품 / 모던하우스",
 "outro":"저장해두고\n장보러 가기!","items":[{"brand":"다이소","name":"...","price":"1,000원","note":"겨울 신상","img":"img/x.jpg"}]}
```
- 제목·부제·아웃트로에 이모지와 가운뎃점(·)은 쓰지 않는다(폰트에 없음, 대신 `/`).
- 먼저 `PREVIEW_ONLY=1 python3 make_reel.py spec.json out/reel.mp4`로 프레임 확인 후 전체 렌더.
- 결과: 1080x1920, 약 20.4초, 자체 합성 배경음.

## 4. 업로드 & 게시
1. `videos/YYYY-MM-DD_am.mp4` 또는 `_pm.mp4`로 커밋·푸시,
   `https://raw.githubusercontent.com/skql27-sudo/reels-hosting/main/videos/<파일>`가 200인지 확인.
2. 캡션: 첫 줄 훅 + 핵심 키워드(다이소/무인양품/모던하우스, 자취, 살림, 계절어) → 번호 목록(브랜드 상품명 가격)
   → "💾 저장" 유도 → 질문 한 줄 → "*가격은 M/D 각 온라인몰 기준이며 바뀔 수 있어요"
   → **해시태그 최대 5개**(시즌·검색량 높은 것, 예: #다이소신상 #다이소크리스마스 #자취템 #겨울살림템 #무인양품).
3. Windsor.ai `execute_action` connector=`instagram`, account=`17841451789241563`,
   action=`create_video_post`, params `{video_url, caption, share_to_feed:true, thumb_offset:0}`.
4. `posted.json`에 기록 후 커밋·푸시.

## 실패 시
- 내장 브라우저에 연결이 안 되면(컴퓨터 꺼짐 등) **오래된 가격으로 게시하지 않고** 건너뛴 뒤 이유를 알린다.
- 게시 실패 시 한 번만 재시도, 그래도 실패하면 영상 링크와 캡션을 남기고 알린다.
