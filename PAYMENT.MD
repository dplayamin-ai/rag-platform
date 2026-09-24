# PAYMENT — 에이전트별 토큰 사용량과 수행 시간

생성: 09-24 03:30 KST · 원천: Claude Code 세션 트랜스크립트(`C:\Users\dplaya.min\.claude\projects\C--Workspaces-rag-platform`) · 생성 도구: `tools/usage-report.mjs`

토큰 열의 의미: **입력**(비캐시 입력), **캐시 쓰기**(프롬프트 캐시 생성 입력), **캐시 읽기**(캐시 적중 입력), **출력**(생성 토큰), **합계**(네 값의 합). 비용은 모델·계층별 단가가 다르므로(캐시 읽기·쓰기는 별도 단가) 이 표의 네 열에 현재 단가표를 곱해 산출한다. 시각은 KST, 소요는 에이전트 첫 메시지~마지막 메시지의 실제 경과 시간이다(동시 실행이므로 합계 소요는 실제 경과 시간보다 길다).

## 1. 총계

| 구분 | 에이전트 | API 호출 | 도구 호출 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 세션 2 (2026-09-22: 3단계 준비·실행) — 오케스트레이터(메인 세션) | 1 | 188 | 118 | 4,628 | 3,612,106 | 43,938,084 | 659,443 | 48,214,261 |
| 세션 2 — 3단계 계약(contracts) (88 에이전트, 4h 58m) | 88 | 7,217 | 5,596 | 220,752 | 200,248,915 | 1,344,967,708 | 5,650,464 | 1,551,087,839 |
| 세션 2 — 3단계 아키텍처(architecture) (51 에이전트, 2h 3m) | 51 | 3,209 | 2,430 | 96,658 | 84,563,742 | 455,251,057 | 2,308,196 | 542,219,653 |
| 세션 2 — 3단계 ADR(adrs) (71 에이전트, 2h 17m) | 71 | 3,793 | 2,751 | 112,290 | 129,787,202 | 387,855,981 | 2,361,954 | 520,117,427 |
| 세션 2 — 3단계 파이프라인(pipelines) (138 에이전트, 4h 53m) | 138 | 7,949 | 6,267 | 239,514 | 279,094,467 | 1,184,704,960 | 5,118,162 | 1,469,157,103 |
| 세션 2 — 3단계 API·평가(api-eval) (52 에이전트, 2h 8m) | 52 | 3,426 | 2,691 | 101,936 | 113,587,748 | 529,611,865 | 2,143,870 | 645,445,419 |
| 세션 2 — 3단계 운영·개발·로드맵(ops-dev-roadmap) (48 에이전트, 2h 16m) | 48 | 2,003 | 1,548 | 59,654 | 81,210,983 | 295,848,470 | 983,940 | 378,103,047 |
| 세션 2 — 3단계 계약 감사(contracts-audit) (60 에이전트, 1h 41m) | 60 | 2,570 | 1,668 | 76,648 | 45,292,876 | 298,901,632 | 1,401,621 | 345,672,777 |
| 세션 1 (2026-09-18~22: 브리프, 1·1b·2단계) — 오케스트레이터(메인 세션) | 1 | 609 | 286 | 14,266 | 19,535,109 | 309,502,663 | 2,067,746 | 331,119,784 |
| 세션 1 — 1단계 기술 지형 리서치 (72 에이전트, 89h 14m) | 72 | 8,299 | 7,227 | 257,234 | 127,380,657 | 697,072,186 | 3,609,758 | 828,319,835 |
| 세션 1 — 1b단계 비전·요구사항 (24 에이전트, 1h 28m) | 24 | 1,078 | 677 | 30,994 | 14,751,817 | 124,628,004 | 1,005,681 | 140,416,496 |
| 세션 1 — 2단계 설계 경쟁·바이블 (11 에이전트, 2h 15m) | 11 | 500 | 343 | 14,562 | 21,623,259 | 87,638,358 | 698,183 | 109,974,362 |
| 세션 1 — wf_94f7a864-1a2 (6 에이전트, 7.5m) | 6 | 366 | 290 | 11,052 | 13,378,952 | 44,284,606 | 79,834 | 57,754,444 |
| 세션 1 — wf_7b7b22c8-830 (84 에이전트, 2h 52m) | 84 | 3,185 | 2,270 | 94,278 | 52,219,021 | 309,350,940 | 2,061,455 | 363,725,694 |
| 세션 1 — wf_6cfeebb9-60e (62 에이전트, 1h 3m) | 62 | 1,953 | 1,273 | 55,296 | 26,450,728 | 145,942,398 | 948,468 | 173,396,890 |
| 세션 1 — wf_9464fd89-d43 (36 에이전트, 3h 35m) | 36 | 6,763 | 3,877 | 13,526 | 21,068,609 | 1,438,024,618 | 2,773,748 | 1,461,880,501 |
| 세션 1 — wf_19c804c1-495 (4 에이전트, 26.1m) | 4 | 289 | 179 | 578 | 1,743,560 | 30,198,224 | 150,587 | 32,092,949 |
| 세션 1 — wf_25dbfe1b-97e (3 에이전트, 25.6m) | 3 | 216 | 133 | 432 | 1,307,226 | 22,891,067 | 102,515 | 24,301,240 |
| 세션 1 — wf_8eef8c02-a6c (6 에이전트, 2h 21m) | 6 | 1,593 | 951 | 3,186 | 4,019,339 | 438,662,655 | 696,724 | 443,381,904 |
| 세션 1 — wf_ac8680f5-c18 (2 에이전트, 7.9m) | 2 | 78 | 45 | 156 | 610,274 | 7,402,053 | 58,274 | 8,070,757 |
| 세션 1 — wf_643ae098-82a (5 에이전트, 20.7m) | 5 | 516 | 320 | 1,032 | 1,579,303 | 60,912,452 | 183,880 | 62,676,667 |
| 세션 1 — wf_0755d3ae-470 (8 에이전트, 1h 26m) | 8 | 1,462 | 891 | 2,924 | 3,993,151 | 251,684,168 | 849,127 | 256,529,370 |
| 세션 1 — wf_b7ec72fc-7e3 (7 에이전트, 1h 13m) | 7 | 1,715 | 994 | 3,430 | 5,366,075 | 404,377,784 | 997,509 | 410,744,798 |
| 세션 1 — wf_9a81fe63-40d (4 에이전트, 49.0m) | 4 | 774 | 455 | 1,548 | 2,396,297 | 156,866,763 | 471,044 | 159,735,652 |
| 세션 1 — wf_52b111c5-c82 (4 에이전트, 1h 13m) | 4 | 1,122 | 682 | 2,244 | 3,083,440 | 286,629,510 | 524,584 | 290,239,778 |
| 세션 1 — wf_a6cb70da-507 (7 에이전트, 2h 38m) | 7 | 2,139 | 1,289 | 4,278 | 5,464,666 | 540,622,631 | 1,070,712 | 547,162,287 |
| 세션 1 — wf_6681bb3d-290 (6 에이전트, 2h 13m) | 6 | 1,770 | 1,036 | 3,540 | 3,909,434 | 409,109,024 | 738,111 | 413,760,109 |
| **전체** | **861** | **64,782** | **46,287** | **1,426,636** | **1,267,278,956** | **10,306,879,861** | **39,715,590** | **11,615,301,043** |

## 2. 워크플로우·단계별 요약

| 세션 | 워크플로우(Run ID) | 단계(phase) | 에이전트 | 완료/실패/진행 | 소요(실제 경과(첫~끝)) | 에이전트 활동 시간 합산 | 출력 토큰 | 합계 토큰 |
|---|---|---|---:|---|---|---:|---:|---:|
| 세션 2 | 3단계 계약(contracts) (`wf_aae863e5-fec`) | Contracts T0 | 15 | 15/0/0 | 09-22 13:37 → 09-22 15:00 (1h 23m) | 4h 29m | 908,771 | 246,851,329 |
| 세션 2 | 3단계 계약(contracts) (`wf_aae863e5-fec`) | Contracts T1 | 73 | 73/0/0 | 09-22 15:00 → 09-22 18:35 (3h 35m) | 20h 40m | 4,741,693 | 1,304,236,510 |
| 세션 2 | 3단계 아키텍처(architecture) (`wf_6d211baa-983`) | Architecture | 51 | 51/0/0 | 09-22 13:37 → 09-22 15:40 (2h 3m) | 11h 34m | 2,308,196 | 542,219,653 |
| 세션 2 | 3단계 ADR(adrs) (`wf_f8852269-0c1`) | ADRs | 71 | 65/0/6 | 09-22 13:37 → 09-22 15:54 (2h 17m) | 11h 42m | 2,361,954 | 520,117,427 |
| 세션 2 | 3단계 파이프라인(pipelines) (`wf_02322627-3eb`) | Pipelines | 138 | 102/35/1 | 09-22 15:43 → 09-22 20:37 (4h 53m) | 23h 33m | 5,118,162 | 1,469,157,103 |
| 세션 2 | 3단계 API·평가(api-eval) (`wf_7bfc9aa6-c62`) | API & Evaluation | 52 | 43/9/0 | 09-22 18:27 → 09-22 20:35 (2h 8m) | 10h 18m | 2,143,870 | 645,445,419 |
| 세션 2 | 3단계 운영·개발·로드맵(ops-dev-roadmap) (`wf_18a2a477-09d`) | Ops, Dev, Roadmap | 48 | 20/28/0 | 09-22 18:27 → 09-22 20:43 (2h 16m) | 8h 16m | 983,940 | 378,103,047 |
| 세션 2 | 3단계 계약 감사(contracts-audit) (`wf_8890c66f-daf`) | Contract Audit | 60 | 53/6/1 | 09-22 18:35 → 09-22 20:16 (1h 41m) | 6h 25m | 1,401,621 | 345,672,777 |
| 세션 1 | 1단계 기술 지형 리서치 (`wf_270deb6d-bba`) | Research | 14 | 14/0/0 | 09-18 17:31 → 09-18 18:35 (1h 5m) | 5h 25m | 972,779 | 208,323,746 |
| 세션 1 | 1단계 기술 지형 리서치 (`wf_270deb6d-bba`) | Verify | 29 | 25/2/2 | 09-18 18:15 → 09-22 09:47 (87h 32m) | 7h 27m | 1,572,759 | 402,587,366 |
| 세션 1 | 1단계 기술 지형 리서치 (`wf_270deb6d-bba`) | Fix | 27 | 17/9/1 | 09-18 18:44 → 09-22 10:22 (87h 38m) | 5h 49m | 1,021,248 | 205,426,756 |
| 세션 1 | 1단계 기술 지형 리서치 (`wf_270deb6d-bba`) | Synthesize | 2 | 1/1/0 | 09-18 19:40 → 09-22 10:45 (87h 5m) | 25.7m | 42,972 | 11,981,967 |
| 세션 1 | 1b단계 비전·요구사항 (`wf_3115816b-af8`) | Write | 8 | 8/0/0 | 09-18 17:32 → 09-18 18:29 (57.1m) | 2h 51m | 331,856 | 25,523,944 |
| 세션 1 | 1b단계 비전·요구사항 (`wf_3115816b-af8`) | Review | 8 | 8/0/0 | 09-18 17:46 → 09-18 18:39 (52.8m) | 1h 5m | 268,858 | 14,674,602 |
| 세션 1 | 1b단계 비전·요구사항 (`wf_3115816b-af8`) | Fix | 8 | 8/0/0 | 09-18 17:57 → 09-18 19:00 (1h 4m) | 2h 37m | 404,967 | 100,217,950 |
| 세션 1 | 2단계 설계 경쟁·바이블 (`wf_97157829-22c`) | Propose | 3 | 3/0/0 | 09-22 10:45 → 09-22 11:16 (30.2m) | 1h 12m | 234,911 | 26,406,118 |
| 세션 1 | 2단계 설계 경쟁·바이블 (`wf_97157829-22c`) | Judge | 3 | 3/0/0 | 09-22 11:16 → 09-22 11:24 (8.2m) | 21.2m | 89,233 | 12,770,239 |
| 세션 1 | 2단계 설계 경쟁·바이블 (`wf_97157829-22c`) | Synthesize | 1 | 1/0/0 | 09-22 11:24 → 09-22 12:07 (43.4m) | 43.4m | 90,611 | 34,355,173 |
| 세션 1 | 2단계 설계 경쟁·바이블 (`wf_97157829-22c`) | Review | 4 | 4/0/0 | 09-22 12:07 → 09-22 13:01 (53.3m) | 1h 7m | 283,428 | 36,442,832 |
| 세션 1 | wf_94f7a864-1a2 (`wf_94f7a864-1a2`) | ADRs | 1 | 0/0/1 | 09-23 09:22 → 09-23 09:30 (7.5m) | 7.5m | 4,566 | 2,772,828 |
| 세션 1 | wf_94f7a864-1a2 (`wf_94f7a864-1a2`) | Finish: write missing | 5 | 0/0/5 | 09-23 09:22 → 09-23 09:30 (7.5m) | 37.3m | 75,268 | 54,981,616 |
| 세션 1 | wf_7b7b22c8-830 (`wf_7b7b22c8-830`) | Finish: write missing | 18 | 18/0/0 | 09-23 09:37 → 09-23 11:03 (1h 25m) | 3h 33m | 795,409 | 147,396,158 |
| 세션 1 | wf_7b7b22c8-830 (`wf_7b7b22c8-830`) | Finish: review cycle | 62 | 62/0/0 | 09-23 09:54 → 09-23 10:58 (1h 3m) | 4h 40m | 974,324 | 175,865,179 |
| 세션 1 | wf_7b7b22c8-830 (`wf_7b7b22c8-830`) | OpenAPI | 3 | 3/0/0 | 09-23 11:03 → 09-23 12:07 (1h 4m) | 1h 4m | 222,299 | 31,601,776 |
| 세션 1 | wf_7b7b22c8-830 (`wf_7b7b22c8-830`) | Completeness Critic | 1 | 1/0/0 | 09-23 12:07 → 09-23 12:30 (22.4m) | 22.4m | 69,423 | 8,862,581 |
| 세션 1 | wf_6cfeebb9-60e (`wf_6cfeebb9-60e`) | ADR fast cycle | 61 | 61/0/0 | 09-23 09:52 → 09-23 10:37 (45.5m) | 4h 15m | 897,880 | 168,144,512 |
| 세션 1 | wf_6cfeebb9-60e (`wf_6cfeebb9-60e`) | ADR index | 1 | 1/0/0 | 09-23 10:37 → 09-23 10:55 (17.5m) | 17.5m | 50,588 | 5,252,378 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | T1 Triage | 1 | 1/0/0 | 09-23 12:44 → 09-23 13:01 (16.5m) | 16.5m | 98,535 | 12,316,283 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | T2 Bible Revision | 1 | 1/0/0 | 09-23 13:01 → 09-23 13:29 (27.6m) | 27.6m | 134,198 | 51,849,237 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | T3 Schema Sync | 1 | 1/0/0 | 09-23 13:29 → 09-23 13:58 (29.4m) | 29.4m | 113,241 | 57,677,701 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | P1 Propagate | 22 | 22/0/0 | 09-23 13:58 → 09-23 15:22 (1h 24m) | 7h 38m | 1,907,800 | 1,081,215,972 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | P2 Trim | 3 | 3/0/0 | 09-23 15:22 → 09-23 15:59 (37.1m) | 1h 32m | 388,617 | 209,125,365 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | P3 Sample Verify | 7 | 7/0/0 | 09-23 15:59 → 09-23 16:04 (4.6m) | 20.5m | 68,456 | 33,196,961 |
| 세션 1 | wf_9464fd89-d43 (`wf_9464fd89-d43`) | P4 Residual | 1 | 1/0/0 | 09-23 16:04 → 09-23 16:20 (16.0m) | 16.0m | 62,901 | 16,498,982 |
| 세션 1 | wf_19c804c1-495 (`wf_19c804c1-495`) | Write | 2 | 2/0/0 | 09-23 14:03 → 09-23 14:14 (10.5m) | 19.8m | 95,598 | 19,029,103 |
| 세션 1 | wf_19c804c1-495 (`wf_19c804c1-495`) | Review | 2 | 2/0/0 | 09-23 14:14 → 09-23 14:30 (15.6m) | 15.6m | 54,989 | 13,063,846 |
| 세션 1 | wf_25dbfe1b-97e (`wf_25dbfe1b-97e`) | S1 Foundation | 1 | 1/0/0 | 09-23 14:05 → 09-23 14:20 (15.2m) | 15.2m | 34,499 | 9,531,706 |
| 세션 1 | wf_25dbfe1b-97e (`wf_25dbfe1b-97e`) | S2 Contracts | 1 | 0/0/1 | 09-23 14:20 → 09-23 14:31 (10.4m) | 10.4m | 27,150 | 7,170,397 |
| 세션 1 | wf_25dbfe1b-97e (`wf_25dbfe1b-97e`) | S3 Core | 1 | 0/0/1 | 09-23 14:20 → 09-23 14:31 (10.3m) | 10.3m | 40,866 | 7,599,137 |
| 세션 1 | wf_8eef8c02-a6c (`wf_8eef8c02-a6c`) | S1 Foundation | 1 | 1/0/0 | 09-23 14:32 → 09-23 14:44 (12.6m) | 12.6m | 48,187 | 10,190,942 |
| 세션 1 | wf_8eef8c02-a6c (`wf_8eef8c02-a6c`) | S2 Contracts | 1 | 1/0/0 | 09-23 14:44 → 09-23 15:55 (1h 10m) | 1h 10m | 211,020 | 149,389,804 |
| 세션 1 | wf_8eef8c02-a6c (`wf_8eef8c02-a6c`) | S3 Core | 1 | 1/0/0 | 09-23 14:44 → 09-23 15:50 (1h 6m) | 1h 6m | 260,184 | 213,845,887 |
| 세션 1 | wf_8eef8c02-a6c (`wf_8eef8c02-a6c`) | S4 Handoff | 1 | 1/0/0 | 09-23 15:55 → 09-23 16:22 (27.7m) | 27.7m | 76,742 | 29,992,143 |
| 세션 1 | wf_8eef8c02-a6c (`wf_8eef8c02-a6c`) | S5 Review | 2 | 2/0/0 | 09-23 16:22 → 09-23 16:52 (30.1m) | 30.0m | 100,591 | 39,963,128 |
| 세션 1 | wf_ac8680f5-c18 (`wf_ac8680f5-c18`) | Edit | 2 | 2/0/0 | 09-23 16:23 → 09-23 16:31 (7.9m) | 11.5m | 58,274 | 8,070,757 |
| 세션 1 | wf_643ae098-82a (`wf_643ae098-82a`) | Header pass | 4 | 4/0/0 | 09-23 16:55 → 09-23 17:13 (18.6m) | 46.0m | 178,698 | 61,455,632 |
| 세션 1 | wf_643ae098-82a (`wf_643ae098-82a`) | Verify | 1 | 1/0/0 | 09-23 17:13 → 09-23 17:15 (2.1m) | 2.1m | 5,182 | 1,221,035 |
| 세션 1 | wf_0755d3ae-470 (`wf_0755d3ae-470`) | S0 Deps | 1 | 1/0/0 | 09-23 17:16 → 09-23 17:26 (9.9m) | 9.9m | 18,459 | 4,294,444 |
| 세션 1 | wf_0755d3ae-470 (`wf_0755d3ae-470`) | 6B Conformance | 3 | 3/0/0 | 09-23 17:26 → 09-23 18:07 (41.5m) | 1h 21m | 337,546 | 108,908,948 |
| 세션 1 | wf_0755d3ae-470 (`wf_0755d3ae-470`) | 6D Spikes | 3 | 3/0/0 | 09-23 17:26 → 09-23 18:10 (44.3m) | 1h 40m | 405,774 | 113,932,912 |
| 세션 1 | wf_0755d3ae-470 (`wf_0755d3ae-470`) | Verify | 1 | 1/0/0 | 09-23 18:10 → 09-23 18:41 (31.4m) | 31.4m | 87,348 | 29,393,066 |
| 세션 1 | wf_b7ec72fc-7e3 (`wf_b7ec72fc-7e3`) | Implement | 6 | 6/0/0 | 09-23 18:48 → 09-23 19:39 (50.5m) | 3h 42m | 945,560 | 381,782,347 |
| 세션 1 | wf_b7ec72fc-7e3 (`wf_b7ec72fc-7e3`) | Verify | 1 | 1/0/0 | 09-23 19:39 → 09-23 20:02 (22.9m) | 22.9m | 51,949 | 28,962,451 |
| 세션 1 | wf_9a81fe63-40d (`wf_9a81fe63-40d`) | Implement | 3 | 3/0/0 | 09-23 20:03 → 09-23 20:40 (36.9m) | 1h 33m | 433,573 | 148,888,776 |
| 세션 1 | wf_9a81fe63-40d (`wf_9a81fe63-40d`) | Verify | 1 | 1/0/0 | 09-23 20:40 → 09-23 20:52 (12.1m) | 12.1m | 37,471 | 10,846,876 |
| 세션 1 | wf_52b111c5-c82 (`wf_52b111c5-c82`) | Implement | 3 | 3/0/0 | 09-23 20:52 → 09-23 21:39 (47.2m) | 1h 59m | 470,560 | 263,052,448 |
| 세션 1 | wf_52b111c5-c82 (`wf_52b111c5-c82`) | Verify | 1 | 1/0/0 | 09-23 21:39 → 09-23 22:05 (25.4m) | 25.4m | 54,024 | 27,187,330 |
| 세션 1 | wf_a6cb70da-507 (`wf_a6cb70da-507`) | Implement | 4 | 4/0/0 | 09-23 22:07 → 09-23 22:55 (48.8m) | 2h 57m | 741,490 | 330,273,700 |
| 세션 1 | wf_a6cb70da-507 (`wf_a6cb70da-507`) | Verify | 1 | 1/0/0 | 09-23 22:55 → 09-24 00:06 (1h 11m) | 1h 11m | 204,233 | 153,643,819 |
| 세션 1 | wf_a6cb70da-507 (`wf_a6cb70da-507`) | Review | 2 | 2/0/0 | 09-24 00:06 → 09-24 00:45 (38.9m) | 38.8m | 124,989 | 63,244,768 |
| 세션 1 | wf_6681bb3d-290 (`wf_6681bb3d-290`) | Implement | 3 | 3/0/0 | 09-24 00:48 → 09-24 01:44 (55.9m) | 2h 7m | 494,778 | 253,556,149 |
| 세션 1 | wf_6681bb3d-290 (`wf_6681bb3d-290`) | Verify | 1 | 1/0/0 | 09-24 01:44 → 09-24 02:37 (52.4m) | 52.4m | 148,810 | 126,034,422 |
| 세션 1 | wf_6681bb3d-290 (`wf_6681bb3d-290`) | Review | 2 | 2/0/0 | 09-24 02:37 → 09-24 03:02 (24.8m) | 24.8m | 94,523 | 34,169,538 |

## 3. 에이전트별 상세

상태: done = 결과 반환, failed = API 오류로 중단(프록시 차단 등), running = 보고 시점에 진행 중(부분 집계), empty = null 결과.

### 세션 2 (2026-09-22: 3단계 준비·실행)

오케스트레이터(메인 세션): 09-22 13:09 → 09-23 09:11 (20h 2m), API 호출 188, 도구 호출 118, 모델 opus-5, fable-5-1, <synthetic>, 입력 4,628 / 캐시 쓰기 3,612,106 / 캐시 읽기 43,938,084 / 출력 659,443 / 합계 48,214,261

#### 3단계 계약(contracts) — `wf_aae863e5-fec` · 88 에이전트 · 실제 경과 시간 09-22 13:37 → 09-22 18:35 (4h 58m) · 에이전트 활동 시간 합산 25h 9m · 합계 1,551,087,839 토큰(출력 5,650,464)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:03-contracts/00-contract-overview.md | Contracts T0 | done | fable-5-1 | 09-22 13:37 | 37.7m | 120 | 91 | 3,720 | 2,619,067 | 31,568,809 | 81,875 | 34,273,471 |
| 2 | write:03-contracts/13-error-model.md | Contracts T0 | done | fable-5-1 | 09-22 13:37 | 31.7m | 90 | 64 | 2,760 | 2,404,178 | 16,336,908 | 62,047 | 18,805,893 |
| 3 | write:03-contracts/14-schema-versioning-and-compatibility… | Contracts T0 | done | fable-5-1 | 09-22 13:37 | 30.6m | 96 | 73 | 2,982 | 4,076,009 | 18,590,171 | 113,723 | 22,782,885 |
| 4 | review-tech:03-contracts/14-schema-versioning-and-compati… | Contracts T0 | done | fable-5-1 | 09-22 14:07 | 18.0m | 58 | 42 | 1,736 | 1,747,707 | 5,979,748 | 50,405 | 7,779,596 |
| 5 | review-anchor:03-contracts/14-schema-versioning-and-compa… | Contracts T0 | done | fable-5-1 | 09-22 14:07 | 10.9m | 65 | 49 | 1,960 | 2,440,855 | 7,523,813 | 50,230 | 10,016,858 |
| 6 | review-anchor:03-contracts/13-error-model.md | Contracts T0 | done | fable-5-1 | 09-22 14:09 | 8.9m | 50 | 42 | 1,450 | 1,442,717 | 5,647,405 | 24,517 | 7,116,089 |
| 7 | review-tech:03-contracts/13-error-model.md | Contracts T0 | done | fable-5-1 | 09-22 14:09 | 11.9m | 66 | 51 | 1,992 | 1,623,878 | 7,658,027 | 42,477 | 9,326,374 |
| 8 | review-anchor:03-contracts/00-contract-overview.md | Contracts T0 | done | fable-5-1 | 09-22 14:15 | 11.5m | 38 | 28 | 1,066 | 1,304,491 | 4,135,867 | 54,532 | 5,495,956 |
| 9 | review-tech:03-contracts/00-contract-overview.md | Contracts T0 | done | fable-5-1 | 09-22 14:15 | 10.1m | 45 | 36 | 1,320 | 1,267,017 | 5,082,449 | 43,638 | 6,394,424 |
| 10 | fix:03-contracts/13-error-model.md | Contracts T0 | done | fable-5-1 | 09-22 14:20 | 29.0m | 178 | 136 | 5,576 | 2,281,686 | 44,002,675 | 129,542 | 46,419,479 |
| 11 | fix:03-contracts/14-schema-versioning-and-compatibility.md | Contracts T0 | done | fable-5-1 | 09-22 14:25 | 25.6m | 155 | 121 | 4,870 | 3,605,939 | 30,881,843 | 109,570 | 34,602,222 |
| 12 | fix:03-contracts/00-contract-overview.md | Contracts T0 | done | fable-5-1 | 09-22 14:26 | 16.1m | 124 | 93 | 3,788 | 1,599,614 | 21,380,912 | 46,342 | 23,030,656 |
| 13 | verify:03-contracts/00-contract-overview.md | Contracts T0 | done | fable-5-1 | 09-22 14:42 | 10.2m | 59 | 43 | 1,798 | 1,183,765 | 6,776,329 | 32,471 | 7,994,363 |
| 14 | verify:03-contracts/13-error-model.md | Contracts T0 | done | fable-5-1 | 09-22 14:50 | 8.7m | 52 | 36 | 1,574 | 967,503 | 5,590,194 | 36,590 | 6,595,861 |
| 15 | verify:03-contracts/14-schema-versioning-and-compatibilit… | Contracts T0 | done | fable-5-1 | 09-22 14:51 | 8.6m | 50 | 39 | 1,510 | 1,121,260 | 5,063,620 | 30,812 | 6,217,202 |
| 16 | write:03-contracts/01-ingest-request.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 32.0m | 81 | 49 | 2,502 | 4,133,952 | 15,111,710 | 115,390 | 19,363,554 |
| 17 | write:03-contracts/02-source-document.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 43.4m | 103 | 69 | 3,206 | 5,774,048 | 22,966,871 | 77,551 | 28,821,676 |
| 18 | write:03-contracts/03-parsed-document.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 32.8m | 135 | 103 | 4,200 | 3,006,001 | 36,258,840 | 107,300 | 39,376,341 |
| 19 | write:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 34.1m | 106 | 75 | 3,332 | 3,053,388 | 24,506,327 | 123,361 | 27,686,408 |
| 20 | write:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 55.9m | 123 | 85 | 3,816 | 7,017,249 | 32,772,172 | 291,917 | 40,085,154 |
| 21 | write:03-contracts/05-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 15:00 | 32.0m | 94 | 72 | 2,948 | 3,725,286 | 20,276,545 | 84,625 | 24,089,404 |
| 22 | write:03-contracts/07-embedded-chunk-set-and-index-record… | Contracts T1 | done | fable-5-1 | 09-22 15:32 | 53.6m | 174 | 134 | 5,448 | 6,207,016 | 63,540,368 | 189,370 | 69,942,202 |
| 23 | write:03-contracts/08-index-commit.md | Contracts T1 | done | fable-5-1 | 09-22 15:32 | 32.6m | 96 | 73 | 2,952 | 4,983,321 | 21,907,242 | 129,301 | 27,022,816 |
| 24 | write:03-contracts/09-query-request-and-query-plan.md | Contracts T1 | done | fable-5-1 | 09-22 15:33 | 54.1m | 158 | 126 | 4,880 | 3,428,542 | 50,817,485 | 227,041 | 54,477,948 |
| 25 | write:03-contracts/10-candidate-set-and-ranked-set.md | Contracts T1 | done | fable-5-1 | 09-22 15:34 | 33.9m | 101 | 71 | 3,112 | 4,037,812 | 21,949,061 | 159,523 | 26,149,508 |
| 26 | write:03-contracts/11-context-pack.md | Contracts T1 | done | fable-5-1 | 09-22 15:43 | 47.3m | 102 | 71 | 3,116 | 5,027,396 | 26,689,705 | 101,772 | 31,821,989 |
| 27 | write:03-contracts/12-jobs-events-and-status.md | Contracts T1 | done | fable-5-1 | 09-22 15:56 | 40.8m | 135 | 102 | 4,140 | 3,703,722 | 34,857,031 | 129,251 | 38,694,144 |
| 28 | write:03-contracts/15-collection-profile-and-policy-contr… | Contracts T1 | done | fable-5-1 | 09-22 16:04 | 33.0m | 137 | 96 | 4,294 | 3,446,483 | 39,087,444 | 135,682 | 42,673,903 |
| 29 | write:03-contracts/16-eval-feedback-and-sidecar-contracts… | Contracts T1 | done | fable-5-1 | 09-22 16:08 | 46.5m | 127 | 102 | 3,916 | 5,322,782 | 32,737,027 | 150,561 | 38,214,286 |
| 30 | review-anchor:03-contracts/01-ingest-request.md | Contracts T1 | done | fable-5-1 | 09-22 16:25 | 7.5m | 51 | 43 | 1,482 | 1,728,315 | 6,790,967 | 34,261 | 8,555,025 |
| 31 | review-tech:03-contracts/01-ingest-request.md | Contracts T1 | done | fable-5-1 | 09-22 16:27 | 8.3m | 47 | 38 | 1,384 | 1,107,559 | 5,522,319 | 35,618 | 6,666,880 |
| 32 | review-anchor:03-contracts/05-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 16:30 | 9.8m | 70 | 58 | 2,090 | 2,922,530 | 8,960,564 | 45,147 | 11,930,331 |
| 33 | review-tech:03-contracts/05-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 16:33 | 14.4m | 64 | 52 | 1,958 | 2,246,041 | 8,462,779 | 55,488 | 10,766,266 |
| 34 | review-anchor:03-contracts/03-parsed-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:35 | 9.9m | 71 | 57 | 2,152 | 3,274,299 | 9,955,268 | 47,127 | 13,278,846 |
| 35 | review-tech:03-contracts/03-parsed-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:37 | 10.3m | 47 | 39 | 1,384 | 1,538,100 | 5,306,308 | 47,986 | 6,893,778 |
| 36 | review-anchor:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 16:37 | 8.7m | 50 | 42 | 1,480 | 1,990,559 | 6,223,431 | 34,299 | 8,249,769 |
| 37 | review-tech:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 16:40 | 17.0m | 52 | 36 | 1,514 | 1,558,743 | 6,706,290 | 65,877 | 8,332,424 |
| 38 | review-anchor:03-contracts/02-source-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:45 | 11.3m | 61 | 52 | 1,862 | 1,787,699 | 8,291,316 | 51,586 | 10,132,463 |
| 39 | review-tech:03-contracts/02-source-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:46 | 8.7m | 42 | 35 | 1,194 | 1,174,582 | 3,896,329 | 39,236 | 5,111,341 |
| 40 | review-anchor:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:47 | 10.5m | 81 | 69 | 2,472 | 3,695,318 | 10,545,097 | 50,408 | 14,293,295 |
| 41 | review-tech:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 16:47 | 11.9m | 48 | 36 | 1,416 | 1,348,170 | 4,922,716 | 53,743 | 6,326,045 |
| 42 | review-anchor:03-contracts/08-index-commit.md | Contracts T1 | done | fable-5-1 | 09-22 16:54 | 10.1m | 51 | 40 | 1,542 | 2,541,511 | 5,524,374 | 47,342 | 8,114,769 |
| 43 | review-tech:03-contracts/08-index-commit.md | Contracts T1 | done | fable-5-1 | 09-22 16:55 | 13.8m | 77 | 65 | 2,344 | 2,322,873 | 12,331,218 | 55,952 | 14,712,387 |
| 44 | review-anchor:03-contracts/10-candidate-set-and-ranked-se… | Contracts T1 | done | fable-5-1 | 09-22 16:56 | 9.4m | 69 | 51 | 2,088 | 2,797,401 | 9,352,145 | 44,535 | 12,196,169 |
| 45 | review-tech:03-contracts/10-candidate-set-and-ranked-set.… | Contracts T1 | done | fable-5-1 | 09-22 16:57 | 13.2m | 61 | 45 | 1,862 | 2,389,466 | 7,690,542 | 59,972 | 10,141,842 |
| 46 | review-anchor:03-contracts/07-embedded-chunk-set-and-inde… | Contracts T1 | done | fable-5-1 | 09-22 16:57 | 10.1m | 59 | 47 | 1,768 | 2,159,611 | 7,827,777 | 39,337 | 10,028,493 |
| 47 | review-tech:03-contracts/07-embedded-chunk-set-and-index-… | Contracts T1 | done | fable-5-1 | 09-22 16:59 | 13.4m | 63 | 48 | 1,926 | 1,033,090 | 10,535,080 | 46,396 | 11,616,492 |
| 48 | review-anchor:03-contracts/09-query-request-and-query-pla… | Contracts T1 | done | fable-5-1 | 09-22 17:04 | 9.7m | 54 | 45 | 1,578 | 3,313,276 | 5,331,196 | 42,574 | 8,688,624 |
| 49 | review-tech:03-contracts/09-query-request-and-query-plan.… | Contracts T1 | done | fable-5-1 | 09-22 17:06 | 15.4m | 86 | 74 | 2,572 | 2,280,454 | 13,242,764 | 38,084 | 15,563,874 |
| 50 | review-anchor:03-contracts/11-context-pack.md | Contracts T1 | done | fable-5-1 | 09-22 17:07 | 11.6m | 68 | 53 | 2,086 | 2,735,274 | 9,875,318 | 37,016 | 12,649,694 |
| 51 | review-tech:03-contracts/11-context-pack.md | Contracts T1 | done | fable-5-1 | 09-22 17:09 | 11.0m | 60 | 48 | 1,830 | 1,160,084 | 8,280,369 | 47,729 | 9,490,012 |
| 52 | fix:03-contracts/01-ingest-request.md | Contracts T1 | done | fable-5-1 | 09-22 17:11 | 18.0m | 129 | 103 | 4,008 | 2,149,075 | 24,322,563 | 58,317 | 26,533,963 |
| 53 | review-anchor:03-contracts/12-jobs-events-and-status.md | Contracts T1 | done | fable-5-1 | 09-22 17:13 | 10.5m | 54 | 45 | 1,578 | 2,564,131 | 7,247,767 | 48,634 | 9,862,110 |
| 54 | review-tech:03-contracts/12-jobs-events-and-status.md | Contracts T1 | done | fable-5-1 | 09-22 17:14 | 10.1m | 70 | 61 | 2,090 | 2,699,179 | 11,067,754 | 25,843 | 13,794,866 |
| 55 | review-anchor:03-contracts/15-collection-profile-and-poli… | Contracts T1 | done | fable-5-1 | 09-22 17:19 | 10.0m | 62 | 51 | 1,864 | 1,848,103 | 9,933,933 | 46,431 | 11,830,331 |
| 56 | review-tech:03-contracts/15-collection-profile-and-policy… | Contracts T1 | done | fable-5-1 | 09-22 17:20 | 10.9m | 64 | 53 | 1,928 | 2,171,209 | 9,544,449 | 49,964 | 11,767,550 |
| 57 | fix:03-contracts/03-parsed-document.md | Contracts T1 | done | fable-5-1 | 09-22 17:21 | 10.2m | 88 | 70 | 2,666 | 1,465,174 | 12,881,046 | 44,138 | 14,393,024 |
| 58 | fix:03-contracts/05-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 17:23 | 17.1m | 116 | 90 | 3,592 | 1,562,323 | 23,100,767 | 57,167 | 24,723,849 |
| 59 | review-anchor:03-contracts/16-eval-feedback-and-sidecar-c… | Contracts T1 | done | fable-5-1 | 09-22 17:24 | 12.3m | 80 | 63 | 2,440 | 3,391,960 | 13,337,528 | 56,277 | 16,788,205 |
| 60 | review-tech:03-contracts/16-eval-feedback-and-sidecar-con… | Contracts T1 | done | fable-5-1 | 09-22 17:29 | 15.2m | 59 | 43 | 1,768 | 1,912,301 | 8,424,481 | 55,314 | 10,393,864 |
| 61 | fix:03-contracts/02-source-document.md | Contracts T1 | done | fable-5-1 | 09-22 17:29 | 11.9m | 109 | 91 | 3,368 | 1,511,043 | 17,782,012 | 41,121 | 19,337,544 |
| 62 | fix:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 17:31 | 19.7m | 147 | 113 | 4,584 | 1,935,279 | 32,171,500 | 85,127 | 34,196,490 |
| 63 | fix:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 17:31 | 24.7m | 152 | 116 | 4,774 | 1,958,345 | 35,378,853 | 88,824 | 37,430,796 |
| 64 | fix:03-contracts/08-index-commit.md | Contracts T1 | done | fable-5-1 | 09-22 17:37 | 18.2m | 156 | 130 | 4,902 | 2,806,442 | 38,731,951 | 76,835 | 41,620,130 |
| 65 | fix:03-contracts/10-candidate-set-and-ranked-set.md | Contracts T1 | done | fable-5-1 | 09-22 17:40 | 15.6m | 145 | 122 | 4,550 | 3,192,898 | 36,180,784 | 60,099 | 39,438,331 |
| 66 | fix:03-contracts/07-embedded-chunk-set-and-index-record.md | Contracts T1 | done | fable-5-1 | 09-22 17:41 | 8.5m | 80 | 66 | 2,440 | 1,725,758 | 12,778,842 | 31,847 | 14,538,887 |
| 67 | fix:03-contracts/11-context-pack.md | Contracts T1 | done | fable-5-1 | 09-22 17:44 | 19.1m | 141 | 114 | 4,422 | 3,010,451 | 33,654,421 | 70,171 | 36,739,465 |
| 68 | fix:03-contracts/09-query-request-and-query-plan.md | Contracts T1 | done | fable-5-1 | 09-22 17:50 | 18.2m | 123 | 106 | 3,816 | 2,178,116 | 25,012,882 | 92,574 | 27,287,388 |
| 69 | fix:03-contracts/12-jobs-events-and-status.md | Contracts T1 | done | fable-5-1 | 09-22 17:50 | 16.1m | 108 | 85 | 3,336 | 2,147,397 | 22,842,591 | 74,331 | 25,067,655 |
| 70 | verify:03-contracts/01-ingest-request.md | Contracts T1 | done | fable-5-1 | 09-22 17:55 | 5.0m | 40 | 32 | 1,190 | 843,596 | 3,434,578 | 22,378 | 4,301,742 |
| 71 | fix:03-contracts/15-collection-profile-and-policy-contrac… | Contracts T1 | done | fable-5-1 | 09-22 17:56 | 21.9m | 121 | 100 | 3,782 | 2,166,580 | 27,051,777 | 99,879 | 29,322,018 |
| 72 | verify:03-contracts/03-parsed-document.md | Contracts T1 | done | fable-5-1 | 09-22 17:56 | 7.7m | 56 | 45 | 1,702 | 851,460 | 5,425,571 | 26,518 | 6,305,251 |
| 73 | verify:03-contracts/05-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 18:00 | 6.9m | 42 | 30 | 1,254 | 992,481 | 4,196,920 | 29,177 | 5,219,832 |
| 74 | verify:03-contracts/02-source-document.md | Contracts T1 | done | fable-5-1 | 09-22 18:03 | 4.4m | 34 | 26 | 968 | 619,184 | 2,503,595 | 16,603 | 3,140,350 |
| 75 | fix:03-contracts/16-eval-feedback-and-sidecar-contracts.md | Contracts T1 | done | fable-5-1 | 09-22 18:04 | 12.8m | 120 | 102 | 3,720 | 2,135,331 | 21,997,389 | 59,186 | 24,195,626 |
| 76 | verify:03-contracts/07-embedded-chunk-set-and-index-recor… | Contracts T1 | done | fable-5-1 | 09-22 18:07 | 2.4m | 32 | 22 | 904 | 673,878 | 2,124,240 | 8,147 | 2,807,169 |
| 77 | verify:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 18:07 | 6.7m | 48 | 37 | 1,386 | 850,474 | 4,309,431 | 23,081 | 5,184,372 |
| 78 | verify:03-contracts/08-index-commit.md | Contracts T1 | done | fable-5-1 | 09-22 18:07 | 5.4m | 50 | 40 | 1,510 | 1,010,095 | 5,173,180 | 22,599 | 6,207,384 |
| 79 | verify:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 18:08 | 14.4m | 60 | 45 | 1,770 | 795,846 | 7,128,505 | 51,494 | 7,977,615 |
| 80 | verify:03-contracts/10-candidate-set-and-ranked-set.md | Contracts T1 | done | fable-5-1 | 09-22 18:09 | 7.9m | 52 | 38 | 1,574 | 1,298,307 | 4,897,910 | 34,720 | 6,232,511 |
| 81 | verify:03-contracts/11-context-pack.md | Contracts T1 | done | fable-5-1 | 09-22 18:13 | 5.3m | 49 | 39 | 1,478 | 1,133,811 | 4,564,127 | 23,103 | 5,722,519 |
| 82 | verify:03-contracts/12-jobs-events-and-status.md | Contracts T1 | done | fable-5-1 | 09-22 18:14 | 6.8m | 46 | 36 | 1,382 | 1,124,383 | 4,801,155 | 29,638 | 5,956,558 |
| 83 | verify:03-contracts/09-query-request-and-query-plan.md | Contracts T1 | done | fable-5-1 | 09-22 18:17 | 6.3m | 47 | 38 | 1,414 | 978,669 | 3,988,889 | 27,012 | 4,995,984 |
| 84 | fix2:03-contracts/06-enriched-chunk-set.md | Contracts T1 | done | fable-5-1 | 09-22 18:17 | 7.9m | 76 | 52 | 2,312 | 898,330 | 10,687,245 | 25,663 | 11,613,550 |
| 85 | verify:03-contracts/16-eval-feedback-and-sidecar-contract… | Contracts T1 | done | fable-5-1 | 09-22 18:18 | 6.3m | 39 | 27 | 1,158 | 942,681 | 3,123,178 | 13,983 | 4,081,000 |
| 86 | verify:03-contracts/15-collection-profile-and-policy-cont… | Contracts T1 | done | fable-5-1 | 09-22 18:18 | 8.4m | 60 | 42 | 1,800 | 1,692,216 | 6,780,125 | 39,223 | 8,513,364 |
| 87 | fix2:03-contracts/04-normalized-document.md | Contracts T1 | done | fable-5-1 | 09-22 18:22 | 12.6m | 66 | 44 | 1,992 | 886,687 | 8,596,114 | 54,718 | 9,539,511 |
| 88 | fix2:03-contracts/09-query-request-and-query-plan.md | Contracts T1 | done | fable-5-1 | 09-22 18:23 | 6.7m | 46 | 34 | 1,382 | 468,083 | 4,518,890 | 29,199 | 5,017,554 |
| | **소계** | | | | | **25h 9m** | **7,217** | **5,596** | **220,752** | **200,248,915** | **1,344,967,708** | **5,650,464** | **1,551,087,839** |

#### 3단계 아키텍처(architecture) — `wf_6d211baa-983` · 51 에이전트 · 실제 경과 시간 09-22 13:37 → 09-22 15:40 (2h 3m) · 에이전트 활동 시간 합산 11h 34m · 합계 542,219,653 토큰(출력 2,308,196)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:02-architecture/02-component-architecture.md | Architecture | done | fable-5-1 | 09-22 13:37 | 21.9m | 74 | 52 | 2,278 | 2,403,711 | 12,927,852 | 104,364 | 15,438,205 |
| 2 | write:02-architecture/01-system-overview.md | Architecture | done | fable-5-1 | 09-22 13:37 | 15.6m | 49 | 36 | 1,448 | 1,898,842 | 6,313,329 | 13,881 | 8,227,500 |
| 3 | write:02-architecture/04-storage-architecture.md | Architecture | done | fable-5-1 | 09-22 13:37 | 30.3m | 70 | 48 | 2,060 | 1,928,898 | 10,728,627 | 44,970 | 12,704,555 |
| 4 | write:02-architecture/03-data-flow-and-document-lifecycle… | Architecture | done | fable-5-1 | 09-22 13:37 | 21.0m | 49 | 35 | 1,448 | 1,568,221 | 6,661,443 | 31,236 | 8,262,348 |
| 5 | write:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 13:37 | 38.7m | 99 | 70 | 2,988 | 2,454,622 | 17,765,128 | 98,803 | 20,321,541 |
| 6 | write:02-architecture/06-orchestration-and-workflows.md | Architecture | done | fable-5-1 | 09-22 13:37 | 21.1m | 53 | 35 | 1,576 | 2,708,021 | 7,491,060 | 52,227 | 10,252,884 |
| 7 | write:02-architecture/07-multi-tenancy-and-security-archi… | Architecture | done | fable-5-1 | 09-22 13:52 | 31.6m | 72 | 52 | 2,124 | 2,654,575 | 12,263,352 | 41,641 | 14,961,692 |
| 8 | write:02-architecture/08-deployment-architecture.md | Architecture | done | fable-5-1 | 09-22 13:58 | 17.9m | 62 | 43 | 1,864 | 2,836,505 | 10,411,221 | 34,911 | 13,284,501 |
| 9 | write:02-architecture/09-failure-modes-and-resilience.md | Architecture | done | fable-5-1 | 09-22 13:58 | 17.3m | 69 | 47 | 2,088 | 2,566,558 | 9,437,038 | 73,872 | 12,079,556 |
| 10 | review-anchor:02-architecture/01-system-overview.md | Architecture | done | fable-5-1 | 09-22 13:59 | 9.6m | 32 | 25 | 874 | 1,364,620 | 3,147,963 | 38,395 | 4,551,852 |
| 11 | review-tech:02-architecture/01-system-overview.md | Architecture | done | fable-5-1 | 09-22 14:07 | 16.8m | 46 | 32 | 1,352 | 1,987,879 | 3,924,305 | 60,194 | 5,973,730 |
| 12 | review-anchor:02-architecture/03-data-flow-and-document-l… | Architecture | done | fable-5-1 | 09-22 14:08 | 9.2m | 39 | 28 | 1,128 | 1,263,479 | 4,121,327 | 42,791 | 5,428,725 |
| 13 | review-tech:02-architecture/03-data-flow-and-document-lif… | Architecture | done | fable-5-1 | 09-22 14:15 | 15.9m | 54 | 43 | 1,608 | 1,094,732 | 5,884,495 | 45,411 | 7,026,246 |
| 14 | review-anchor:02-architecture/06-orchestration-and-workfl… | Architecture | done | fable-5-1 | 09-22 14:16 | 10.1m | 42 | 33 | 1,224 | 1,118,612 | 4,804,912 | 43,280 | 5,968,028 |
| 15 | review-tech:02-architecture/06-orchestration-and-workflow… | Architecture | done | fable-5-1 | 09-22 14:16 | 13.0m | 50 | 37 | 1,480 | 1,503,066 | 4,808,839 | 31,112 | 6,344,497 |
| 16 | review-anchor:02-architecture/02-component-architecture.md | Architecture | done | fable-5-1 | 09-22 14:18 | 9.1m | 43 | 36 | 1,226 | 2,013,638 | 3,204,810 | 43,827 | 5,263,501 |
| 17 | review-tech:02-architecture/02-component-architecture.md | Architecture | done | fable-5-1 | 09-22 14:24 | 25.2m | 59 | 41 | 1,678 | 2,588,502 | 6,259,976 | 67,231 | 8,917,387 |
| 18 | review-anchor:02-architecture/04-storage-architecture.md | Architecture | done | fable-5-1 | 09-22 14:24 | 9.0m | 46 | 37 | 1,382 | 1,599,821 | 4,664,405 | 42,447 | 6,308,055 |
| 19 | review-tech:02-architecture/04-storage-architecture.md | Architecture | done | fable-5-1 | 09-22 14:26 | 8.6m | 34 | 25 | 998 | 1,008,136 | 2,503,339 | 38,975 | 3,551,448 |
| 20 | review-anchor:02-architecture/09-failure-modes-and-resili… | Architecture | done | fable-5-1 | 09-22 14:27 | 9.0m | 56 | 42 | 1,642 | 1,936,321 | 6,695,614 | 40,902 | 8,674,479 |
| 21 | review-tech:02-architecture/09-failure-modes-and-resilien… | Architecture | done | fable-5-1 | 09-22 14:29 | 9.2m | 60 | 50 | 1,800 | 1,841,557 | 6,218,386 | 25,637 | 8,087,380 |
| 22 | review-anchor:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 14:31 | 9.7m | 46 | 35 | 1,352 | 1,308,823 | 5,554,197 | 46,562 | 6,910,934 |
| 23 | review-tech:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 14:33 | 17.7m | 54 | 42 | 1,608 | 1,980,052 | 6,602,290 | 33,727 | 8,617,677 |
| 24 | review-anchor:02-architecture/08-deployment-architecture.… | Architecture | done | fable-5-1 | 09-22 14:34 | 11.2m | 50 | 40 | 1,480 | 2,155,135 | 6,741,906 | 50,488 | 8,949,009 |
| 25 | review-tech:02-architecture/08-deployment-architecture.md | Architecture | done | fable-5-1 | 09-22 14:36 | 12.6m | 56 | 44 | 1,672 | 2,047,337 | 5,618,217 | 54,334 | 7,721,560 |
| 26 | fix:02-architecture/01-system-overview.md | Architecture | done | fable-5-1 | 09-22 14:38 | 7.1m | 64 | 49 | 1,898 | 880,008 | 8,520,892 | 28,515 | 9,431,313 |
| 27 | review-anchor:02-architecture/07-multi-tenancy-and-securi… | Architecture | done | fable-5-1 | 09-22 14:41 | 10.1m | 58 | 45 | 1,736 | 2,326,350 | 7,420,487 | 45,029 | 9,793,602 |
| 28 | review-tech:02-architecture/07-multi-tenancy-and-security… | Architecture | done | fable-5-1 | 09-22 14:45 | 9.7m | 51 | 40 | 1,512 | 2,132,885 | 5,069,564 | 42,215 | 7,246,176 |
| 29 | fix:02-architecture/06-orchestration-and-workflows.md | Architecture | done | fable-5-1 | 09-22 14:45 | 16.5m | 94 | 72 | 2,888 | 1,664,132 | 17,815,096 | 69,713 | 19,551,829 |
| 30 | fix:02-architecture/03-data-flow-and-document-lifecycle.md | Architecture | done | fable-5-1 | 09-22 14:48 | 25.9m | 140 | 110 | 4,360 | 2,806,190 | 28,980,343 | 79,647 | 31,870,540 |
| 31 | fix:02-architecture/04-storage-architecture.md | Architecture | done | fable-5-1 | 09-22 14:49 | 15.2m | 118 | 90 | 3,656 | 2,078,758 | 20,653,447 | 48,034 | 22,783,895 |
| 32 | fix:02-architecture/09-failure-modes-and-resilience.md | Architecture | done | fable-5-1 | 09-22 14:51 | 12.9m | 116 | 96 | 3,592 | 1,627,243 | 21,678,864 | 58,485 | 23,368,184 |
| 33 | verify:02-architecture/01-system-overview.md | Architecture | done | fable-5-1 | 09-22 14:51 | 3.1m | 24 | 18 | 708 | 340,263 | 1,711,972 | 10,002 | 2,062,945 |
| 34 | fix:02-architecture/08-deployment-architecture.md | Architecture | done | fable-5-1 | 09-22 14:54 | 13.8m | 114 | 92 | 3,528 | 1,612,753 | 20,733,569 | 65,013 | 22,414,863 |
| 35 | fix:02-architecture/02-component-architecture.md | Architecture | done | fable-5-1 | 09-22 14:55 | 19.5m | 100 | 82 | 3,110 | 1,934,998 | 19,565,854 | 95,221 | 21,599,183 |
| 36 | fix:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 15:02 | 17.7m | 126 | 103 | 3,942 | 2,789,963 | 24,822,924 | 54,380 | 27,671,209 |
| 37 | fix:02-architecture/07-multi-tenancy-and-security-archite… | Architecture | done | fable-5-1 | 09-22 15:04 | 16.5m | 122 | 99 | 3,814 | 1,943,932 | 24,820,628 | 63,884 | 26,832,258 |
| 38 | verify:02-architecture/06-orchestration-and-workflows.md | Architecture | done | fable-5-1 | 09-22 15:05 | 9.0m | 32 | 22 | 934 | 802,875 | 2,790,818 | 37,790 | 3,632,417 |
| 39 | verify:02-architecture/09-failure-modes-and-resilience.md | Architecture | done | fable-5-1 | 09-22 15:08 | 5.9m | 36 | 30 | 1,092 | 885,528 | 2,989,992 | 23,685 | 3,900,297 |
| 40 | verify:02-architecture/04-storage-architecture.md | Architecture | done | fable-5-1 | 09-22 15:14 | 6.1m | 44 | 32 | 1,318 | 830,848 | 3,676,358 | 26,805 | 4,535,329 |
| 41 | verify:02-architecture/08-deployment-architecture.md | Architecture | done | fable-5-1 | 09-22 15:14 | 8.2m | 59 | 43 | 1,798 | 1,340,207 | 6,274,201 | 35,469 | 7,651,675 |
| 42 | fix2:02-architecture/06-orchestration-and-workflows.md | Architecture | done | fable-5-1 | 09-22 15:14 | 10.9m | 84 | 63 | 2,568 | 1,502,642 | 13,942,365 | 55,486 | 15,503,061 |
| 43 | fix2:02-architecture/09-failure-modes-and-resilience.md | Architecture | done | fable-5-1 | 09-22 15:14 | 3.9m | 45 | 33 | 1,320 | 697,182 | 4,268,687 | 17,388 | 4,984,577 |
| 44 | verify:02-architecture/03-data-flow-and-document-lifecycl… | Architecture | done | fable-5-1 | 09-22 15:18 | 6.7m | 38 | 26 | 1,126 | 839,102 | 3,243,500 | 28,345 | 4,112,073 |
| 45 | verify:02-architecture/02-component-architecture.md | Architecture | done | fable-5-1 | 09-22 15:20 | 20.2m | 57 | 35 | 1,704 | 1,473,542 | 4,784,376 | 36,725 | 6,296,347 |
| 46 | verify:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 15:20 | 8.0m | 47 | 33 | 1,414 | 1,065,800 | 5,205,260 | 35,862 | 6,308,336 |
| 47 | verify:02-architecture/07-multi-tenancy-and-security-arch… | Architecture | done | fable-5-1 | 09-22 15:20 | 10.4m | 57 | 41 | 1,704 | 1,031,463 | 6,395,914 | 32,125 | 7,461,206 |
| 48 | fix2:02-architecture/08-deployment-architecture.md | Architecture | done | fable-5-1 | 09-22 15:22 | 4.7m | 49 | 33 | 1,448 | 747,794 | 4,881,280 | 18,392 | 5,648,914 |
| 49 | fix2:02-architecture/03-data-flow-and-document-lifecycle.… | Architecture | done | fable-5-1 | 09-22 15:25 | 8.0m | 57 | 45 | 1,704 | 965,535 | 6,763,547 | 37,984 | 7,768,770 |
| 50 | fix2:02-architecture/05-plugin-architecture.md | Architecture | done | fable-5-1 | 09-22 15:28 | 8.8m | 64 | 54 | 1,928 | 1,699,404 | 9,076,436 | 44,752 | 10,822,520 |
| 51 | fix2:02-architecture/07-multi-tenancy-and-security-archit… | Architecture | done | fable-5-1 | 09-22 15:31 | 3.9m | 49 | 36 | 1,478 | 712,682 | 4,410,652 | 16,032 | 5,140,844 |
| | **소계** | | | | | **11h 34m** | **3,209** | **2,430** | **96,658** | **84,563,742** | **455,251,057** | **2,308,196** | **542,219,653** |

#### 3단계 ADR(adrs) — `wf_f8852269-0c1` · 71 에이전트 · 실제 경과 시간 09-22 13:37 → 09-22 15:54 (2h 17m) · 에이전트 활동 시간 합산 11h 42m · 합계 520,117,427 토큰(출력 2,361,954)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | adr:list | ADRs | done | fable-5-1 | 09-22 13:37 | 24.0m | 23 | 14 | 586 | 862,489 | 705,079 | 58,752 | 1,626,906 |
| 2 | write:06-adr/0001-license-grade-table-and-d02-interpretat… | ADRs | done | fable-5-1 | 09-22 14:01 | 7.8m | 51 | 33 | 1,512 | 1,053,337 | 4,535,898 | 34,697 | 5,625,444 |
| 3 | write:06-adr/0002-provenance-element-path-and-nullable-pa… | ADRs | done | fable-5-1 | 09-22 14:01 | 8.4m | 56 | 38 | 1,672 | 1,773,737 | 5,942,413 | 37,101 | 7,754,923 |
| 4 | write:06-adr/0003-orchestrator-neutral-pipeline-and-non-d… | ADRs | done | fable-5-1 | 09-22 14:01 | 8.9m | 48 | 35 | 1,416 | 1,421,653 | 5,640,581 | 38,565 | 7,102,215 |
| 5 | write:06-adr/0004-deterministic-chunk-id-scoped-record-id… | ADRs | done | fable-5-1 | 09-22 14:01 | 10.3m | 61 | 45 | 1,832 | 1,199,765 | 7,085,726 | 25,208 | 8,312,531 |
| 6 | write:06-adr/0005-doc-version-content-hash-only-and-acl-p… | ADRs | done | fable-5-1 | 09-22 14:01 | 8.4m | 54 | 41 | 1,608 | 1,690,425 | 5,518,356 | 38,327 | 7,248,716 |
| 7 | write:06-adr/0006-pdf-fast-path-pypdfium2-pdftext-replace… | ADRs | done | fable-5-1 | 09-22 14:01 | 8.4m | 55 | 41 | 1,670 | 1,893,039 | 5,199,955 | 39,476 | 7,134,140 |
| 8 | write:06-adr/0007-hwp5-java-sidecar-first-pyhwp-demoted.md | ADRs | done | fable-5-1 | 09-22 14:09 | 8.8m | 58 | 43 | 1,736 | 2,889,300 | 5,581,663 | 11,082 | 8,483,781 |
| 9 | write:06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md | ADRs | done | fable-5-1 | 09-22 14:09 | 10.6m | 61 | 44 | 1,832 | 1,814,916 | 7,212,469 | 32,811 | 9,062,028 |
| 10 | write:06-adr/0009-embedding-serving-vllm-pooling-tei-inpr… | ADRs | done | fable-5-1 | 09-22 14:09 | 9.2m | 59 | 41 | 1,768 | 2,030,526 | 6,670,157 | 20,339 | 8,722,790 |
| 11 | write:06-adr/0010-bge-m3-rationale-and-late-interaction-s… | ADRs | done | fable-5-1 | 09-22 14:09 | 10.5m | 49 | 36 | 1,448 | 2,257,372 | 4,816,884 | 48,274 | 7,123,978 |
| 12 | write:06-adr/0011-kv-and-object-storage-valkey-rustfs-sea… | ADRs | done | fable-5-1 | 09-22 14:10 | 9.9m | 52 | 39 | 1,544 | 1,539,217 | 6,399,608 | 28,191 | 7,968,560 |
| 13 | write:06-adr/0012-lite-profile-qdrant-only-client-bm25.md | ADRs | done | fable-5-1 | 09-22 14:11 | 10.0m | 63 | 49 | 1,896 | 2,875,675 | 6,181,392 | 50,006 | 9,108,969 |
| 14 | write:06-adr/0013-fusion-rrf-k60-then-convex-combination-… | ADRs | done | fable-5-1 | 09-22 14:18 | 8.6m | 50 | 37 | 1,510 | 2,045,566 | 4,918,093 | 38,924 | 7,004,093 |
| 15 | write:06-adr/0014-sparse-representation-bge-m3-lexical-le… | ADRs | done | fable-5-1 | 09-22 14:19 | 10.1m | 53 | 40 | 1,606 | 1,576,961 | 6,034,580 | 31,585 | 7,644,732 |
| 16 | write:06-adr/0015-graph-rag-external-plugin-raptor-core-o… | ADRs | done | fable-5-1 | 09-22 14:20 | 10.3m | 67 | 47 | 2,024 | 1,923,710 | 9,053,220 | 46,279 | 11,025,233 |
| 17 | write:06-adr/0016-llm-enrichment-default-off-and-budget-p… | ADRs | done | fable-5-1 | 09-22 14:20 | 8.0m | 52 | 36 | 1,544 | 1,903,031 | 4,268,885 | 36,970 | 6,210,430 |
| 18 | write:06-adr/0017-event-delivery-outbox-cloudevents-no-br… | ADRs | done | fable-5-1 | 09-22 14:20 | 7.4m | 47 | 34 | 1,384 | 1,242,198 | 5,079,441 | 10,251 | 6,333,274 |
| 19 | write:06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md | ADRs | done | fable-5-1 | 09-22 14:21 | 9.0m | 50 | 33 | 1,510 | 1,326,557 | 4,720,881 | 40,745 | 6,089,693 |
| 20 | write:06-adr/0019-chunk-size-tokenizer-defaults-and-recou… | ADRs | done | fable-5-1 | 09-22 14:26 | 9.3m | 56 | 40 | 1,672 | 2,347,973 | 6,088,736 | 40,624 | 8,479,005 |
| 21 | write:06-adr/0020-default-chunker-structure-aware-and-dep… | ADRs | done | fable-5-1 | 09-22 14:27 | 10.3m | 52 | 40 | 1,544 | 2,337,721 | 5,353,237 | 46,268 | 7,738,770 |
| 22 | write:06-adr/0021-korean-analyzer-kiwi-promotion-and-inte… | ADRs | done | fable-5-1 | 09-22 14:28 | 10.3m | 68 | 45 | 2,056 | 2,423,581 | 8,482,105 | 43,971 | 10,951,713 |
| 23 | write:06-adr/0022-observability-genai-semconv-pin-and-lic… | ADRs | done | fable-5-1 | 09-22 14:29 | 11.9m | 59 | 46 | 1,768 | 1,782,829 | 6,369,126 | 7,592 | 8,161,315 |
| 24 | write:06-adr/0023-evaluation-qrels-answer-spans-and-linea… | ADRs | done | fable-5-1 | 09-22 14:30 | 13.0m | 61 | 39 | 1,832 | 2,258,898 | 7,503,800 | 41,783 | 9,806,313 |
| 25 | write:06-adr/0024-context-pack-ordering-and-anthropic-sea… | ADRs | done | fable-5-1 | 09-22 14:30 | 12.3m | 50 | 34 | 1,360 | 2,751,602 | 5,205,855 | 59,935 | 8,018,752 |
| 26 | write:06-adr/0025-mcp-cursor-pagination-and-tool-set.md | ADRs | done | fable-5-1 | 09-22 14:35 | 8.9m | 53 | 37 | 1,576 | 1,878,175 | 5,378,189 | 9,663 | 7,267,603 |
| 27 | write:06-adr/0026-index-commit-generation-saga-and-ledger… | ADRs | done | fable-5-1 | 09-22 14:38 | 9.4m | 59 | 44 | 1,768 | 2,277,891 | 7,488,015 | 42,163 | 9,809,837 |
| 28 | write:06-adr/0027-security-context-injection-and-acl-enfo… | ADRs | done | fable-5-1 | 09-22 14:38 | 8.5m | 57 | 37 | 1,704 | 1,433,466 | 6,303,116 | 14,020 | 7,752,306 |
| 29 | write:06-adr/0028-tenant-isolation-tiering-policy.md | ADRs | done | fable-5-1 | 09-22 14:41 | 8.5m | 60 | 44 | 1,800 | 1,858,579 | 7,096,853 | 21,446 | 8,978,678 |
| 30 | write:06-adr/0029-three-text-rule-and-deterministic-conte… | ADRs | done | fable-5-1 | 09-22 14:43 | 11.2m | 72 | 48 | 2,184 | 1,688,666 | 9,220,428 | 48,649 | 10,959,927 |
| 31 | write:06-adr/0030-single-coordinate-system-and-score-ledg… | ADRs | done | fable-5-1 | 09-22 14:43 | 8.2m | 53 | 41 | 1,576 | 1,570,007 | 5,840,822 | 37,050 | 7,449,455 |
| 32 | write:06-adr/0031-profile-schema-extends-and-quality-gate… | ADRs | done | fable-5-1 | 09-22 14:44 | 12.5m | 80 | 58 | 2,440 | 2,536,709 | 10,890,262 | 11,126 | 13,440,537 |
| 33 | write:06-adr/0032-plugin-sdk-stage-protocol-and-conforman… | ADRs | done | fable-5-1 | 09-22 14:47 | 10.5m | 70 | 53 | 2,120 | 2,057,292 | 9,917,915 | 12,938 | 11,990,265 |
| 34 | write:06-adr/0033-sidecar-convert-contract-and-isolation-… | ADRs | done | fable-5-1 | 09-22 14:47 | 9.8m | 55 | 41 | 1,670 | 2,961,462 | 6,039,501 | 12,271 | 9,014,904 |
| 35 | write:06-adr/0034-retrieval-hot-path-postgres-independenc… | ADRs | done | fable-5-1 | 09-22 14:49 | 17.5m | 77 | 53 | 2,344 | 2,928,978 | 14,372,036 | 22,906 | 17,326,264 |
| 36 | write:06-adr/0035-python-version-and-toolchain-pins.md | ADRs | done | fable-5-1 | 09-22 14:51 | 9.5m | 51 | 38 | 1,512 | 2,315,575 | 4,704,025 | 42,040 | 7,063,152 |
| 37 | write:06-adr/0036-naming-and-identifier-conventions.md | ADRs | done | fable-5-1 | 09-22 14:54 | 12.7m | 68 | 44 | 2,056 | 2,224,275 | 8,391,537 | 51,718 | 10,669,586 |
| 38 | write:06-adr/0037-artifact-cache-scope-and-stage-key-comp… | ADRs | done | fable-5-1 | 09-22 14:57 | 10.8m | 60 | 40 | 1,800 | 1,488,985 | 7,242,345 | 47,155 | 8,780,285 |
| 39 | write:06-adr/0038-outbound-egress-policy-and-webhook-sign… | ADRs | done | fable-5-1 | 09-22 14:57 | 9.5m | 57 | 39 | 1,704 | 2,138,952 | 5,329,679 | 11,056 | 7,481,391 |
| 40 | review-anchor:06-adr/0001-license-grade-table-and-d02-int… | ADRs | done | fable-5-1 | 09-22 14:57 | 6.4m | 35 | 28 | 970 | 1,269,285 | 2,395,105 | 29,590 | 3,694,950 |
| 41 | review-tech:06-adr/0001-license-grade-table-and-d02-inter… | ADRs | done | fable-5-1 | 09-22 15:01 | 9.3m | 43 | 32 | 1,226 | 1,393,138 | 2,845,971 | 36,360 | 4,276,695 |
| 42 | review-anchor:06-adr/0002-provenance-element-path-and-nul… | ADRs | done | fable-5-1 | 09-22 15:04 | 7.1m | 52 | 44 | 1,514 | 1,810,015 | 4,349,369 | 32,239 | 6,193,137 |
| 43 | review-tech:06-adr/0002-provenance-element-path-and-nulla… | ADRs | done | fable-5-1 | 09-22 15:07 | 7.3m | 63 | 50 | 1,896 | 2,245,096 | 4,794,247 | 31,394 | 7,072,633 |
| 44 | review-anchor:06-adr/0005-doc-version-content-hash-only-a… | ADRs | done | fable-5-1 | 09-22 15:07 | 8.4m | 46 | 38 | 1,322 | 1,429,979 | 4,125,722 | 38,802 | 5,595,825 |
| 45 | review-tech:06-adr/0005-doc-version-content-hash-only-and… | ADRs | done | fable-5-1 | 09-22 15:07 | 14.8m | 58 | 48 | 1,736 | 2,509,262 | 4,295,072 | 37,623 | 6,843,693 |
| 46 | review-anchor:06-adr/0006-pdf-fast-path-pypdfium2-pdftext… | ADRs | done | fable-5-1 | 09-22 15:08 | 6.5m | 45 | 34 | 1,290 | 1,521,285 | 3,565,795 | 48,878 | 5,137,248 |
| 47 | review-tech:06-adr/0006-pdf-fast-path-pypdfium2-pdftext-r… | ADRs | done | fable-5-1 | 09-22 15:10 | 15.4m | 69 | 54 | 2,088 | 2,722,229 | 6,189,135 | 39,345 | 8,952,797 |
| 48 | review-anchor:06-adr/0003-orchestrator-neutral-pipeline-a… | ADRs | done | fable-5-1 | 09-22 15:11 | 6.3m | 38 | 27 | 1,066 | 1,218,957 | 3,289,683 | 28,218 | 4,537,924 |
| 49 | review-tech:06-adr/0003-orchestrator-neutral-pipeline-and… | ADRs | done | fable-5-1 | 09-22 15:14 | 17.7m | 85 | 55 | 2,600 | 1,983,055 | 9,073,499 | 39,364 | 11,098,518 |
| 50 | review-anchor:06-adr/0004-deterministic-chunk-id-scoped-r… | ADRs | done | fable-5-1 | 09-22 15:14 | 7.6m | 47 | 32 | 1,354 | 1,144,350 | 4,564,211 | 42,056 | 5,751,971 |
| 51 | review-tech:06-adr/0004-deterministic-chunk-id-scoped-rec… | ADRs | done | fable-5-1 | 09-22 15:15 | 13.8m | 64 | 38 | 1,928 | 1,296,977 | 6,338,235 | 27,301 | 7,664,441 |
| 52 | review-anchor:06-adr/0007-hwp5-java-sidecar-first-pyhwp-d… | ADRs | done | fable-5-1 | 09-22 15:17 | 7.2m | 37 | 28 | 1,034 | 1,400,952 | 2,929,724 | 31,955 | 4,363,665 |
| 53 | review-tech:06-adr/0007-hwp5-java-sidecar-first-pyhwp-dem… | ADRs | done | fable-5-1 | 09-22 15:22 | 14.3m | 57 | 43 | 1,704 | 3,180,937 | 6,128,801 | 38,350 | 9,349,792 |
| 54 | review-anchor:06-adr/0009-embedding-serving-vllm-pooling-… | ADRs | done | fable-5-1 | 09-22 15:22 | 8.4m | 46 | 36 | 1,322 | 2,057,399 | 3,888,398 | 40,632 | 5,987,751 |
| 55 | review-tech:06-adr/0009-embedding-serving-vllm-pooling-te… | ADRs | done | fable-5-1 | 09-22 15:24 | 14.0m | 48 | 32 | 1,416 | 1,541,798 | 4,022,975 | 60,030 | 5,626,219 |
| 56 | review-anchor:06-adr/0011-kv-and-object-storage-valkey-ru… | ADRs | done | fable-5-1 | 09-22 15:26 | 6.5m | 36 | 28 | 1,002 | 1,159,731 | 3,004,327 | 28,996 | 4,194,056 |
| 57 | review-tech:06-adr/0011-kv-and-object-storage-valkey-rust… | ADRs | done | fable-5-1 | 09-22 15:29 | 19.2m | 68 | 40 | 2,056 | 1,659,759 | 6,970,158 | 53,407 | 8,685,380 |
| 58 | review-anchor:06-adr/0010-bge-m3-rationale-and-late-inter… | ADRs | done | fable-5-1 | 09-22 15:30 | 7.3m | 47 | 39 | 1,354 | 1,606,122 | 4,623,331 | 32,551 | 6,263,358 |
| 59 | review-tech:06-adr/0010-bge-m3-rationale-and-late-interac… | ADRs | done | fable-5-1 | 09-22 15:32 | 9.7m | 44 | 31 | 1,288 | 1,279,989 | 4,051,879 | 34,667 | 5,367,823 |
| 60 | review-anchor:06-adr/0008-ocr-default-rapidocr-ppocrv5-ko… | ADRs | done | fable-5-1 | 09-22 15:32 | 8.0m | 39 | 25 | 1,098 | 1,382,092 | 3,343,902 | 34,172 | 4,761,264 |
| 61 | review-tech:06-adr/0008-ocr-default-rapidocr-ppocrv5-kore… | ADRs | done | fable-5-1 | 09-22 15:36 | 15.7m | 78 | 57 | 2,320 | 2,975,421 | 7,669,688 | 42,392 | 10,689,821 |
| 62 | review-anchor:06-adr/0012-lite-profile-qdrant-only-client… | ADRs | done | fable-5-1 | 09-22 15:38 | 9.8m | 47 | 38 | 1,354 | 1,456,197 | 4,792,421 | 39,024 | 6,288,996 |
| 63 | review-tech:06-adr/0012-lite-profile-qdrant-only-client-b… | ADRs | done | fable-5-1 | 09-22 15:38 | 11.7m | 54 | 40 | 1,608 | 1,959,148 | 4,034,227 | 39,509 | 6,034,492 |
| 64 | review-anchor:06-adr/0013-fusion-rrf-k60-then-convex-comb… | ADRs | done | fable-5-1 | 09-22 15:40 | 8.4m | 42 | 34 | 1,194 | 1,383,147 | 3,988,885 | 34,034 | 5,407,260 |
| 65 | review-tech:06-adr/0013-fusion-rrf-k60-then-convex-combin… | ADRs | done | fable-5-1 | 09-22 15:41 | 7.4m | 52 | 38 | 1,544 | 1,525,787 | 3,994,096 | 31,656 | 5,553,083 |
| 66 | review-anchor:06-adr/0017-event-delivery-outbox-cloudeven… | ADRs | running | fable-5-1 | 09-22 15:48 | 6.7m | 39 | 30 | 1,098 | 1,361,681 | 3,609,239 | 18,470 | 4,990,488 |
| 67 | review-tech:06-adr/0017-event-delivery-outbox-cloudevents… | ADRs | running | fable-5-1 | 09-22 15:48 | 6.0m | 43 | 36 | 1,256 | 1,853,383 | 2,898,766 | 22,321 | 4,775,726 |
| 68 | review-anchor:06-adr/0016-llm-enrichment-default-off-and-… | ADRs | running | fable-5-1 | 09-22 15:48 | 5.8m | 32 | 23 | 874 | 848,808 | 2,485,022 | 26,506 | 3,361,210 |
| 69 | review-tech:06-adr/0016-llm-enrichment-default-off-and-bu… | ADRs | running | fable-5-1 | 09-22 15:49 | 5.5m | 35 | 26 | 1,000 | 1,007,723 | 2,294,323 | 18,255 | 3,321,301 |
| 70 | review-anchor:06-adr/0014-sparse-representation-bge-m3-le… | ADRs | running | fable-5-1 | 09-22 15:50 | 4.1m | 32 | 24 | 874 | 1,384,198 | 1,722,526 | 2,663 | 3,110,261 |
| 71 | review-tech:06-adr/0014-sparse-representation-bge-m3-lexi… | ADRs | running | fable-5-1 | 09-22 15:52 | 2.7m | 45 | 36 | 1,320 | 1,638,212 | 2,794,386 | 9,237 | 4,443,155 |
| | **소계** | | | | | **11h 42m** | **3,793** | **2,751** | **112,290** | **129,787,202** | **387,855,981** | **2,361,954** | **520,117,427** |

#### 3단계 파이프라인(pipelines) — `wf_02322627-3eb` · 138 에이전트 · 실제 경과 시간 09-22 15:43 → 09-22 20:37 (4h 53m) · 에이전트 활동 시간 합산 23h 33m · 합계 1,469,157,103 토큰(출력 5,118,162)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:04-pipelines/01-pipeline-framework.md | Pipelines | done | fable-5-1 | 09-22 15:43 | 26.4m | 61 | 45 | 1,804 | 3,648,582 | 9,776,172 | 59,351 | 13,485,909 |
| 2 | review-anchor:04-pipelines/01-pipeline-framework.md | Pipelines | done | fable-5-1 | 09-22 16:10 | 8.9m | 71 | 61 | 2,122 | 2,818,939 | 9,788,959 | 43,782 | 12,653,802 |
| 3 | review-tech:04-pipelines/01-pipeline-framework.md | Pipelines | done | fable-5-1 | 09-22 16:10 | 17.0m | 72 | 56 | 2,184 | 2,398,709 | 10,023,950 | 50,687 | 12,475,530 |
| 4 | fix:04-pipelines/01-pipeline-framework.md | Pipelines | done | fable-5-1 | 09-22 16:27 | 17.4m | 129 | 110 | 4,008 | 2,067,542 | 24,594,300 | 68,381 | 26,734,231 |
| 5 | verify:04-pipelines/01-pipeline-framework.md | Pipelines | done | fable-5-1 | 09-22 16:44 | 5.9m | 50 | 32 | 1,510 | 896,238 | 5,201,019 | 26,663 | 6,125,430 |
| 6 | write:04-pipelines/02-fetching-and-source-resolution.md | Pipelines | done | fable-5-1 | 09-22 16:50 | 21.0m | 72 | 54 | 2,214 | 4,857,474 | 11,963,612 | 91,855 | 16,915,155 |
| 7 | write:04-pipelines/03-parsing-router-and-format-detection… | Pipelines | done | fable-5-1 | 09-22 16:50 | 21.4m | 114 | 96 | 3,558 | 7,387,172 | 21,716,403 | 47,319 | 29,154,452 |
| 8 | write:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | done | fable-5-1 | 09-22 16:50 | 18.8m | 66 | 51 | 1,992 | 3,844,615 | 9,165,146 | 11,669 | 13,023,422 |
| 9 | write:04-pipelines/07-parser-html.md | Pipelines | done | fable-5-1 | 09-22 16:50 | 24.0m | 94 | 70 | 2,888 | 4,350,470 | 15,053,789 | 99,923 | 19,507,070 |
| 10 | write:04-pipelines/06-parser-doc-and-docx.md | Pipelines | done | fable-5-1 | 09-22 16:50 | 25.0m | 106 | 76 | 3,272 | 3,586,411 | 25,875,235 | 96,876 | 29,561,794 |
| 11 | write:04-pipelines/05-parser-pdf.md | Pipelines | done | fable-5-1 | 09-22 16:50 | 19.9m | 67 | 45 | 2,024 | 3,804,024 | 10,163,880 | 41,897 | 14,011,825 |
| 12 | write:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 17:09 | 32.3m | 73 | 56 | 2,188 | 3,616,723 | 11,605,840 | 76,767 | 15,301,518 |
| 13 | write:04-pipelines/09-normalization-and-cleaning.md | Pipelines | done | fable-5-1 | 09-22 17:10 | 23.8m | 86 | 58 | 2,632 | 5,054,511 | 15,575,624 | 54,338 | 20,687,105 |
| 14 | write:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 17:11 | 20.9m | 83 | 64 | 2,536 | 5,691,486 | 16,563,054 | 89,921 | 22,346,997 |
| 15 | write:04-pipelines/11-enrichment.md | Pipelines | done | fable-5-1 | 09-22 17:12 | 15.8m | 78 | 64 | 2,376 | 4,301,007 | 13,791,783 | 69,158 | 18,164,324 |
| 16 | write:04-pipelines/12-embedding.md | Pipelines | done | fable-5-1 | 09-22 17:14 | 17.2m | 74 | 57 | 2,248 | 3,565,739 | 14,239,212 | 72,632 | 17,879,831 |
| 17 | write:04-pipelines/13-indexing.md | Pipelines | done | fable-5-1 | 09-22 17:15 | 27.5m | 84 | 57 | 2,478 | 5,468,745 | 18,077,021 | 64,487 | 23,612,731 |
| 18 | write:04-pipelines/14-query-understanding.md | Pipelines | done | fable-5-1 | 09-22 17:27 | 29.9m | 69 | 56 | 2,060 | 4,171,667 | 11,283,734 | 24,763 | 15,482,224 |
| 19 | write:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 17:31 | 15.2m | 72 | 53 | 2,184 | 3,068,689 | 9,780,784 | 65,073 | 12,916,730 |
| 20 | write:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 17:32 | 29.0m | 107 | 72 | 3,304 | 5,683,711 | 18,448,754 | 58,586 | 24,194,355 |
| 21 | write:04-pipelines/17-post-processing-and-context-packing… | Pipelines | done | fable-5-1 | 09-22 17:34 | 18.1m | 71 | 55 | 2,212 | 2,394,883 | 11,307,711 | 23,604 | 13,728,410 |
| 22 | write:04-pipelines/18-advanced-retrieval-graph-raptor-age… | Pipelines | done | fable-5-1 | 09-22 17:41 | 19.8m | 89 | 70 | 2,728 | 3,935,322 | 17,597,576 | 38,098 | 21,573,724 |
| 23 | write:04-pipelines/19-update-delete-and-reindexing.md | Pipelines | done | fable-5-1 | 09-22 17:43 | 15.9m | 67 | 50 | 2,024 | 2,786,985 | 10,764,886 | 68,419 | 13,622,314 |
| 24 | review-anchor:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | done | fable-5-1 | 09-22 17:47 | 8.7m | 63 | 49 | 1,866 | 2,311,331 | 8,471,937 | 40,120 | 10,825,254 |
| 25 | review-tech:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | done | fable-5-1 | 09-22 17:52 | 10.9m | 61 | 50 | 1,832 | 1,707,103 | 10,105,527 | 40,517 | 11,854,979 |
| 26 | review-anchor:04-pipelines/05-parser-pdf.md | Pipelines | done | fable-5-1 | 09-22 17:55 | 8.7m | 48 | 39 | 1,386 | 1,749,030 | 4,618,788 | 38,966 | 6,408,170 |
| 27 | review-tech:04-pipelines/05-parser-pdf.md | Pipelines | done | fable-5-1 | 09-22 17:57 | 9.3m | 53 | 42 | 1,576 | 2,075,263 | 5,744,786 | 28,466 | 7,850,091 |
| 28 | review-anchor:04-pipelines/02-fetching-and-source-resolut… | Pipelines | done | fable-5-1 | 09-22 17:59 | 9.9m | 60 | 49 | 1,770 | 2,041,913 | 9,057,091 | 43,828 | 11,144,602 |
| 29 | review-tech:04-pipelines/02-fetching-and-source-resolutio… | Pipelines | done | fable-5-1 | 09-22 18:01 | 9.0m | 58 | 50 | 1,736 | 2,229,144 | 5,631,364 | 39,961 | 7,902,205 |
| 30 | review-anchor:04-pipelines/03-parsing-router-and-format-d… | Pipelines | done | fable-5-1 | 09-22 18:01 | 11.2m | 61 | 52 | 1,802 | 1,999,590 | 9,219,448 | 48,749 | 11,269,589 |
| 31 | review-tech:04-pipelines/03-parsing-router-and-format-det… | Pipelines | done | fable-5-1 | 09-22 18:03 | 11.5m | 67 | 53 | 2,054 | 2,459,391 | 7,272,898 | 34,987 | 9,769,330 |
| 32 | review-anchor:04-pipelines/07-parser-html.md | Pipelines | done | fable-5-1 | 09-22 18:04 | 8.7m | 62 | 53 | 1,834 | 2,086,556 | 9,524,877 | 38,267 | 11,651,534 |
| 33 | review-tech:04-pipelines/07-parser-html.md | Pipelines | done | fable-5-1 | 09-22 18:07 | 10.5m | 61 | 50 | 1,802 | 1,371,796 | 7,484,991 | 44,714 | 8,903,303 |
| 34 | review-anchor:04-pipelines/06-parser-doc-and-docx.md | Pipelines | done | fable-5-1 | 09-22 18:09 | 10.1m | 61 | 51 | 1,802 | 2,977,207 | 7,829,578 | 46,679 | 10,855,266 |
| 35 | review-tech:04-pipelines/06-parser-doc-and-docx.md | Pipelines | done | fable-5-1 | 09-22 18:10 | 10.2m | 77 | 64 | 2,314 | 3,058,099 | 9,844,810 | 45,928 | 12,951,151 |
| 36 | review-anchor:04-pipelines/11-enrichment.md | Pipelines | done | fable-5-1 | 09-22 18:12 | 9.4m | 65 | 55 | 1,960 | 2,749,989 | 9,618,002 | 43,985 | 12,413,936 |
| 37 | review-tech:04-pipelines/11-enrichment.md | Pipelines | done | fable-5-1 | 09-22 18:13 | 10.5m | 49 | 40 | 1,448 | 1,577,440 | 5,872,748 | 44,794 | 7,496,430 |
| 38 | review-anchor:04-pipelines/12-embedding.md | Pipelines | done | fable-5-1 | 09-22 18:15 | 9.2m | 70 | 60 | 2,120 | 3,230,083 | 12,075,422 | 41,860 | 15,349,485 |
| 39 | review-tech:04-pipelines/12-embedding.md | Pipelines | done | fable-5-1 | 09-22 18:17 | 19.3m | 80 | 54 | 2,440 | 3,353,350 | 13,577,927 | 57,891 | 16,991,608 |
| 40 | review-anchor:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 18:19 | 9.6m | 51 | 42 | 1,482 | 2,791,554 | 6,530,376 | 44,242 | 9,367,654 |
| 41 | review-tech:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 18:20 | 9.9m | 57 | 47 | 1,704 | 2,863,098 | 7,456,382 | 43,034 | 10,364,218 |
| 42 | review-anchor:04-pipelines/09-normalization-and-cleaning.… | Pipelines | done | fable-5-1 | 09-22 18:22 | 9.7m | 59 | 47 | 1,798 | 2,418,046 | 6,933,113 | 42,450 | 9,395,407 |
| 43 | review-tech:04-pipelines/09-normalization-and-cleaning.md | Pipelines | done | fable-5-1 | 09-22 18:23 | 11.7m | 50 | 42 | 1,480 | 1,596,989 | 5,949,888 | 44,542 | 7,592,899 |
| 44 | review-anchor:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 18:24 | 10.0m | 67 | 57 | 1,994 | 2,914,596 | 9,420,472 | 30,351 | 12,367,413 |
| 45 | review-tech:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 18:28 | 11.1m | 57 | 42 | 1,734 | 1,175,594 | 5,550,081 | 48,064 | 6,775,473 |
| 46 | review-anchor:04-pipelines/13-indexing.md | Pipelines | done | fable-5-1 | 09-22 18:30 | 7.1m | 51 | 42 | 1,482 | 2,062,482 | 6,716,697 | 30,550 | 8,811,211 |
| 47 | review-tech:04-pipelines/13-indexing.md | Pipelines | done | fable-5-1 | 09-22 18:32 | 12.4m | 72 | 59 | 2,184 | 1,777,624 | 9,440,382 | 53,419 | 11,273,609 |
| 48 | review-anchor:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 18:34 | 9.9m | 59 | 49 | 1,738 | 2,164,024 | 8,151,082 | 43,007 | 10,359,851 |
| 49 | review-tech:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 18:35 | 11.0m | 82 | 70 | 2,534 | 2,235,032 | 10,888,473 | 44,802 | 13,170,841 |
| 50 | review-anchor:04-pipelines/17-post-processing-and-context… | Pipelines | done | fable-5-1 | 09-22 18:37 | 9.6m | 73 | 62 | 2,186 | 2,041,947 | 11,811,255 | 43,055 | 13,898,443 |
| 51 | review-tech:04-pipelines/17-post-processing-and-context-p… | Pipelines | done | fable-5-1 | 09-22 18:38 | 9.6m | 54 | 42 | 1,608 | 1,811,853 | 6,640,846 | 42,986 | 8,497,293 |
| 52 | review-anchor:04-pipelines/14-query-understanding.md | Pipelines | done | fable-5-1 | 09-22 18:40 | 10.1m | 60 | 51 | 1,830 | 2,609,395 | 7,406,983 | 46,411 | 10,064,619 |
| 53 | review-tech:04-pipelines/14-query-understanding.md | Pipelines | done | fable-5-1 | 09-22 18:44 | 11.3m | 54 | 42 | 1,608 | 1,602,467 | 6,378,697 | 48,915 | 8,031,687 |
| 54 | review-anchor:04-pipelines/19-update-delete-and-reindexin… | Pipelines | done | fable-5-1 | 09-22 18:44 | 9.1m | 56 | 49 | 1,642 | 2,358,044 | 6,165,427 | 42,681 | 8,567,794 |
| 55 | review-tech:04-pipelines/19-update-delete-and-reindexing.… | Pipelines | done | fable-5-1 | 09-22 18:46 | 16.4m | 77 | 64 | 2,314 | 2,037,479 | 9,119,988 | 51,128 | 11,210,909 |
| 56 | review-anchor:04-pipelines/18-advanced-retrieval-graph-ra… | Pipelines | done | fable-5-1 | 09-22 18:46 | 10.9m | 53 | 40 | 1,576 | 1,525,042 | 7,826,666 | 48,923 | 9,402,207 |
| 57 | review-tech:04-pipelines/18-advanced-retrieval-graph-rapt… | Pipelines | done | fable-5-1 | 09-22 18:47 | 10.7m | 55 | 44 | 1,640 | 2,699,725 | 6,888,047 | 41,913 | 9,631,325 |
| 58 | review-anchor:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 18:50 | 8.8m | 61 | 52 | 1,832 | 2,786,269 | 7,645,725 | 41,653 | 10,475,479 |
| 59 | review-tech:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 18:53 | 9.8m | 55 | 44 | 1,640 | 1,941,166 | 5,508,350 | 22,754 | 7,473,910 |
| 60 | fix:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 18:55 | 14.2m | 95 | 74 | 2,918 | 2,096,091 | 16,122,762 | 49,105 | 18,270,876 |
| 61 | fix:04-pipelines/05-parser-pdf.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 18:57 | 9.1m | 69 | 55 | 2,056 | 1,836,130 | 10,438,653 | 27,455 | 12,304,294 |
| 62 | fix:04-pipelines/02-fetching-and-source-resolution.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 18:58 | 10.8m | 72 | 57 | 2,152 | 1,825,494 | 9,728,044 | 31,607 | 11,587,297 |
| 63 | fix:04-pipelines/03-parsing-router-and-format-detection.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 18:59 | 10.9m | 74 | 64 | 2,216 | 1,754,123 | 10,856,819 | 22,430 | 12,635,588 |
| 64 | fix:04-pipelines/07-parser-html.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 19:02 | 3.8m | 37 | 35 | 1,062 | 485,224 | 3,961,867 | 6,228 | 4,454,381 |
| 65 | fix:04-pipelines/06-parser-doc-and-docx.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 19:03 | 3.3m | 7 | 4 | 72 | 161,344 | 165,474 | 272 | 327,162 |
| 66 | fix:04-pipelines/11-enrichment.md | Pipelines | failed | <synthetic> | 09-22 19:06 | 3.1m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 67 | fix:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 19:06 | 20.1m | 140 | 120 | 4,390 | 3,283,688 | 34,456,069 | 89,714 | 37,833,861 |
| 68 | fix:04-pipelines/09-normalization-and-cleaning.md | Pipelines | done | fable-5-1 | 09-22 19:06 | 21.0m | 112 | 94 | 3,554 | 1,607,691 | 22,898,830 | 71,817 | 24,581,892 |
| 69 | fix:04-pipelines/12-embedding.md | Pipelines | done | fable-5-1 | 09-22 19:09 | 12.2m | 104 | 81 | 3,238 | 1,514,161 | 17,084,261 | 40,434 | 18,642,094 |
| 70 | fix:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 19:09 | 15.9m | 111 | 88 | 3,462 | 1,564,357 | 18,911,607 | 72,547 | 20,551,973 |
| 71 | fix:04-pipelines/13-indexing.md | Pipelines | done | fable-5-1 | 09-22 19:09 | 13.0m | 105 | 90 | 3,270 | 1,420,000 | 15,892,414 | 45,302 | 17,360,986 |
| 72 | fix:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 19:09 | 14.2m | 126 | 103 | 3,942 | 2,254,379 | 22,768,608 | 55,705 | 25,082,634 |
| 73 | fix:04-pipelines/17-post-processing-and-context-packing.md | Pipelines | done | fable-5-1 | 09-22 19:21 | 20.3m | 157 | 116 | 4,904 | 2,563,442 | 43,064,857 | 76,806 | 45,710,009 |
| 74 | fix:04-pipelines/14-query-understanding.md | Pipelines | running | fable-5-1 | 09-22 19:22 | 13.4m | 89 | 77 | 2,758 | 1,738,170 | 16,099,663 | 42,112 | 17,882,703 |
| 75 | fix:04-pipelines/18-advanced-retrieval-graph-raptor-agent… | Pipelines | done | fable-5-1 | 09-22 19:24 | 16.9m | 120 | 100 | 3,720 | 2,639,782 | 21,844,849 | 76,549 | 24,564,900 |
| 76 | fix:04-pipelines/19-update-delete-and-reindexing.md | Pipelines | done | fable-5-1 | 09-22 19:25 | 20.8m | 124 | 106 | 3,848 | 8,210,284 | 25,760,323 | 104,982 | 34,079,437 |
| 77 | fix:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 19:26 | 12.6m | 101 | 86 | 3,112 | 1,922,953 | 16,922,028 | 52,637 | 18,900,730 |
| 78 | verify:04-pipelines/12-embedding.md | Pipelines | done | fable-5-1 | 09-22 19:27 | 8.0m | 42 | 31 | 1,224 | 969,717 | 3,655,069 | 33,087 | 4,659,097 |
| 79 | verify:04-pipelines/13-indexing.md | Pipelines | done | fable-5-1 | 09-22 19:35 | 9.9m | 104 | 39 | 3,238 | 283,246 | 11,212,753 | 56,596 | 11,555,833 |
| 80 | fix:04-pipelines/14-query-understanding.md | Pipelines | done | fable-5-1 | 09-22 19:36 | 10.4m | 80 | 56 | 2,440 | 1,762,205 | 14,410,658 | 42,012 | 16,217,315 |
| 81 | verify:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 19:39 | 7.2m | 64 | 53 | 1,928 | 1,859,446 | 6,704,067 | 33,222 | 8,598,663 |
| 82 | verify:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 19:41 | 9.6m | 43 | 17 | 1,286 | 279,304 | 4,250,087 | 36,790 | 4,567,467 |
| 83 | verify:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 19:41 | 7.4m | 49 | 34 | 1,478 | 929,798 | 5,328,123 | 33,312 | 6,292,711 |
| 84 | verify:04-pipelines/09-normalization-and-cleaning.md | Pipelines | done | fable-5-1 | 09-22 19:45 | 6.9m | 44 | 30 | 1,288 | 866,055 | 4,740,941 | 29,204 | 5,637,488 |
| 85 | verify:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 19:46 | 5.0m | 44 | 34 | 1,318 | 970,910 | 3,662,563 | 21,865 | 4,656,656 |
| 86 | verify:04-pipelines/18-advanced-retrieval-graph-raptor-ag… | Pipelines | done | fable-5-1 | 09-22 19:46 | 5.5m | 43 | 30 | 1,286 | 921,442 | 3,972,459 | 24,615 | 4,919,802 |
| 87 | verify:04-pipelines/17-post-processing-and-context-packin… | Pipelines | done | fable-5-1 | 09-22 19:46 | 6.9m | 51 | 40 | 1,512 | 1,266,285 | 6,178,231 | 20,868 | 7,466,896 |
| 88 | verify:04-pipelines/19-update-delete-and-reindexing.md | Pipelines | done | fable-5-1 | 09-22 19:49 | 7.1m | 47 | 36 | 1,414 | 1,604,633 | 4,427,631 | 31,635 | 6,065,313 |
| 89 | fix2:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | done | fable-5-1 | 09-22 19:50 | 6.1m | 69 | 55 | 2,088 | 925,057 | 8,037,845 | 25,573 | 8,990,563 |
| 90 | verify:04-pipelines/14-query-understanding.md | Pipelines | done | fable-5-1 | 09-22 19:51 | 5.0m | 37 | 25 | 1,094 | 864,630 | 3,349,912 | 21,884 | 4,237,520 |
| 91 | fix2:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 19:52 | 5.3m | 43 | 31 | 1,256 | 1,027,778 | 4,024,368 | 22,679 | 5,076,081 |
| 92 | fix2:04-pipelines/16-reranking.md | Pipelines | done | fable-5-1 | 09-22 19:52 | 5.4m | 60 | 49 | 1,800 | 961,152 | 6,609,921 | 24,083 | 7,596,956 |
| 93 | review-anchor:04-pipelines/02-fetching-and-source-resolut… | Pipelines | done | fable-5-1 | 09-22 19:58 | 9.0m | 62 | 53 | 1,834 | 2,414,394 | 8,691,597 | 44,622 | 11,152,447 |
| 94 | review-tech:04-pipelines/02-fetching-and-source-resolutio… | Pipelines | done | fable-5-1 | 09-22 19:58 | 10.2m | 55 | 42 | 1,640 | 1,344,964 | 5,838,646 | 45,574 | 7,230,824 |
| 95 | review-anchor:04-pipelines/03-parsing-router-and-format-d… | Pipelines | done | fable-5-1 | 09-22 19:58 | 10.0m | 81 | 68 | 2,472 | 3,563,423 | 11,972,322 | 46,690 | 15,584,907 |
| 96 | review-tech:04-pipelines/03-parsing-router-and-format-det… | Pipelines | done | fable-5-1 | 09-22 19:58 | 12.5m | 82 | 69 | 2,504 | 2,638,893 | 9,901,042 | 54,436 | 12,596,875 |
| 97 | review-anchor:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | done | fable-5-1 | 09-22 19:58 | 9.2m | 66 | 53 | 1,962 | 2,673,556 | 9,156,223 | 42,035 | 11,873,776 |
| 98 | review-tech:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | done | fable-5-1 | 09-22 19:58 | 17.4m | 64 | 44 | 1,928 | 3,269,467 | 7,414,773 | 51,746 | 10,737,914 |
| 99 | review-anchor:04-pipelines/05-parser-pdf.md | Pipelines | done | fable-5-1 | 09-22 20:07 | 9.8m | 62 | 53 | 1,864 | 3,485,503 | 7,707,266 | 45,907 | 11,240,540 |
| 100 | review-tech:04-pipelines/05-parser-pdf.md | Pipelines | done | fable-5-1 | 09-22 20:07 | 8.4m | 53 | 40 | 1,546 | 2,421,401 | 5,240,030 | 30,965 | 7,693,942 |
| 101 | review-anchor:04-pipelines/06-parser-doc-and-docx.md | Pipelines | done | fable-5-1 | 09-22 20:08 | 9.6m | 66 | 57 | 1,962 | 3,106,427 | 8,325,569 | 43,066 | 11,477,024 |
| 102 | review-tech:04-pipelines/06-parser-doc-and-docx.md | Pipelines | done | fable-5-1 | 09-22 20:08 | 9.7m | 67 | 55 | 2,054 | 2,633,272 | 7,912,623 | 41,198 | 10,589,147 |
| 103 | review-anchor:04-pipelines/07-parser-html.md | Pipelines | done | fable-5-1 | 09-22 20:10 | 9.1m | 63 | 53 | 1,866 | 2,399,849 | 9,020,109 | 41,295 | 11,463,119 |
| 104 | review-tech:04-pipelines/07-parser-html.md | Pipelines | done | fable-5-1 | 09-22 20:15 | 11.2m | 44 | 35 | 1,258 | 1,470,185 | 3,092,712 | 43,810 | 4,607,965 |
| 105 | review-anchor:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 20:15 | 11.1m | 44 | 35 | 1,258 | 1,231,985 | 5,485,007 | 47,117 | 6,765,367 |
| 106 | review-tech:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | done | fable-5-1 | 09-22 20:17 | 11.3m | 66 | 57 | 1,962 | 1,875,184 | 7,604,955 | 50,548 | 9,532,649 |
| 107 | review-anchor:04-pipelines/09-normalization-and-cleaning.… | Pipelines | done | fable-5-1 | 09-22 20:18 | 8.5m | 64 | 52 | 1,898 | 2,081,322 | 9,822,263 | 38,276 | 11,943,759 |
| 108 | review-tech:04-pipelines/09-normalization-and-cleaning.md | Pipelines | done | fable-5-1 | 09-22 20:18 | 11.9m | 59 | 47 | 1,768 | 2,606,920 | 6,291,928 | 46,447 | 8,947,063 |
| 109 | review-anchor:04-pipelines/10-chunking-strategies.md | Pipelines | done | fable-5-1 | 09-22 20:20 | 10.5m | 64 | 48 | 1,898 | 3,467,027 | 9,912,478 | 48,786 | 13,430,189 |
| 110 | review-tech:04-pipelines/10-chunking-strategies.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 20:26 | 7.1m | 64 | 55 | 1,896 | 2,631,181 | 9,041,931 | 17,352 | 11,692,360 |
| 111 | review-anchor:04-pipelines/11-enrichment.md | Pipelines | done | fable-5-1 | 09-22 20:26 | 8.2m | 62 | 46 | 1,834 | 2,139,835 | 7,609,593 | 38,595 | 9,789,857 |
| 112 | review-tech:04-pipelines/11-enrichment.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 20:27 | 10.0m | 60 | 52 | 1,768 | 2,169,154 | 8,013,914 | 35,114 | 10,219,950 |
| 113 | review-anchor:04-pipelines/12-embedding.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 20:28 | 6.4m | 58 | 51 | 1,734 | 2,954,400 | 7,343,227 | 21,368 | 10,320,729 |
| 114 | review-tech:04-pipelines/12-embedding.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 20:30 | 6.4m | 45 | 38 | 1,288 | 1,607,913 | 4,506,145 | 23,139 | 6,138,485 |
| 115 | review-anchor:04-pipelines/13-indexing.md | Pipelines | failed | fable-5-1, <synthetic> | 09-22 20:30 | 6.7m | 57 | 48 | 1,702 | 2,749,886 | 6,521,283 | 18,108 | 9,290,979 |
| 116 | review-tech:04-pipelines/13-indexing.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 117 | review-anchor:04-pipelines/14-query-understanding.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 118 | review-tech:04-pipelines/14-query-understanding.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 119 | review-anchor:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 120 | review-tech:04-pipelines/15-hybrid-search-and-fusion.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 121 | review-anchor:04-pipelines/16-reranking.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 122 | review-tech:04-pipelines/16-reranking.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 123 | review-anchor:04-pipelines/17-post-processing-and-context… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 124 | review-tech:04-pipelines/17-post-processing-and-context-p… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 125 | review-anchor:04-pipelines/18-advanced-retrieval-graph-ra… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 126 | review-tech:04-pipelines/18-advanced-retrieval-graph-rapt… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 127 | review-anchor:04-pipelines/19-update-delete-and-reindexin… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 128 | review-tech:04-pipelines/19-update-delete-and-reindexing.… | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 129 | fix:04-pipelines/02-fetching-and-source-resolution.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 130 | fix:04-pipelines/03-parsing-router-and-format-detection.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 131 | fix:04-pipelines/04-parser-hwpx-and-hwp.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 132 | fix:04-pipelines/05-parser-pdf.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 133 | fix:04-pipelines/06-parser-doc-and-docx.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 134 | fix:04-pipelines/07-parser-html.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 135 | fix:04-pipelines/08-parser-txt-md-and-others.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 136 | fix:04-pipelines/09-normalization-and-cleaning.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 137 | fix:04-pipelines/10-chunking-strategies.md | Pipelines | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 138 | fix:04-pipelines/11-enrichment.md | Pipelines | failed | <synthetic> | 09-22 20:37 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| | **소계** | | | | | **23h 33m** | **7,949** | **6,267** | **239,514** | **279,094,467** | **1,184,704,960** | **5,118,162** | **1,469,157,103** |

#### 3단계 API·평가(api-eval) — `wf_7bfc9aa6-c62` · 52 에이전트 · 실제 경과 시간 09-22 18:27 → 09-22 20:35 (2h 8m) · 에이전트 활동 시간 합산 10h 18m · 합계 645,445,419 토큰(출력 2,143,870)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:05-api/01-api-design-guidelines.md | API & Evaluation | done | fable-5-1 | 09-22 18:27 | 23.8m | 97 | 68 | 3,014 | 4,665,197 | 14,770,480 | 103,387 | 19,542,078 |
| 2 | write:08-evaluation/01-evaluation-strategy.md | API & Evaluation | done | fable-5-1 | 09-22 18:27 | 11.7m | 50 | 38 | 1,480 | 2,883,303 | 6,051,923 | 11,243 | 8,947,949 |
| 3 | review-anchor:08-evaluation/01-evaluation-strategy.md | API & Evaluation | done | fable-5-1 | 09-22 18:38 | 10.0m | 51 | 42 | 1,482 | 2,182,015 | 6,048,154 | 44,968 | 8,276,619 |
| 4 | review-tech:08-evaluation/01-evaluation-strategy.md | API & Evaluation | done | fable-5-1 | 09-22 18:38 | 8.6m | 54 | 43 | 1,578 | 1,382,042 | 6,152,773 | 36,708 | 7,573,101 |
| 5 | fix:08-evaluation/01-evaluation-strategy.md | API & Evaluation | done | fable-5-1 | 09-22 18:48 | 11.9m | 92 | 74 | 2,824 | 1,466,593 | 14,424,082 | 50,078 | 15,943,577 |
| 6 | review-anchor:05-api/01-api-design-guidelines.md | API & Evaluation | done | fable-5-1 | 09-22 18:50 | 8.9m | 68 | 57 | 2,026 | 2,721,343 | 8,404,715 | 41,196 | 11,169,280 |
| 7 | review-tech:05-api/01-api-design-guidelines.md | API & Evaluation | done | fable-5-1 | 09-22 18:50 | 9.6m | 50 | 42 | 1,480 | 1,212,463 | 4,735,525 | 29,824 | 5,979,292 |
| 8 | fix:05-api/01-api-design-guidelines.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 19:00 | 6.2m | 46 | 37 | 1,320 | 1,200,649 | 4,474,962 | 5,346 | 5,682,277 |
| 9 | verify:08-evaluation/01-evaluation-strategy.md | API & Evaluation | done | fable-5-1 | 09-22 19:00 | 5.3m | 22 | 18 | 614 | 556,384 | 1,108,927 | 16,678 | 1,682,603 |
| 10 | write:05-api/02-ingestion-api.md | API & Evaluation | failed | <synthetic> | 09-22 19:06 | 2.9m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11 | write:05-api/03-retrieval-api.md | API & Evaluation | done | fable-5-1 | 09-22 19:06 | 31.0m | 91 | 70 | 2,792 | 6,764,471 | 19,513,283 | 78,522 | 26,359,068 |
| 12 | write:05-api/05-mcp-server.md | API & Evaluation | failed | <synthetic> | 09-22 19:06 | 3.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 13 | write:05-api/04-management-api.md | API & Evaluation | failed | <synthetic> | 09-22 19:06 | 3.2m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 14 | write:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 19:06 | 17.8m | 80 | 68 | 2,440 | 3,199,718 | 14,167,924 | 28,196 | 17,398,278 |
| 15 | write:05-api/07-webhooks-and-events.md | API & Evaluation | done | fable-5-1 | 09-22 19:06 | 20.3m | 72 | 59 | 2,274 | 3,163,309 | 13,027,607 | 78,347 | 16,271,537 |
| 16 | write:08-evaluation/02-retrieval-metrics-and-harness.md | API & Evaluation | done | fable-5-1 | 09-22 19:09 | 17.6m | 94 | 75 | 2,888 | 4,207,093 | 16,534,885 | 76,077 | 20,820,943 |
| 17 | write:08-evaluation/03-golden-dataset-construction.md | API & Evaluation | done | fable-5-1 | 09-22 19:09 | 21.8m | 92 | 75 | 2,764 | 3,081,552 | 19,253,955 | 32,474 | 22,370,745 |
| 18 | write:08-evaluation/04-llm-judge-and-generation-quality.md | API & Evaluation | done | fable-5-1 | 09-22 19:09 | 27.6m | 87 | 71 | 2,666 | 3,685,032 | 18,093,977 | 21,814 | 21,803,489 |
| 19 | write:08-evaluation/05-benchmark-plan-and-baselines.md | API & Evaluation | done | fable-5-1 | 09-22 19:24 | 33.9m | 89 | 60 | 2,638 | 9,131,962 | 17,599,483 | 84,321 | 26,818,404 |
| 20 | write:08-evaluation/06-online-feedback-loop.md | API & Evaluation | done | fable-5-1 | 09-22 19:27 | 17.5m | 80 | 63 | 2,440 | 3,564,527 | 14,358,515 | 74,384 | 17,999,866 |
| 21 | review-anchor:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 19:27 | 10.7m | 77 | 63 | 2,074 | 2,560,450 | 12,601,595 | 94,679 | 15,258,798 |
| 22 | review-tech:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 19:31 | 12.1m | 52 | 42 | 1,304 | 1,924,694 | 5,038,343 | 61,672 | 7,026,013 |
| 23 | review-anchor:05-api/07-webhooks-and-events.md | API & Evaluation | done | fable-5-1 | 09-22 19:37 | 8.8m | 69 | 60 | 2,088 | 2,144,673 | 9,051,909 | 38,687 | 11,237,357 |
| 24 | review-tech:05-api/07-webhooks-and-events.md | API & Evaluation | done | fable-5-1 | 09-22 19:37 | 11.5m | 70 | 59 | 2,120 | 2,119,963 | 7,813,471 | 52,212 | 9,987,766 |
| 25 | review-anchor:08-evaluation/02-retrieval-metrics-and-harn… | API & Evaluation | done | fable-5-1 | 09-22 19:37 | 9.5m | 52 | 42 | 1,544 | 1,808,883 | 7,638,373 | 40,311 | 9,489,111 |
| 26 | review-tech:08-evaluation/02-retrieval-metrics-and-harnes… | API & Evaluation | done | fable-5-1 | 09-22 19:43 | 14.2m | 64 | 51 | 1,778 | 2,175,084 | 7,760,719 | 43,450 | 9,981,031 |
| 27 | review-anchor:08-evaluation/03-golden-dataset-constructio… | API & Evaluation | done | fable-5-1 | 09-22 19:44 | 10.4m | 57 | 41 | 1,704 | 2,251,588 | 8,602,188 | 44,028 | 10,899,508 |
| 28 | review-tech:08-evaluation/03-golden-dataset-construction.… | API & Evaluation | done | fable-5-1 | 09-22 19:46 | 15.6m | 45 | 32 | 1,230 | 1,578,822 | 5,311,906 | 36,013 | 6,927,971 |
| 29 | review-anchor:08-evaluation/04-llm-judge-and-generation-q… | API & Evaluation | done | fable-5-1 | 09-22 19:47 | 7.9m | 57 | 48 | 1,644 | 2,477,327 | 7,981,190 | 35,415 | 10,495,576 |
| 30 | review-tech:08-evaluation/04-llm-judge-and-generation-qua… | API & Evaluation | done | fable-5-1 | 09-22 19:49 | 27.1m | 105 | 58 | 3,060 | 2,605,977 | 17,959,310 | 61,805 | 20,630,152 |
| 31 | review-anchor:05-api/03-retrieval-api.md | API & Evaluation | done | fable-5-1 | 09-22 19:55 | 9.8m | 86 | 67 | 2,572 | 2,761,189 | 14,886,488 | 40,732 | 17,690,981 |
| 32 | review-tech:05-api/03-retrieval-api.md | API & Evaluation | done | fable-5-1 | 09-22 19:55 | 9.3m | 64 | 50 | 1,658 | 2,153,209 | 8,447,690 | 40,578 | 10,643,135 |
| 33 | fix:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 19:57 | 15.7m | 132 | 102 | 3,864 | 2,703,970 | 28,130,058 | 47,014 | 30,884,906 |
| 34 | review-anchor:08-evaluation/06-online-feedback-loop.md | API & Evaluation | done | fable-5-1 | 09-22 19:58 | 8.4m | 61 | 54 | 1,802 | 2,428,639 | 6,661,615 | 39,109 | 9,131,165 |
| 35 | review-tech:08-evaluation/06-online-feedback-loop.md | API & Evaluation | done | fable-5-1 | 09-22 20:01 | 10.2m | 72 | 60 | 2,184 | 1,814,013 | 8,285,553 | 44,360 | 10,146,110 |
| 36 | fix:05-api/07-webhooks-and-events.md | API & Evaluation | done | fable-5-1 | 09-22 20:04 | 16.4m | 131 | 104 | 4,072 | 2,342,171 | 25,748,693 | 79,607 | 28,174,543 |
| 37 | fix:08-evaluation/02-retrieval-metrics-and-harness.md | API & Evaluation | done | fable-5-1 | 09-22 20:04 | 14.9m | 127 | 104 | 3,944 | 2,168,522 | 24,680,852 | 63,792 | 26,917,110 |
| 38 | review-anchor:08-evaluation/05-benchmark-plan-and-baselin… | API & Evaluation | done | fable-5-1 | 09-22 20:06 | 11.2m | 63 | 48 | 1,896 | 2,448,278 | 10,007,627 | 48,421 | 12,506,222 |
| 39 | review-tech:08-evaluation/05-benchmark-plan-and-baselines… | API & Evaluation | done | fable-5-1 | 09-22 20:12 | 9.7m | 51 | 39 | 1,512 | 1,566,479 | 5,129,269 | 42,444 | 6,739,704 |
| 40 | fix:08-evaluation/03-golden-dataset-construction.md | API & Evaluation | done | fable-5-1 | 09-22 20:13 | 15.0m | 126 | 105 | 3,852 | 2,444,073 | 27,217,125 | 68,279 | 29,733,329 |
| 41 | fix:05-api/03-retrieval-api.md | API & Evaluation | done | fable-5-1 | 09-22 20:16 | 14.5m | 135 | 117 | 4,230 | 2,712,168 | 26,840,596 | 51,776 | 29,608,770 |
| 42 | fix:08-evaluation/06-online-feedback-loop.md | API & Evaluation | done | fable-5-1 | 09-22 20:18 | 9.1m | 84 | 61 | 2,598 | 1,206,623 | 11,225,187 | 42,114 | 12,476,522 |
| 43 | verify:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 20:19 | 6.7m | 51 | 43 | 1,542 | 1,051,977 | 4,240,503 | 29,711 | 5,323,733 |
| 44 | fix:08-evaluation/04-llm-judge-and-generation-quality.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 20:21 | 12.0m | 87 | 67 | 2,572 | 2,965,093 | 15,970,279 | 35,804 | 18,973,748 |
| 45 | verify:08-evaluation/02-retrieval-metrics-and-harness.md | API & Evaluation | done | fable-5-1 | 09-22 20:21 | 6.4m | 47 | 32 | 1,414 | 391,439 | 4,757,867 | 25,923 | 5,176,643 |
| 46 | verify:05-api/07-webhooks-and-events.md | API & Evaluation | done | fable-5-1 | 09-22 20:26 | 4.6m | 41 | 31 | 1,222 | 925,743 | 3,231,101 | 20,286 | 4,178,352 |
| 47 | fix:08-evaluation/05-benchmark-plan-and-baselines.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 20:27 | 6.1m | 41 | 32 | 1,160 | 917,770 | 4,195,595 | 27,192 | 5,141,717 |
| 48 | fix2:05-api/06-client-sdks.md | API & Evaluation | done | fable-5-1 | 09-22 20:28 | 4.8m | 34 | 24 | 998 | 404,403 | 2,744,254 | 20,320 | 3,169,975 |
| 49 | verify:08-evaluation/06-online-feedback-loop.md | API & Evaluation | done | fable-5-1 | 09-22 20:28 | 3.6m | 28 | 18 | 806 | 575,531 | 1,847,118 | 22,884 | 2,446,339 |
| 50 | fix2:08-evaluation/02-retrieval-metrics-and-harness.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 20:30 | 3.6m | 33 | 26 | 934 | 515,392 | 2,068,646 | 15,269 | 2,600,241 |
| 51 | verify:08-evaluation/03-golden-dataset-construction.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 20:31 | 2.5m | 38 | 29 | 1,094 | 1,543,716 | 3,224,495 | 10,332 | 4,779,637 |
| 52 | verify:05-api/03-retrieval-api.md | API & Evaluation | failed | fable-5-1, <synthetic> | 09-22 20:32 | 2.8m | 28 | 22 | 744 | 832,236 | 1,591,080 | 6,088 | 2,430,148 |
| | **소계** | | | | | **10h 18m** | **3,426** | **2,691** | **101,936** | **113,587,748** | **529,611,865** | **2,143,870** | **645,445,419** |

#### 3단계 운영·개발·로드맵(ops-dev-roadmap) — `wf_18a2a477-09d` · 48 에이전트 · 실제 경과 시간 09-22 18:27 → 09-22 20:43 (2h 16m) · 에이전트 활동 시간 합산 8h 16m · 합계 378,103,047 토큰(출력 983,940)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:09-operations/01-deployment-guide.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:27 | 20.9m | 94 | 68 | 2,888 | 3,460,203 | 19,652,142 | 75,803 | 23,191,036 |
| 2 | write:11-roadmap/01-milestones.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:27 | 27.6m | 66 | 53 | 1,964 | 2,777,120 | 9,399,875 | 58,704 | 12,237,663 |
| 3 | write:10-development/01-repository-structure.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:27 | 12.0m | 57 | 47 | 1,704 | 3,785,446 | 4,874,223 | 16,628 | 8,678,001 |
| 4 | review-anchor:10-development/01-repository-structure.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:39 | 7.6m | 46 | 40 | 1,322 | 1,824,182 | 3,592,427 | 35,608 | 5,453,539 |
| 5 | review-tech:10-development/01-repository-structure.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:39 | 14.1m | 63 | 52 | 1,896 | 1,842,273 | 6,233,589 | 42,110 | 8,119,868 |
| 6 | review-tech:09-operations/01-deployment-guide.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:48 | 11.6m | 55 | 47 | 1,640 | 2,304,880 | 6,131,298 | 43,574 | 8,481,392 |
| 7 | review-anchor:09-operations/01-deployment-guide.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:48 | 8.6m | 46 | 39 | 1,322 | 1,963,470 | 5,947,530 | 40,014 | 7,952,336 |
| 8 | fix:10-development/01-repository-structure.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:53 | 9.6m | 98 | 82 | 3,046 | 1,309,322 | 12,931,555 | 33,014 | 14,276,937 |
| 9 | review-tech:11-roadmap/01-milestones.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 18:54 | 32.6m | 104 | 79 | 3,208 | 3,910,565 | 15,349,784 | 65,372 | 19,328,929 |
| 10 | review-anchor:11-roadmap/01-milestones.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 18:54 | 12.3m | 51 | 40 | 1,480 | 1,859,465 | 6,686,643 | 34,805 | 8,582,393 |
| 11 | fix:09-operations/01-deployment-guide.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 18:59 | 7.1m | 44 | 39 | 1,256 | 1,336,649 | 5,373,388 | 15,476 | 6,726,769 |
| 12 | verify:10-development/01-repository-structure.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 19:02 | 5.6m | 26 | 21 | 680 | 540,444 | 1,228,606 | 11,389 | 1,781,119 |
| 13 | fix:11-roadmap/01-milestones.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:27 | 15.2m | 92 | 71 | 2,628 | 1,349,333 | 13,234,780 | 49,052 | 14,635,793 |
| 14 | verify:11-roadmap/01-milestones.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:42 | 4.6m | 32 | 22 | 934 | 585,069 | 2,232,648 | 19,645 | 2,838,296 |
| 15 | write:09-operations/02-configuration-reference.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 34.0m | 115 | 95 | 3,530 | 7,453,018 | 20,139,788 | 52,860 | 27,649,196 |
| 16 | write:09-operations/03-observability.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 27.8m | 79 | 61 | 2,440 | 3,344,188 | 15,508,447 | 14,383 | 18,869,458 |
| 17 | write:09-operations/04-scaling-and-performance.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 21.0m | 98 | 79 | 3,016 | 4,528,190 | 21,467,533 | 47,639 | 26,046,378 |
| 18 | write:09-operations/05-security-and-compliance.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 28.0m | 69 | 58 | 2,120 | 4,586,071 | 11,734,875 | 13,889 | 16,336,955 |
| 19 | write:09-operations/06-runbooks.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 30.6m | 82 | 63 | 2,476 | 2,899,926 | 15,490,631 | 23,496 | 18,416,529 |
| 20 | write:09-operations/07-backup-and-disaster-recovery.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 19:47 | 18.6m | 96 | 79 | 2,952 | 4,152,020 | 15,527,431 | 35,555 | 19,717,958 |
| 21 | write:09-operations/08-upgrade-and-migration.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 20:05 | 20.1m | 75 | 58 | 2,280 | 4,528,900 | 13,460,641 | 42,128 | 18,033,949 |
| 22 | write:10-development/02-development-environment.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 20:08 | 18.5m | 72 | 44 | 2,214 | 3,198,085 | 11,882,408 | 66,670 | 15,149,377 |
| 23 | write:10-development/03-coding-standards.md | Ops, Dev, Roadmap | done | fable-5-1 | 09-22 20:15 | 18.2m | 86 | 61 | 2,632 | 4,221,917 | 13,090,746 | 75,149 | 17,390,444 |
| 24 | write:10-development/04-testing-strategy.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 20:15 | 27.8m | 77 | 60 | 2,284 | 3,757,665 | 10,397,460 | 9,446 | 14,166,855 |
| 25 | write:10-development/05-ci-cd.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 20:17 | 16.0m | 70 | 52 | 2,118 | 2,956,655 | 8,082,246 | 9,684 | 11,050,703 |
| 26 | write:10-development/06-plugin-development-guide.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 20:21 | 15.7m | 82 | 59 | 2,472 | 3,160,891 | 14,538,334 | 30,991 | 17,732,688 |
| 27 | write:10-development/07-contributing.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 20:25 | 15.3m | 52 | 36 | 1,512 | 1,491,640 | 4,788,874 | 12,429 | 6,294,455 |
| 28 | write:10-development/08-release-process.md | Ops, Dev, Roadmap | failed | fable-5-1, <synthetic> | 09-22 20:26 | 14.9m | 56 | 43 | 1,640 | 2,083,396 | 6,870,568 | 8,427 | 8,964,031 |
| 29 | write:11-roadmap/02-epics-and-backlog.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 30 | write:11-roadmap/03-risks-and-mitigations.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 31 | review-anchor:09-operations/07-backup-and-disaster-recove… | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 32 | review-tech:09-operations/07-backup-and-disaster-recovery… | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 33 | review-anchor:09-operations/04-scaling-and-performance.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 34 | review-tech:09-operations/04-scaling-and-performance.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 35 | review-anchor:09-operations/03-observability.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 36 | review-tech:09-operations/03-observability.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 37 | review-anchor:09-operations/05-security-and-compliance.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 38 | review-tech:09-operations/05-security-and-compliance.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 39 | review-anchor:09-operations/06-runbooks.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 40 | review-tech:09-operations/06-runbooks.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 41 | review-anchor:09-operations/02-configuration-reference.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 42 | review-tech:09-operations/02-configuration-reference.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 43 | review-anchor:09-operations/08-upgrade-and-migration.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 44 | review-tech:09-operations/08-upgrade-and-migration.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 45 | review-anchor:10-development/02-development-environment.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 46 | review-tech:10-development/02-development-environment.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:33 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 47 | review-anchor:10-development/03-coding-standards.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:35 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 48 | review-tech:10-development/03-coding-standards.md | Ops, Dev, Roadmap | failed | <synthetic> | 09-22 20:35 | 0.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| | **소계** | | | | | **8h 16m** | **2,003** | **1,548** | **59,654** | **81,210,983** | **295,848,470** | **983,940** | **378,103,047** |

#### 3단계 계약 감사(contracts-audit) — `wf_8890c66f-daf` · 60 에이전트 · 실제 경과 시간 09-22 18:35 → 09-22 20:16 (1h 41m) · 에이전트 활동 시간 합산 6h 25m · 합계 345,672,777 토큰(출력 1,401,621)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | contracts:validator:pre | Contract Audit | done | fable-5-1 | 09-22 18:35 | 9.3m | 55 | 31 | 1,670 | 648,933 | 4,237,449 | 39,689 | 4,927,741 |
| 2 | contracts:audit:ingest-chain | Contract Audit | done | fable-5-1 | 09-22 18:45 | 16.8m | 85 | 64 | 2,630 | 8,155,379 | 24,767,554 | 76,852 | 33,002,415 |
| 3 | contracts:audit:query-chain | Contract Audit | done | fable-5-1 | 09-22 18:45 | 18.1m | 87 | 71 | 2,694 | 6,839,269 | 23,171,457 | 82,375 | 30,095,795 |
| 4 | contracts:audit:ops-common | Contract Audit | done | fable-5-1 | 09-22 18:45 | 14.0m | 76 | 62 | 2,342 | 6,510,320 | 20,079,139 | 63,434 | 26,655,235 |
| 5 | contracts:fix:08-index-commit.md | Contract Audit | done | fable-5-1 | 09-22 19:03 | 14.7m | 81 | 70 | 2,502 | 770,154 | 11,593,921 | 45,766 | 12,412,343 |
| 6 | contracts:fix:06-enriched-chunk-set.md | Contract Audit | failed | fable-5-1, <synthetic> | 09-22 19:03 | 4.8m | 11 | 11 | 230 | 170,667 | 513,484 | 4,015 | 688,396 |
| 7 | contracts:fix:index-commit.schema.json | Contract Audit | failed | fable-5-1, <synthetic> | 09-22 19:03 | 3.5m | 40 | 27 | 1,128 | 740,614 | 2,525,976 | 9,683 | 3,277,401 |
| 8 | contracts:fix:05-chunk-set.md | Contract Audit | failed | fable-5-1, <synthetic> | 09-22 19:03 | 3.8m | 12 | 7 | 262 | 149,240 | 573,025 | 1,073 | 723,600 |
| 9 | contracts:fix:07-embedded-chunk-set-and-index-record.md | Contract Audit | failed | fable-5-1, <synthetic> | 09-22 19:03 | 5.9m | 14 | 8 | 326 | 182,840 | 956,901 | 10,687 | 1,150,754 |
| 10 | contracts:fix:04-normalized-document.md | Contract Audit | failed | fable-5-1, <synthetic> | 09-22 19:03 | 4.6m | 14 | 10 | 356 | 238,088 | 839,371 | 2,754 | 1,080,569 |
| 11 | contracts:fix:normalized-document.schema.json | Contract Audit | failed | <synthetic> | 09-22 19:06 | 3.1m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 12 | contracts:fix:index-record.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:07 | 6.5m | 69 | 53 | 2,088 | 429,376 | 6,550,896 | 23,819 | 7,006,179 |
| 13 | contracts:fix:common-types.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:07 | 10.3m | 40 | 21 | 1,190 | 211,562 | 3,192,718 | 37,578 | 3,443,048 |
| 14 | contracts:fix:parsed-document.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:08 | 3.7m | 28 | 13 | 776 | 202,362 | 1,481,961 | 12,598 | 1,697,697 |
| 15 | contracts:fix:source-document.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:09 | 3.7m | 43 | 30 | 1,256 | 318,099 | 2,651,232 | 15,288 | 2,985,875 |
| 16 | contracts:fix:00-contract-overview.md | Contract Audit | done | fable-5-1 | 09-22 19:09 | 8.9m | 60 | 45 | 1,830 | 756,483 | 7,156,793 | 34,848 | 7,949,954 |
| 17 | contracts:fix:02-source-document.md | Contract Audit | done | fable-5-1 | 09-22 19:11 | 7.3m | 26 | 14 | 772 | 193,261 | 2,568,256 | 28,721 | 2,791,010 |
| 18 | contracts:fix:09-query-request-and-query-plan.md | Contract Audit | done | fable-5-1 | 09-22 19:12 | 10.2m | 100 | 84 | 3,110 | 1,445,769 | 15,046,164 | 42,554 | 16,537,597 |
| 19 | contracts:fix:query-plan.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:13 | 5.4m | 49 | 37 | 1,508 | 471,333 | 4,220,481 | 25,730 | 4,719,052 |
| 20 | contracts:fix:11-context-pack.md | Contract Audit | done | fable-5-1 | 09-22 19:17 | 15.7m | 104 | 82 | 3,238 | 1,106,315 | 18,416,828 | 75,438 | 19,601,819 |
| 21 | contracts:fix:10-candidate-set-and-ranked-set.md | Contract Audit | running | fable-5-1 | 09-22 19:18 | 18.4m | 47 | 23 | 1,414 | 398,276 | 6,180,699 | 59,196 | 6,639,585 |
| 22 | contracts:fix:embedded-chunk-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:18 | 3.0m | 41 | 29 | 1,192 | 396,335 | 2,682,728 | 15,038 | 3,095,293 |
| 23 | contracts:fix:candidate-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:18 | 2.3m | 23 | 13 | 676 | 64,612 | 1,016,920 | 6,629 | 1,088,837 |
| 24 | contracts:fix:ranked-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:19 | 5.7m | 38 | 14 | 1,096 | 215,096 | 2,102,743 | 21,916 | 2,340,851 |
| 25 | contracts:fix:12-jobs-events-and-status.md | Contract Audit | done | fable-5-1 | 09-22 19:21 | 9.8m | 83 | 36 | 2,566 | 275,288 | 10,241,159 | 30,675 | 10,549,688 |
| 26 | contracts:fix:plugin-meta.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:21 | 4.3m | 35 | 20 | 1,000 | 213,316 | 1,725,080 | 18,924 | 1,958,320 |
| 27 | contracts:fix:16-eval-feedback-and-sidecar-contracts.md | Contract Audit | done | fable-5-1 | 09-22 19:23 | 12.9m | 55 | 39 | 1,670 | 581,355 | 5,142,603 | 52,822 | 5,778,450 |
| 28 | contracts:fix:13-error-model.md | Contract Audit | done | fable-5-1 | 09-22 19:24 | 5.7m | 28 | 14 | 836 | 157,104 | 1,857,425 | 21,021 | 2,036,386 |
| 29 | contracts:fix:00-design-bible.md | Contract Audit | done | fable-5-1 | 09-22 19:26 | 6.8m | 43 | 25 | 1,316 | 118,944 | 2,845,154 | 13,228 | 2,978,642 |
| 30 | contracts:fix:14-schema-versioning-and-compatibility.md | Contract Audit | done | fable-5-1 | 09-22 19:30 | 2.7m | 29 | 18 | 838 | 296,556 | 2,112,679 | 10,292 | 2,420,365 |
| 31 | contracts:fix:15-collection-profile-and-policy-contracts.… | Contract Audit | done | fable-5-1 | 09-22 19:31 | 10.2m | 89 | 72 | 2,758 | 1,165,357 | 12,382,533 | 44,893 | 13,595,541 |
| 32 | contracts:fix:10-candidate-set-and-ranked-set.md | Contract Audit | done | fable-5-1 | 09-22 19:36 | 11.5m | 99 | 79 | 3,078 | 1,480,794 | 14,769,283 | 55,291 | 16,308,446 |
| 33 | contracts:validator:post | Contract Audit | done | fable-5-1 | 09-22 19:48 | 3.9m | 32 | 16 | 934 | 284,092 | 1,536,018 | 13,947 | 1,834,991 |
| 34 | contracts:fix:index-commit.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:53 | 3.4m | 32 | 16 | 904 | 382,447 | 1,858,630 | 10,805 | 2,252,786 |
| 35 | contracts:fix:07-embedded-chunk-set-and-index-record.md | Contract Audit | done | fable-5-1 | 09-22 19:53 | 15.4m | 56 | 41 | 1,702 | 852,342 | 7,120,558 | 58,997 | 8,033,599 |
| 36 | contracts:fix:06-enriched-chunk-set.md | Contract Audit | done | fable-5-1 | 09-22 19:53 | 4.9m | 52 | 37 | 1,574 | 497,240 | 5,414,498 | 18,606 | 5,931,918 |
| 37 | contracts:fix:04-normalized-document.md | Contract Audit | done | fable-5-1 | 09-22 19:53 | 5.3m | 36 | 23 | 1,092 | 201,204 | 3,722,293 | 13,575 | 3,938,164 |
| 38 | contracts:fix:05-chunk-set.md | Contract Audit | done | fable-5-1 | 09-22 19:53 | 10.6m | 68 | 49 | 2,086 | 874,915 | 9,448,884 | 42,911 | 10,368,796 |
| 39 | contracts:fix:normalized-document.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:53 | 3.2m | 28 | 11 | 776 | 187,315 | 1,412,841 | 10,608 | 1,611,540 |
| 40 | contracts:fix:index-record.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:56 | 1.8m | 22 | 11 | 584 | 222,079 | 1,019,767 | 7,286 | 1,249,716 |
| 41 | contracts:fix:common-types.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:56 | 2.5m | 17 | 9 | 484 | 88,473 | 801,823 | 5,738 | 896,518 |
| 42 | contracts:fix:parsed-document.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:58 | 1.9m | 19 | 7 | 488 | 129,637 | 817,183 | 5,528 | 952,836 |
| 43 | contracts:fix:source-document.schema.json | Contract Audit | done | fable-5-1 | 09-22 19:58 | 1.2m | 15 | 6 | 360 | 134,302 | 582,796 | 3,201 | 720,659 |
| 44 | contracts:fix:00-contract-overview.md | Contract Audit | done | fable-5-1 | 09-22 19:58 | 11.3m | 72 | 50 | 2,214 | 811,696 | 8,209,230 | 31,245 | 9,054,385 |
| 45 | contracts:fix:02-source-document.md | Contract Audit | done | fable-5-1 | 09-22 19:59 | 6.7m | 65 | 23 | 1,990 | 256,016 | 6,016,166 | 29,342 | 6,303,514 |
| 46 | contracts:fix:09-query-request-and-query-plan.md | Contract Audit | done | fable-5-1 | 09-22 19:59 | 4.1m | 38 | 23 | 1,126 | 618,983 | 4,138,656 | 14,318 | 4,773,083 |
| 47 | contracts:fix:query-plan.schema.json | Contract Audit | done | fable-5-1 | 09-22 20:00 | 2.2m | 18 | 7 | 426 | 180,503 | 815,514 | 6,567 | 1,003,010 |
| 48 | contracts:fix:11-context-pack.md | Contract Audit | done | fable-5-1 | 09-22 20:02 | 7.6m | 52 | 28 | 1,574 | 602,609 | 6,441,546 | 26,785 | 7,072,514 |
| 49 | contracts:fix:10-candidate-set-and-ranked-set.md | Contract Audit | done | fable-5-1 | 09-22 20:03 | 5.7m | 57 | 34 | 1,734 | 722,088 | 7,120,637 | 21,121 | 7,865,580 |
| 50 | contracts:fix:embedded-chunk-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 20:03 | 1.6m | 16 | 5 | 422 | 96,848 | 626,804 | 6,111 | 730,185 |
| 51 | contracts:fix:candidate-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 20:05 | 1.8m | 18 | 7 | 516 | 97,037 | 791,987 | 5,049 | 894,589 |
| 52 | contracts:fix:ranked-set.schema.json | Contract Audit | done | fable-5-1 | 09-22 20:05 | 1.4m | 12 | 6 | 324 | 61,030 | 481,512 | 3,079 | 545,945 |
| 53 | contracts:fix:12-jobs-events-and-status.md | Contract Audit | done | fable-5-1 | 09-22 20:07 | 2.9m | 31 | 18 | 902 | 648,247 | 2,433,738 | 10,816 | 3,093,703 |
| 54 | contracts:fix:plugin-meta.schema.json | Contract Audit | done | fable-5-1 | 09-22 20:07 | 1.9m | 17 | 8 | 424 | 125,321 | 627,524 | 6,286 | 759,555 |
| 55 | contracts:fix:16-eval-feedback-and-sidecar-contracts.md | Contract Audit | done | fable-5-1 | 09-22 20:08 | 3.2m | 38 | 23 | 1,126 | 779,640 | 3,378,677 | 11,813 | 4,171,256 |
| 56 | contracts:fix:13-error-model.md | Contract Audit | done | fable-5-1 | 09-22 20:09 | 3.9m | 43 | 31 | 1,286 | 406,867 | 3,211,532 | 15,904 | 3,635,589 |
| 57 | contracts:fix:00-design-bible.md | Contract Audit | done | fable-5-1 | 09-22 20:09 | 3.3m | 20 | 10 | 580 | 110,215 | 1,004,641 | 9,876 | 1,125,312 |
| 58 | contracts:fix:14-schema-versioning-and-compatibility.md | Contract Audit | done | fable-5-1 | 09-22 20:09 | 2.3m | 23 | 10 | 646 | 177,060 | 1,758,557 | 6,665 | 1,942,928 |
| 59 | contracts:fix:15-collection-profile-and-policy-contracts.… | Contract Audit | done | fable-5-1 | 09-22 20:09 | 3.4m | 31 | 19 | 932 | 407,035 | 2,657,973 | 10,691 | 3,076,631 |
| 60 | contracts:validator:post | Contract Audit | done | fable-5-1 | 09-22 20:13 | 3.4m | 37 | 18 | 1,094 | 434,538 | 1,849,035 | 11,924 | 2,296,591 |
| | **소계** | | | | | **6h 25m** | **2,570** | **1,668** | **76,648** | **45,292,876** | **298,901,632** | **1,401,621** | **345,672,777** |

### 세션 1 (2026-09-18~22: 브리프, 1·1b·2단계)

오케스트레이터(메인 세션): 09-18 17:16 → 09-24 03:30 (130h 13m), API 호출 609, 도구 호출 286, 모델 fable-5-1, <synthetic>, 입력 14,266 / 캐시 쓰기 19,535,109 / 캐시 읽기 309,502,663 / 출력 2,067,746 / 합계 331,119,784

#### 1단계 기술 지형 리서치 — `wf_270deb6d-bba` · 72 에이전트 · 실제 경과 시간 09-18 17:31 → 09-22 10:45 (89h 14m, 중단 후 재개 구간 포함) · 에이전트 활동 시간 합산 19h 7m · 합계 828,319,835 토큰(출력 3,609,758)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | research:01-document-parsing-hwpx-hwp | Research | done | fable-5-1 | 09-18 17:31 | 15.3m | 95 | 74 | 2,920 | 1,302,760 | 5,587,144 | 23,807 | 6,916,631 |
| 2 | research:02-document-parsing-pdf-layout-ocr | Research | done | fable-5-1 | 09-18 17:31 | 21.7m | 114 | 86 | 3,528 | 1,680,855 | 8,648,043 | 75,729 | 10,408,155 |
| 3 | research:03-document-parsing-office-html-text | Research | done | fable-5-1 | 09-18 17:31 | 53.4m | 1015 | 998 | 32,390 | 6,484,569 | 50,058,605 | 126,286 | 56,701,850 |
| 4 | research:04-chunking-strategies-and-libraries | Research | done | fable-5-1 | 09-18 17:31 | 21.1m | 134 | 119 | 4,228 | 2,110,817 | 10,580,195 | 78,319 | 12,773,559 |
| 5 | research:06-vector-and-lexical-index-backends | Research | done | fable-5-1 | 09-18 17:31 | 19.1m | 123 | 101 | 3,846 | 2,332,277 | 7,923,608 | 23,031 | 10,282,762 |
| 6 | research:05-embedding-models-and-serving | Research | done | fable-5-1 | 09-18 17:31 | 17.8m | 98 | 79 | 3,016 | 1,573,060 | 6,279,929 | 70,070 | 7,926,075 |
| 7 | research:07-retrieval-techniques-fusion-reranking | Research | done | fable-5-1 | 09-18 17:46 | 15.7m | 97 | 75 | 2,984 | 1,268,030 | 5,147,238 | 61,297 | 6,479,549 |
| 8 | research:08-orchestration-messaging-and-api-frameworks | Research | done | fable-5-1 | 09-18 17:48 | 26.2m | 200 | 181 | 6,340 | 2,466,641 | 13,765,896 | 103,854 | 16,342,731 |
| 9 | research:09-evaluation-and-observability | Research | done | fable-5-1 | 09-18 17:50 | 23.8m | 164 | 139 | 5,128 | 2,471,748 | 10,951,420 | 99,305 | 13,527,601 |
| 10 | research:10-llm-context-optimization-and-mcp | Research | done | fable-5-1 | 09-18 17:52 | 18.8m | 105 | 78 | 3,240 | 3,222,667 | 11,750,906 | 75,630 | 15,052,443 |
| 11 | research:11-existing-rag-platforms-gap-analysis | Research | done | fable-5-1 | 09-18 17:52 | 25.5m | 216 | 196 | 6,822 | 3,894,983 | 12,762,457 | 95,653 | 16,759,915 |
| 12 | research:12-security-multitenancy-pii-and-licensing | Research | done | fable-5-1 | 09-18 18:02 | 23.6m | 163 | 138 | 5,096 | 2,367,633 | 10,181,382 | 54,905 | 12,609,016 |
| 13 | research:13-korean-nlp-tokenization-and-language-resources | Research | done | fable-5-1 | 09-18 18:11 | 24.8m | 138 | 117 | 4,326 | 2,638,943 | 9,861,407 | 49,708 | 12,554,384 |
| 14 | research:14-advanced-rag-graph-raptor-agentic-multimodal | Research | done | fable-5-1 | 09-18 18:14 | 18.9m | 130 | 103 | 4,040 | 2,005,287 | 7,944,563 | 35,185 | 9,989,075 |
| 15 | verify:01 | Verify | done | fable-5-1 | 09-18 18:15 | 13.2m | 105 | 91 | 3,240 | 1,402,893 | 8,242,196 | 50,328 | 9,698,657 |
| 16 | verify:05 | Verify | done | fable-5-1 | 09-18 18:18 | 12.7m | 102 | 88 | 3,144 | 1,889,255 | 7,962,669 | 53,028 | 9,908,096 |
| 17 | verify:06 | Verify | done | fable-5-1 | 09-18 18:24 | 11.9m | 118 | 104 | 3,656 | 1,994,978 | 9,873,741 | 47,954 | 11,920,329 |
| 18 | verify:04 | Verify | done | fable-5-1 | 09-18 18:25 | 14.8m | 148 | 133 | 4,616 | 2,441,064 | 13,200,372 | 46,734 | 15,692,786 |
| 19 | verify:02 | Verify | done | fable-5-1 | 09-18 18:28 | 16.0m | 141 | 125 | 4,392 | 2,527,278 | 13,001,061 | 64,864 | 15,597,595 |
| 20 | verify:07 | Verify | done | fable-5-1 | 09-18 18:31 | 13.3m | 117 | 105 | 3,624 | 1,939,949 | 9,548,132 | 55,357 | 11,547,062 |
| 21 | verify:10 | Verify | done | fable-5-1 | 09-18 18:33 | 11.1m | 80 | 65 | 2,350 | 2,952,817 | 11,613,012 | 45,848 | 14,614,027 |
| 22 | verify:09 | Verify | done | fable-5-1 | 09-18 18:35 | 22.9m | 95 | 72 | 2,920 | 1,418,331 | 10,696,379 | 66,469 | 12,184,099 |
| 23 | verify:08 | Verify | done | fable-5-1 | 09-18 18:36 | 14.1m | 108 | 92 | 3,336 | 1,767,264 | 10,488,026 | 58,312 | 12,316,938 |
| 24 | verify:11 | Verify | done | fable-5-1 | 09-18 18:40 | 21.3m | 128 | 108 | 3,976 | 1,336,232 | 11,126,795 | 53,401 | 12,520,404 |
| 25 | verify:03 | Verify | running | fable-5-1 | 09-18 18:44 | 18.2m | 177 | 165 | 5,544 | 4,180,855 | 15,442,689 | 56,699 | 19,685,787 |
| 26 | verify:12 | Verify | done | fable-5-1 | 09-18 18:44 | 17.4m | 149 | 132 | 4,588 | 2,471,369 | 14,574,488 | 54,672 | 17,105,117 |
| 27 | fix:01 | Fix | done | fable-5-1 | 09-18 18:44 | 14.6m | 101 | 76 | 3,112 | 923,360 | 9,653,133 | 61,260 | 10,640,865 |
| 28 | fix:05 | Fix | done | fable-5-1 | 09-18 18:50 | 13.3m | 80 | 62 | 2,470 | 896,906 | 7,509,042 | 25,293 | 8,433,711 |
| 29 | verify:14 | Verify | running | fable-5-1 | 09-18 18:58 | 16.5m | 89 | 102 | 2,728 | 1,597,776 | 7,846,881 | 38,868 | 9,486,253 |
| 30 | verify:13 | Verify | failed | fable-5-1, <synthetic> | 09-18 18:59 | 16.5m | 78 | 71 | 2,344 | 1,161,095 | 5,333,629 | 40,209 | 6,537,277 |
| 31 | fix:06 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:01 | 14.1m | 73 | 57 | 2,184 | 672,687 | 6,755,669 | 16,581 | 7,447,121 |
| 32 | fix:04 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:02 | 14.4m | 92 | 69 | 2,822 | 632,050 | 8,764,539 | 31,090 | 9,430,501 |
| 33 | verify:03 | Verify | done | fable-5-1 | 09-18 19:02 | 33.3m | 201 | 211 | 6,312 | 9,045,579 | 16,579,143 | 75,159 | 25,706,193 |
| 34 | fix:10 | Fix | done | fable-5-1 | 09-18 19:03 | 14.7m | 84 | 62 | 2,118 | 757,384 | 8,234,566 | 43,201 | 9,037,269 |
| 35 | verify:14 | Verify | failed | fable-5-1, <synthetic> | 09-18 19:15 | 22.1m | 116 | 107 | 3,560 | 2,100,028 | 9,357,554 | 33,410 | 11,494,552 |
| 36 | fix:07 | Fix | failed | <synthetic> | 09-18 19:15 | 3.1m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 37 | fix:02 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:16 | 20.0m | 61 | 41 | 1,800 | 395,176 | 5,328,948 | 42,669 | 5,768,593 |
| 38 | fix:08 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:16 | 21.7m | 90 | 67 | 2,758 | 720,586 | 9,749,954 | 36,406 | 10,509,704 |
| 39 | fix:09 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:18 | 21.6m | 106 | 89 | 3,240 | 897,330 | 10,149,874 | 59,920 | 11,110,364 |
| 40 | fix:12 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:18 | 7.0m | 27 | 16 | 712 | 255,507 | 1,912,918 | 7,703 | 2,176,840 |
| 41 | fix:11 | Fix | failed | fable-5-1, <synthetic> | 09-18 19:25 | 10.2m | 46 | 34 | 1,350 | 367,606 | 3,426,470 | 9,793 | 3,805,219 |
| 42 | fix:03 | Fix | failed | <synthetic> | 09-18 19:35 | 3.0m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 43 | synthesize:selection-matrix | Synthesize | failed | <synthetic> | 09-18 19:40 | 3.2m | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 44 | verify:02 | Verify | done | fable-5-1 | 09-22 09:15 | 12.7m | 143 | 129 | 4,426 | 3,447,251 | 13,079,879 | 48,535 | 16,580,091 |
| 45 | verify:04 | Verify | done | fable-5-1 | 09-22 09:15 | 16.3m | 143 | 125 | 4,456 | 2,861,393 | 14,378,806 | 74,576 | 17,319,231 |
| 46 | verify:03 | Verify | done | fable-5-1 | 09-22 09:15 | 14.5m | 164 | 148 | 5,098 | 2,998,489 | 15,438,393 | 63,251 | 18,505,231 |
| 47 | verify:05 | Verify | done | fable-5-1 | 09-22 09:15 | 13.7m | 118 | 107 | 3,626 | 2,216,471 | 11,771,099 | 63,266 | 14,054,462 |
| 48 | verify:07 | Verify | done | fable-5-1 | 09-22 09:15 | 11.4m | 92 | 78 | 2,794 | 1,799,976 | 7,151,702 | 49,993 | 9,004,465 |
| 49 | verify:06 | Verify | done | fable-5-1 | 09-22 09:15 | 12.7m | 123 | 111 | 3,816 | 2,826,512 | 10,884,769 | 55,887 | 13,770,984 |
| 50 | verify:08 | Verify | done | fable-5-1 | 09-22 09:27 | 11.6m | 87 | 75 | 2,664 | 2,549,413 | 8,056,911 | 51,155 | 10,660,143 |
| 51 | verify:09 | Verify | done | fable-5-1 | 09-22 09:28 | 15.6m | 125 | 104 | 3,850 | 1,664,418 | 14,039,380 | 62,424 | 15,770,072 |
| 52 | verify:10 | Verify | done | fable-5-1 | 09-22 09:28 | 11.2m | 93 | 81 | 2,856 | 4,592,003 | 10,620,079 | 49,900 | 15,264,838 |
| 53 | verify:11 | Verify | done | fable-5-1 | 09-22 09:29 | 16.3m | 154 | 134 | 4,808 | 2,427,222 | 15,898,699 | 66,126 | 18,396,855 |
| 54 | verify:12 | Verify | done | fable-5-1 | 09-22 09:30 | 12.8m | 112 | 98 | 3,464 | 2,260,871 | 10,140,309 | 54,783 | 12,459,427 |
| 55 | verify:13 | Verify | done | fable-5-1 | 09-22 09:32 | 14.0m | 124 | 102 | 3,818 | 1,983,173 | 11,992,099 | 57,879 | 14,036,969 |
| 56 | verify:14 | Verify | done | fable-5-1 | 09-22 09:38 | 8.5m | 110 | 104 | 3,430 | 2,241,236 | 8,471,088 | 33,672 | 10,749,426 |
| 57 | fix:01 | Fix | done | fable-5-1 | 09-22 09:39 | 4.3m | 25 | 15 | 740 | 188,794 | 1,766,094 | 16,020 | 1,971,648 |
| 58 | fix:07 | Fix | done | fable-5-1 | 09-22 09:43 | 10.9m | 23 | 17 | 676 | 375,110 | 1,453,371 | 52,269 | 1,881,426 |
| 59 | fix:02 | Fix | done | fable-5-1 | 09-22 09:43 | 10.7m | 74 | 59 | 2,248 | 690,019 | 6,671,460 | 52,203 | 7,415,930 |
| 60 | fix:06 | Fix | done | fable-5-1 | 09-22 09:43 | 10.7m | 108 | 95 | 3,396 | 600,086 | 10,780,714 | 46,484 | 11,430,680 |
| 61 | fix:05 | Fix | done | fable-5-1 | 09-22 09:45 | 18.2m | 95 | 80 | 2,980 | 851,530 | 10,032,780 | 72,263 | 10,959,553 |
| 62 | fix:03 | Fix | done | fable-5-1 | 09-22 09:46 | 16.0m | 81 | 70 | 2,472 | 547,888 | 8,038,005 | 53,982 | 8,642,347 |
| 63 | fix:04 | Fix | running | fable-5-1 | 09-22 09:47 | 11.8m | 80 | 69 | 2,470 | 583,722 | 6,935,270 | 29,320 | 7,550,782 |
| 64 | fix:08 | Fix | done | fable-5-1 | 09-22 09:54 | 16.9m | 108 | 98 | 3,426 | 1,031,950 | 11,725,523 | 54,380 | 12,815,279 |
| 65 | fix:10 | Fix | done | fable-5-1 | 09-22 09:54 | 13.9m | 83 | 73 | 2,626 | 507,493 | 8,644,262 | 48,905 | 9,203,286 |
| 66 | fix:12 | Fix | done | fable-5-1 | 09-22 09:54 | 14.4m | 73 | 64 | 2,306 | 530,291 | 7,095,691 | 39,693 | 7,667,981 |
| 67 | fix:04 | Fix | done | fable-5-1 | 09-22 09:59 | 6.8m | 38 | 31 | 1,156 | 246,407 | 3,260,634 | 26,336 | 3,534,533 |
| 68 | fix:09 | Fix | done | fable-5-1 | 09-22 10:02 | 16.6m | 125 | 107 | 3,880 | 945,422 | 15,338,708 | 75,822 | 16,363,832 |
| 69 | fix:11 | Fix | done | fable-5-1 | 09-22 10:03 | 14.6m | 122 | 94 | 3,814 | 856,302 | 12,929,403 | 63,372 | 13,852,891 |
| 70 | fix:13 | Fix | done | fable-5-1 | 09-22 10:05 | 11.7m | 84 | 68 | 2,598 | 693,805 | 9,131,644 | 37,997 | 9,866,044 |
| 71 | fix:14 | Fix | done | fable-5-1 | 09-22 10:08 | 13.9m | 38 | 26 | 1,096 | 772,455 | 3,118,520 | 18,286 | 3,910,357 |
| 72 | synthesize:selection-matrix | Synthesize | done | fable-5-1 | 09-22 10:22 | 22.5m | 47 | 37 | 1,444 | 1,525,330 | 10,412,221 | 42,972 | 11,981,967 |
| | **소계** | | | | | **19h 7m** | **8,299** | **7,227** | **257,234** | **127,380,657** | **697,072,186** | **3,609,758** | **828,319,835** |

#### 1b단계 비전·요구사항 — `wf_3115816b-af8` · 24 에이전트 · 실제 경과 시간 09-18 17:32 → 09-18 19:00 (1h 28m) · 에이전트 활동 시간 합산 6h 33m · 합계 140,416,496 토큰(출력 1,005,681)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:00-vision/01-vision-and-goals.md | Write | done | fable-5-1 | 09-18 17:32 | 9.5m | 19 | 9 | 518 | 262,361 | 854,401 | 39,338 | 1,156,618 |
| 2 | write:00-vision/03-glossary.md | Write | done | fable-5-1 | 09-18 17:32 | 24.0m | 24 | 11 | 622 | 256,445 | 1,960,099 | 47,856 | 2,265,022 |
| 3 | write:00-vision/02-design-principles.md | Write | done | fable-5-1 | 09-18 17:32 | 13.3m | 21 | 8 | 582 | 281,250 | 1,144,566 | 54,488 | 1,480,886 |
| 4 | write:01-requirements/02-non-functional-requirements.md | Write | done | fable-5-1 | 09-18 17:32 | 13.4m | 14 | 6 | 328 | 292,556 | 607,294 | 6,181 | 906,359 |
| 5 | write:00-vision/04-scope-and-non-goals.md | Write | done | fable-5-1 | 09-18 17:32 | 13.6m | 25 | 9 | 710 | 277,416 | 1,518,118 | 7,129 | 1,803,373 |
| 6 | write:01-requirements/01-functional-requirements.md | Write | done | fable-5-1 | 09-18 17:32 | 25.6m | 28 | 16 | 716 | 196,671 | 1,536,396 | 51,980 | 1,785,763 |
| 7 | write:01-requirements/03-personas-and-use-cases.md | Write | done | fable-5-1 | 09-18 17:42 | 28.3m | 42 | 15 | 1,134 | 412,270 | 2,803,135 | 32,372 | 3,248,911 |
| 8 | write:01-requirements/04-user-stories-and-acceptance-crit… | Write | done | fable-5-1 | 09-18 17:46 | 43.7m | 92 | 34 | 2,614 | 808,613 | 11,973,273 | 92,512 | 12,877,012 |
| 9 | review:00-vision/01-vision-and-goals.md | Review | done | fable-5-1 | 09-18 17:46 | 7.5m | 13 | 7 | 296 | 246,684 | 563,364 | 32,245 | 842,589 |
| 10 | review:00-vision/02-design-principles.md | Review | done | fable-5-1 | 09-18 17:46 | 7.4m | 24 | 14 | 648 | 363,787 | 1,624,499 | 30,653 | 2,019,587 |
| 11 | review:01-requirements/02-non-functional-requirements.md | Review | done | fable-5-1 | 09-18 17:53 | 9.3m | 21 | 11 | 552 | 324,888 | 1,397,951 | 39,306 | 1,762,697 |
| 12 | review:00-vision/04-scope-and-non-goals.md | Review | done | fable-5-1 | 09-18 17:53 | 7.4m | 18 | 8 | 456 | 216,349 | 1,128,420 | 30,548 | 1,375,773 |
| 13 | fix:00-vision/01-vision-and-goals.md | Fix | done | fable-5-1 | 09-18 17:57 | 13.5m | 36 | 20 | 1,032 | 1,373,875 | 2,785,833 | 23,194 | 4,183,934 |
| 14 | fix:00-vision/02-design-principles.md | Fix | done | fable-5-1 | 09-18 17:58 | 14.6m | 102 | 84 | 3,144 | 969,245 | 12,099,805 | 27,143 | 13,099,337 |
| 15 | review:00-vision/03-glossary.md | Review | done | fable-5-1 | 09-18 18:01 | 7.5m | 11 | 5 | 232 | 389,121 | 365,525 | 32,834 | 787,712 |
| 16 | review:01-requirements/01-functional-requirements.md | Review | done | fable-5-1 | 09-18 18:03 | 8.3m | 24 | 12 | 648 | 198,754 | 1,733,455 | 35,407 | 1,968,264 |
| 17 | fix:00-vision/04-scope-and-non-goals.md | Fix | done | fable-5-1 | 09-18 18:08 | 17.0m | 31 | 15 | 902 | 892,390 | 2,437,351 | 14,951 | 3,345,594 |
| 18 | fix:01-requirements/02-non-functional-requirements.md | Fix | done | fable-5-1 | 09-18 18:10 | 33.2m | 49 | 32 | 1,392 | 823,009 | 6,848,948 | 99,179 | 7,772,528 |
| 19 | fix:00-vision/03-glossary.md | Fix | done | fable-5-1 | 09-18 18:10 | 15.3m | 101 | 74 | 3,142 | 472,082 | 11,853,397 | 35,913 | 12,364,534 |
| 20 | review:01-requirements/03-personas-and-use-cases.md | Review | done | fable-5-1 | 09-18 18:11 | 8.2m | 24 | 17 | 648 | 554,180 | 1,748,518 | 35,086 | 2,338,432 |
| 21 | fix:01-requirements/01-functional-requirements.md | Fix | done | fable-5-1 | 09-18 18:13 | 16.4m | 100 | 72 | 3,080 | 1,870,585 | 11,149,321 | 70,143 | 13,093,129 |
| 22 | fix:01-requirements/03-personas-and-use-cases.md | Fix | done | fable-5-1 | 09-18 18:19 | 25.3m | 105 | 87 | 3,180 | 1,547,683 | 17,783,496 | 61,769 | 19,396,128 |
| 23 | review:01-requirements/04-user-stories-and-acceptance-cri… | Review | done | fable-5-1 | 09-18 18:30 | 9.2m | 37 | 20 | 1,064 | 680,707 | 2,864,998 | 32,779 | 3,579,548 |
| 24 | fix:01-requirements/04-user-stories-and-acceptance-criter… | Fix | done | fable-5-1 | 09-18 18:39 | 21.5m | 117 | 91 | 3,354 | 1,040,896 | 25,845,841 | 72,675 | 26,962,766 |
| | **소계** | | | | | **6h 33m** | **1,078** | **677** | **30,994** | **14,751,817** | **124,628,004** | **1,005,681** | **140,416,496** |

#### 2단계 설계 경쟁·바이블 — `wf_97157829-22c` · 11 에이전트 · 실제 경과 시간 09-22 10:45 → 09-22 13:01 (2h 15m) · 에이전트 활동 시간 합산 3h 24m · 합계 109,974,362 토큰(출력 698,183)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | propose:A | Propose | done | fable-5-1 | 09-22 10:45 | 17.9m | 32 | 23 | 904 | 1,474,010 | 3,163,060 | 74,072 | 4,712,046 |
| 2 | propose:B | Propose | done | fable-5-1 | 09-22 10:45 | 23.6m | 61 | 42 | 1,832 | 1,422,438 | 13,050,518 | 100,549 | 14,575,337 |
| 3 | propose:C | Propose | done | fable-5-1 | 09-22 10:45 | 30.1m | 41 | 31 | 1,132 | 1,614,616 | 5,442,697 | 60,290 | 7,118,735 |
| 4 | judge:1 | Judge | done | fable-5-1 | 09-22 11:16 | 8.2m | 32 | 22 | 904 | 1,286,585 | 3,129,169 | 36,272 | 4,452,930 |
| 5 | judge:2 | Judge | done | fable-5-1 | 09-22 11:16 | 7.4m | 30 | 21 | 840 | 1,162,830 | 2,834,811 | 29,879 | 4,028,360 |
| 6 | judge:3 | Judge | done | fable-5-1 | 09-22 11:16 | 5.6m | 30 | 20 | 840 | 1,344,120 | 2,920,907 | 23,082 | 4,288,949 |
| 7 | synthesize:design-bible | Synthesize | done | fable-5-1 | 09-22 11:24 | 43.4m | 94 | 71 | 2,860 | 8,111,929 | 26,149,773 | 90,611 | 34,355,173 |
| 8 | review:1 | Review | done | fable-5-1 | 09-22 12:07 | 9.7m | 21 | 14 | 552 | 834,182 | 1,453,609 | 42,843 | 2,331,186 |
| 9 | review:2 | Review | done | fable-5-1 | 09-22 12:07 | 7.7m | 28 | 20 | 746 | 940,885 | 2,790,270 | 32,545 | 3,764,446 |
| 10 | review:3 | Review | done | fable-5-1 | 09-22 12:07 | 6.6m | 37 | 25 | 1,034 | 1,632,582 | 3,681,981 | 26,718 | 5,342,315 |
| 11 | fix:design-bible | Review | done | fable-5-1 | 09-22 12:17 | 43.6m | 94 | 54 | 2,918 | 1,799,082 | 23,021,563 | 181,322 | 25,004,885 |
| | **소계** | | | | | **3h 24m** | **500** | **343** | **14,562** | **21,623,259** | **87,638,358** | **698,183** | **109,974,362** |

#### wf_94f7a864-1a2 — `wf_94f7a864-1a2` · 6 에이전트 · 실제 경과 시간 09-23 09:22 → 09-23 09:30 (7.5m) · 에이전트 활동 시간 합산 44.8m · 합계 57,754,444 토큰(출력 79,834)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | adr:list | ADRs | running | fable-5-1 | 09-23 09:22 | 7.5m | 31 | 20 | 902 | 790,978 | 1,976,382 | 4,566 | 2,772,828 |
| 2 | write:05-api/02-ingestion-api.md | Finish: write missing | running | fable-5-1 | 09-23 09:22 | 7.5m | 56 | 41 | 1,672 | 1,767,678 | 7,841,012 | 14,625 | 9,624,987 |
| 3 | write:05-api/04-management-api.md | Finish: write missing | running | fable-5-1 | 09-23 09:22 | 7.4m | 95 | 84 | 2,920 | 3,707,094 | 15,179,915 | 17,560 | 18,907,489 |
| 4 | write:05-api/05-mcp-server.md | Finish: write missing | running | fable-5-1 | 09-23 09:22 | 7.4m | 69 | 53 | 2,118 | 2,444,793 | 7,714,344 | 24,817 | 10,186,072 |
| 5 | write:11-roadmap/02-epics-and-backlog.md | Finish: write missing | running | fable-5-1 | 09-23 09:22 | 7.4m | 37 | 27 | 1,064 | 1,852,814 | 3,228,285 | 5,652 | 5,087,815 |
| 6 | write:10-development/05-ci-cd.md | Finish: write missing | running | fable-5-1 | 09-23 09:22 | 7.4m | 78 | 65 | 2,376 | 2,815,595 | 8,344,668 | 12,614 | 11,175,253 |
| | **소계** | | | | | **44.8m** | **366** | **290** | **11,052** | **13,378,952** | **44,284,606** | **79,834** | **57,754,444** |

#### wf_7b7b22c8-830 — `wf_7b7b22c8-830` · 84 에이전트 · 실제 경과 시간 09-23 09:37 → 09-23 12:30 (2h 52m) · 에이전트 활동 시간 합산 9h 40m · 합계 363,725,694 토큰(출력 2,061,455)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:05-api/02-ingestion-api.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 17.3m | 89 | 58 | 2,728 | 2,672,692 | 13,577,157 | 77,624 | 16,330,201 |
| 2 | write:05-api/04-management-api.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 17.0m | 73 | 58 | 2,216 | 2,560,578 | 10,286,120 | 78,766 | 12,927,680 |
| 3 | write:05-api/05-mcp-server.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 22.5m | 104 | 85 | 3,208 | 3,372,081 | 18,476,181 | 106,085 | 21,957,555 |
| 4 | write:10-development/05-ci-cd.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 31.1m | 121 | 98 | 3,724 | 3,683,870 | 21,840,767 | 81,457 | 25,609,818 |
| 5 | write:11-roadmap/02-epics-and-backlog.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 41.3m | 70 | 36 | 2,030 | 2,170,559 | 12,546,694 | 189,182 | 14,908,465 |
| 6 | write:11-roadmap/03-risks-and-mitigations.md | Finish: write missing | done | fable-5-1 | 09-23 09:37 | 29.3m | 45 | 30 | 1,292 | 1,235,489 | 5,598,491 | 64,049 | 6,899,321 |
| 7 | review:05-api/01-api-design-guidelines.md | Finish: review cycle | done | fable-5-1 | 09-23 09:54 | 3.0m | 21 | 16 | 612 | 477,442 | 1,161,416 | 11,087 | 1,650,557 |
| 8 | review:05-api/03-retrieval-api.md | Finish: review cycle | done | fable-5-1 | 09-23 09:55 | 3.7m | 24 | 19 | 708 | 354,270 | 1,592,615 | 13,858 | 1,961,451 |
| 9 | review:04-pipelines/02-fetching-and-source-resolution.md | Finish: review cycle | done | fable-5-1 | 09-23 09:57 | 2.8m | 23 | 19 | 646 | 533,988 | 1,391,773 | 10,650 | 1,937,057 |
| 10 | review:04-pipelines/03-parsing-router-and-format-detectio… | Finish: review cycle | done | fable-5-1 | 09-23 09:58 | 2.7m | 17 | 12 | 454 | 312,346 | 1,036,535 | 9,728 | 1,359,063 |
| 11 | review:04-pipelines/04-parser-hwpx-and-hwp.md | Finish: review cycle | done | fable-5-1 | 09-23 10:00 | 3.0m | 19 | 14 | 548 | 334,824 | 1,265,394 | 9,720 | 1,610,486 |
| 12 | review:04-pipelines/05-parser-pdf.md | Finish: review cycle | done | fable-5-1 | 09-23 10:00 | 3.6m | 21 | 16 | 612 | 467,420 | 1,178,327 | 12,058 | 1,658,417 |
| 13 | review:04-pipelines/06-parser-doc-and-docx.md | Finish: review cycle | done | fable-5-1 | 09-23 10:01 | 3.2m | 24 | 18 | 618 | 641,892 | 1,403,692 | 12,074 | 2,058,276 |
| 14 | review:04-pipelines/07-parser-html.md | Finish: review cycle | done | fable-5-1 | 09-23 10:03 | 4.5m | 31 | 23 | 932 | 556,978 | 2,359,829 | 16,034 | 2,933,773 |
| 15 | review:04-pipelines/08-parser-txt-md-and-others.md | Finish: review cycle | done | fable-5-1 | 09-23 10:04 | 4.3m | 33 | 27 | 996 | 609,471 | 2,421,715 | 15,594 | 3,047,776 |
| 16 | review:04-pipelines/09-normalization-and-cleaning.md | Finish: review cycle | done | fable-5-1 | 09-23 10:04 | 4.3m | 27 | 20 | 804 | 455,815 | 1,895,134 | 15,760 | 2,367,513 |
| 17 | review:04-pipelines/10-chunking-strategies.md | Finish: review cycle | done | fable-5-1 | 09-23 10:07 | 4.9m | 30 | 18 | 900 | 201,934 | 2,880,507 | 11,235 | 3,094,576 |
| 18 | review:04-pipelines/11-enrichment.md | Finish: review cycle | done | fable-5-1 | 09-23 10:07 | 3.0m | 13 | 9 | 356 | 176,445 | 793,392 | 9,717 | 979,910 |
| 19 | review:08-evaluation/02-retrieval-metrics-and-harness.md | Finish: review cycle | done | fable-5-1 | 09-23 10:08 | 4.1m | 27 | 20 | 744 | 437,766 | 1,928,193 | 13,196 | 2,379,899 |
| 20 | review:08-evaluation/03-golden-dataset-construction.md | Finish: review cycle | done | fable-5-1 | 09-23 10:08 | 3.8m | 27 | 21 | 804 | 503,356 | 1,901,389 | 13,244 | 2,418,793 |
| 21 | review:08-evaluation/04-llm-judge-and-generation-quality.… | Finish: review cycle | done | fable-5-1 | 09-23 10:09 | 4.3m | 21 | 12 | 612 | 141,624 | 1,596,867 | 12,546 | 1,751,649 |
| 22 | review:08-evaluation/05-benchmark-plan-and-baselines.md | Finish: review cycle | done | fable-5-1 | 09-23 10:11 | 5.9m | 28 | 21 | 806 | 401,875 | 2,065,133 | 17,605 | 2,485,419 |
| 23 | review:09-operations/01-deployment-guide.md | Finish: review cycle | done | fable-5-1 | 09-23 10:12 | 5.5m | 27 | 20 | 804 | 529,458 | 2,107,012 | 16,055 | 2,653,329 |
| 24 | review:09-operations/02-configuration-reference.md | Finish: review cycle | done | fable-5-1 | 09-23 10:12 | 9.9m | 43 | 31 | 1,316 | 473,877 | 4,033,185 | 21,232 | 4,529,610 |
| 25 | review:09-operations/03-observability.md | Finish: review cycle | done | fable-5-1 | 09-23 10:12 | 7.3m | 28 | 17 | 836 | 180,176 | 2,276,849 | 15,407 | 2,473,268 |
| 26 | review:09-operations/04-scaling-and-performance.md | Finish: review cycle | done | fable-5-1 | 09-23 10:13 | 5.5m | 20 | 12 | 580 | 144,134 | 1,407,703 | 9,822 | 1,562,239 |
| 27 | review:09-operations/05-security-and-compliance.md | Finish: review cycle | done | fable-5-1 | 09-23 10:16 | 8.1m | 30 | 21 | 900 | 532,284 | 2,412,791 | 17,775 | 2,963,750 |
| 28 | review:09-operations/06-runbooks.md | Finish: review cycle | done | fable-5-1 | 09-23 10:17 | 7.5m | 28 | 18 | 776 | 162,489 | 1,867,102 | 14,520 | 2,044,887 |
| 29 | review:09-operations/07-backup-and-disaster-recovery.md | Finish: review cycle | done | fable-5-1 | 09-23 10:19 | 2.6m | 21 | 18 | 582 | 666,404 | 1,074,966 | 8,363 | 1,750,315 |
| 30 | review:09-operations/08-upgrade-and-migration.md | Finish: review cycle | done | fable-5-1 | 09-23 10:19 | 5.7m | 24 | 14 | 708 | 190,980 | 1,885,534 | 12,866 | 2,090,088 |
| 31 | review:10-development/01-repository-structure.md | Finish: review cycle | done | fable-5-1 | 09-23 10:20 | 4.9m | 23 | 14 | 676 | 124,970 | 1,547,480 | 11,431 | 1,684,557 |
| 32 | review:10-development/02-development-environment.md | Finish: review cycle | done | fable-5-1 | 09-23 10:21 | 4.5m | 21 | 15 | 582 | 328,996 | 1,358,998 | 10,214 | 1,698,790 |
| 33 | review:10-development/03-coding-standards.md | Finish: review cycle | done | fable-5-1 | 09-23 10:22 | 5.3m | 23 | 15 | 676 | 149,657 | 1,549,319 | 12,269 | 1,711,921 |
| 34 | review:10-development/04-testing-strategy.md | Finish: review cycle | done | fable-5-1 | 09-23 10:24 | 5.4m | 22 | 17 | 614 | 358,744 | 1,403,864 | 10,497 | 1,773,719 |
| 35 | review:10-development/06-plugin-development-guide.md | Finish: review cycle | done | fable-5-1 | 09-23 10:25 | 5.2m | 26 | 16 | 772 | 171,573 | 2,059,026 | 11,681 | 2,243,052 |
| 36 | review:10-development/07-contributing.md | Finish: review cycle | done | fable-5-1 | 09-23 10:25 | 2.8m | 16 | 11 | 422 | 236,489 | 877,309 | 8,867 | 1,123,087 |
| 37 | review:10-development/08-release-process.md | Finish: review cycle | done | fable-5-1 | 09-23 10:25 | 6.0m | 23 | 14 | 676 | 176,924 | 1,707,233 | 14,984 | 1,899,817 |
| 38 | review:05-api/04-management-api.md | Finish: write missing | done | fable-5-1 | 09-23 10:26 | 6.2m | 28 | 17 | 836 | 165,830 | 2,258,286 | 13,869 | 2,438,821 |
| 39 | review:05-api/02-ingestion-api.md | Finish: write missing | done | fable-5-1 | 09-23 10:27 | 4.2m | 34 | 28 | 998 | 519,236 | 2,503,234 | 14,122 | 3,037,590 |
| 40 | fix:05-api/01-api-design-guidelines.md | Finish: review cycle | done | fable-5-1 | 09-23 10:28 | 5.2m | 58 | 48 | 1,706 | 982,019 | 6,245,707 | 23,170 | 7,252,602 |
| 41 | fix:05-api/03-retrieval-api.md | Finish: review cycle | done | fable-5-1 | 09-23 10:30 | 1.8m | 26 | 15 | 742 | 296,946 | 1,659,768 | 6,616 | 1,964,072 |
| 42 | review:05-api/05-mcp-server.md | Finish: write missing | done | fable-5-1 | 09-23 10:30 | 3.3m | 36 | 29 | 1,032 | 572,705 | 2,841,959 | 13,164 | 3,428,860 |
| 43 | fix:04-pipelines/02-fetching-and-source-resolution.md | Finish: review cycle | done | fable-5-1 | 09-23 10:31 | 5.6m | 50 | 37 | 1,510 | 492,368 | 4,028,475 | 21,634 | 4,543,987 |
| 44 | fix:04-pipelines/03-parsing-router-and-format-detection.md | Finish: review cycle | done | fable-5-1 | 09-23 10:32 | 2.4m | 29 | 19 | 808 | 306,765 | 1,964,649 | 10,622 | 2,282,844 |
| 45 | fix:04-pipelines/04-parser-hwpx-and-hwp.md | Finish: review cycle | done | fable-5-1 | 09-23 10:32 | 5.5m | 48 | 31 | 1,446 | 571,696 | 4,413,800 | 32,001 | 5,018,943 |
| 46 | fix:04-pipelines/05-parser-pdf.md | Finish: review cycle | done | fable-5-1 | 09-23 10:32 | 4.1m | 40 | 28 | 1,190 | 391,471 | 2,861,407 | 19,397 | 3,273,465 |
| 47 | fix:04-pipelines/06-parser-doc-and-docx.md | Finish: review cycle | done | fable-5-1 | 09-23 10:33 | 3.2m | 32 | 18 | 934 | 293,341 | 2,154,778 | 15,543 | 2,464,596 |
| 48 | review:11-roadmap/03-risks-and-mitigations.md | Finish: write missing | done | fable-5-1 | 09-23 10:33 | 3.1m | 17 | 13 | 454 | 329,007 | 810,155 | 9,095 | 1,148,711 |
| 49 | fix:04-pipelines/07-parser-html.md | Finish: review cycle | done | fable-5-1 | 09-23 10:34 | 8.3m | 41 | 20 | 1,192 | 388,602 | 3,718,252 | 48,155 | 4,156,201 |
| 50 | fix:04-pipelines/08-parser-txt-md-and-others.md | Finish: review cycle | done | fable-5-1 | 09-23 10:36 | 3.8m | 43 | 32 | 1,286 | 591,503 | 3,366,387 | 16,569 | 3,975,745 |
| 51 | review:10-development/05-ci-cd.md | Finish: write missing | done | fable-5-1 | 09-23 10:36 | 3.7m | 27 | 20 | 804 | 450,111 | 1,846,053 | 12,539 | 2,309,507 |
| 52 | fix:04-pipelines/09-normalization-and-cleaning.md | Finish: review cycle | done | fable-5-1 | 09-23 10:36 | 2.8m | 29 | 22 | 868 | 277,028 | 2,123,381 | 10,704 | 2,411,981 |
| 53 | fix:04-pipelines/11-enrichment.md | Finish: review cycle | done | fable-5-1 | 09-23 10:36 | 4.6m | 37 | 19 | 1,094 | 177,792 | 2,830,375 | 19,069 | 3,028,330 |
| 54 | fix:04-pipelines/10-chunking-strategies.md | Finish: review cycle | done | fable-5-1 | 09-23 10:37 | 2.2m | 17 | 10 | 484 | 112,807 | 988,824 | 6,403 | 1,108,518 |
| 55 | fix:08-evaluation/03-golden-dataset-construction.md | Finish: review cycle | done | fable-5-1 | 09-23 10:39 | 2.5m | 26 | 18 | 772 | 221,622 | 1,601,963 | 8,510 | 1,832,867 |
| 56 | fix:08-evaluation/02-retrieval-metrics-and-harness.md | Finish: review cycle | done | fable-5-1 | 09-23 10:39 | 2.5m | 29 | 20 | 838 | 345,540 | 1,852,288 | 9,253 | 2,207,919 |
| 57 | fix:08-evaluation/04-llm-judge-and-generation-quality.md | Finish: review cycle | done | fable-5-1 | 09-23 10:40 | 7.1m | 57 | 46 | 1,704 | 704,371 | 5,501,681 | 35,902 | 6,243,658 |
| 58 | fix:08-evaluation/05-benchmark-plan-and-baselines.md | Finish: review cycle | done | fable-5-1 | 09-23 10:40 | 9.1m | 26 | 17 | 772 | 323,703 | 2,413,592 | 40,943 | 2,779,010 |
| 59 | fix:09-operations/01-deployment-guide.md | Finish: review cycle | done | fable-5-1 | 09-23 10:41 | 3.3m | 28 | 22 | 836 | 341,371 | 1,901,092 | 12,866 | 2,256,165 |
| 60 | fix:09-operations/04-scaling-and-performance.md | Finish: review cycle | done | fable-5-1 | 09-23 10:42 | 2.2m | 28 | 16 | 776 | 465,722 | 1,932,589 | 8,627 | 2,407,714 |
| 61 | review:11-roadmap/02-epics-and-backlog.md | Finish: write missing | done | fable-5-1 | 09-23 10:42 | 6.0m | 37 | 28 | 1,124 | 933,681 | 3,475,513 | 23,575 | 4,433,893 |
| 62 | fix:09-operations/03-observability.md | Finish: review cycle | done | fable-5-1 | 09-23 10:42 | 4.3m | 45 | 39 | 1,350 | 358,481 | 4,572,359 | 19,276 | 4,951,466 |
| 63 | fix:09-operations/07-backup-and-disaster-recovery.md | Finish: review cycle | done | fable-5-1 | 09-23 10:44 | 2.5m | 32 | 24 | 874 | 907,489 | 1,933,051 | 11,268 | 2,852,682 |
| 64 | fix:09-operations/02-configuration-reference.md | Finish: review cycle | done | fable-5-1 | 09-23 10:44 | 10.6m | 67 | 50 | 2,024 | 1,082,352 | 8,883,625 | 38,437 | 10,006,438 |
| 65 | fix:09-operations/08-upgrade-and-migration.md | Finish: review cycle | done | fable-5-1 | 09-23 10:47 | 4.8m | 43 | 35 | 1,316 | 471,283 | 3,923,511 | 22,191 | 4,418,301 |
| 66 | fix:09-operations/05-security-and-compliance.md | Finish: review cycle | done | fable-5-1 | 09-23 10:47 | 2.0m | 26 | 16 | 742 | 325,368 | 1,474,701 | 7,380 | 1,808,191 |
| 67 | fix:10-development/01-repository-structure.md | Finish: review cycle | done | fable-5-1 | 09-23 10:47 | 1.5m | 15 | 11 | 420 | 137,287 | 805,529 | 5,061 | 948,297 |
| 68 | fix:09-operations/06-runbooks.md | Finish: review cycle | done | fable-5-1 | 09-23 10:48 | 4.0m | 43 | 36 | 1,316 | 436,591 | 3,226,964 | 19,608 | 3,684,479 |
| 69 | fix:10-development/02-development-environment.md | Finish: review cycle | done | fable-5-1 | 09-23 10:49 | 2.2m | 34 | 19 | 968 | 310,528 | 2,098,033 | 8,926 | 2,418,455 |
| 70 | fix:10-development/07-contributing.md | Finish: review cycle | done | fable-5-1 | 09-23 10:49 | 5.3m | 46 | 37 | 1,352 | 683,322 | 4,717,192 | 23,971 | 5,425,837 |
| 71 | fix:10-development/03-coding-standards.md | Finish: review cycle | done | fable-5-1 | 09-23 10:49 | 3.0m | 34 | 27 | 1,028 | 354,301 | 2,472,724 | 12,242 | 2,840,295 |
| 72 | fix:10-development/06-plugin-development-guide.md | Finish: review cycle | done | fable-5-1 | 09-23 10:51 | 7.0m | 51 | 28 | 1,542 | 181,138 | 4,161,434 | 22,924 | 4,367,038 |
| 73 | fix:10-development/04-testing-strategy.md | Finish: review cycle | done | fable-5-1 | 09-23 10:51 | 4.8m | 36 | 25 | 1,062 | 218,801 | 2,497,802 | 19,310 | 2,736,975 |
| 74 | fix:10-development/08-release-process.md | Finish: review cycle | done | fable-5-1 | 09-23 10:52 | 4.4m | 51 | 37 | 1,542 | 412,981 | 3,868,884 | 17,657 | 4,301,064 |
| 75 | fix:05-api/02-ingestion-api.md | Finish: write missing | done | fable-5-1 | 09-23 10:52 | 3.2m | 45 | 32 | 1,350 | 430,973 | 3,518,212 | 14,470 | 3,965,005 |
| 76 | fix:05-api/04-management-api.md | Finish: write missing | done | fable-5-1 | 09-23 10:54 | 3.8m | 24 | 17 | 708 | 117,834 | 1,814,297 | 12,061 | 1,944,900 |
| 77 | fix:05-api/05-mcp-server.md | Finish: write missing | done | fable-5-1 | 09-23 10:55 | 3.5m | 45 | 33 | 1,350 | 511,908 | 3,889,360 | 14,024 | 4,416,642 |
| 78 | fix:11-roadmap/03-risks-and-mitigations.md | Finish: write missing | done | fable-5-1 | 09-23 10:55 | 4.7m | 46 | 32 | 1,352 | 457,852 | 4,186,611 | 20,818 | 4,666,633 |
| 79 | fix:10-development/05-ci-cd.md | Finish: write missing | done | fable-5-1 | 09-23 10:56 | 6.4m | 66 | 46 | 1,962 | 756,313 | 7,352,096 | 26,858 | 8,137,229 |
| 80 | fix:11-roadmap/02-epics-and-backlog.md | Finish: write missing | done | fable-5-1 | 09-23 10:56 | 6.3m | 63 | 41 | 1,926 | 965,947 | 7,843,803 | 23,651 | 8,835,327 |
| 81 | openapi:assemble | OpenAPI | done | fable-5-1 | 09-23 11:03 | 41.8m | 88 | 64 | 2,640 | 3,486,971 | 15,771,921 | 124,363 | 19,385,895 |
| 82 | openapi:review | OpenAPI | done | fable-5-1 | 09-23 11:44 | 9.5m | 57 | 43 | 1,704 | 776,018 | 4,255,663 | 44,571 | 5,077,956 |
| 83 | openapi:fix | OpenAPI | done | fable-5-1 | 09-23 11:54 | 13.1m | 79 | 54 | 2,408 | 914,792 | 6,167,360 | 53,365 | 7,137,925 |
| 84 | critic:completeness | Completeness Critic | done | fable-5-1 | 09-23 12:07 | 22.4m | 63 | 48 | 1,866 | 935,384 | 7,855,908 | 69,423 | 8,862,581 |
| | **소계** | | | | | **9h 40m** | **3,185** | **2,270** | **94,278** | **52,219,021** | **309,350,940** | **2,061,455** | **363,725,694** |

#### wf_6cfeebb9-60e — `wf_6cfeebb9-60e` · 62 에이전트 · 실제 경과 시간 09-23 09:52 → 09-23 10:55 (1h 3m) · 에이전트 활동 시간 합산 4h 33m · 합계 173,396,890 토큰(출력 948,468)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | fix:06-adr/0001-license-grade-table-and-d02-interpretatio… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 8.1m | 65 | 52 | 1,990 | 634,815 | 5,351,620 | 29,499 | 6,017,924 |
| 2 | fix:06-adr/0003-orchestrator-neutral-pipeline-and-non-dur… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 6.8m | 61 | 46 | 1,802 | 837,007 | 5,695,417 | 30,804 | 6,565,030 |
| 3 | fix:06-adr/0002-provenance-element-path-and-nullable-page… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 6.8m | 73 | 56 | 2,216 | 1,242,355 | 7,654,192 | 26,632 | 8,925,395 |
| 4 | fix:06-adr/0005-doc-version-content-hash-only-and-acl-pay… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 6.9m | 51 | 37 | 1,512 | 1,137,517 | 5,670,583 | 31,345 | 6,840,957 |
| 5 | fix:06-adr/0004-deterministic-chunk-id-scoped-record-id-a… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 4.8m | 36 | 18 | 1,002 | 415,248 | 2,372,300 | 18,019 | 2,806,569 |
| 6 | fix:06-adr/0006-pdf-fast-path-pypdfium2-pdftext-replaces-… | ADR fast cycle | done | fable-5-1 | 09-23 09:52 | 6.8m | 56 | 39 | 1,642 | 1,188,897 | 4,854,746 | 31,797 | 6,077,082 |
| 7 | fix:06-adr/0007-hwp5-java-sidecar-first-pyhwp-demoted.md | ADR fast cycle | done | fable-5-1 | 09-23 09:57 | 4.9m | 46 | 37 | 1,352 | 571,872 | 3,959,976 | 21,991 | 4,555,191 |
| 8 | fix:06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md | ADR fast cycle | done | fable-5-1 | 09-23 09:59 | 9.1m | 80 | 64 | 2,440 | 2,078,578 | 10,320,181 | 45,631 | 12,446,830 |
| 9 | fix:06-adr/0009-embedding-serving-vllm-pooling-tei-inproc… | ADR fast cycle | done | fable-5-1 | 09-23 09:59 | 7.8m | 57 | 43 | 1,704 | 892,631 | 6,981,268 | 35,085 | 7,910,688 |
| 10 | fix:06-adr/0010-bge-m3-rationale-and-late-interaction-slo… | ADR fast cycle | done | fable-5-1 | 09-23 09:59 | 4.3m | 44 | 31 | 1,288 | 555,070 | 3,665,916 | 18,755 | 4,241,029 |
| 11 | fix:06-adr/0011-kv-and-object-storage-valkey-rustfs-seawe… | ADR fast cycle | done | fable-5-1 | 09-23 09:59 | 4.5m | 46 | 33 | 1,352 | 839,216 | 4,688,926 | 19,277 | 5,548,771 |
| 12 | fix:06-adr/0012-lite-profile-qdrant-only-client-bm25.md | ADR fast cycle | done | fable-5-1 | 09-23 10:00 | 6.2m | 68 | 49 | 2,026 | 993,606 | 8,139,862 | 27,378 | 9,162,872 |
| 13 | fix:06-adr/0013-fusion-rrf-k60-then-convex-combination-an… | ADR fast cycle | done | fable-5-1 | 09-23 10:01 | 8.7m | 49 | 31 | 1,448 | 843,034 | 4,830,973 | 36,251 | 5,711,706 |
| 14 | review:06-adr/0014-sparse-representation-bge-m3-lexical-l… | ADR fast cycle | done | fable-5-1 | 09-23 10:03 | 3.3m | 18 | 12 | 426 | 345,916 | 844,796 | 10,909 | 1,202,047 |
| 15 | review:06-adr/0015-graph-rag-external-plugin-raptor-core-… | ADR fast cycle | done | fable-5-1 | 09-23 10:03 | 3.0m | 20 | 12 | 490 | 303,879 | 976,352 | 10,660 | 1,291,381 |
| 16 | review:06-adr/0016-llm-enrichment-default-off-and-budget-… | ADR fast cycle | done | fable-5-1 | 09-23 10:06 | 2.1m | 15 | 10 | 360 | 219,497 | 668,553 | 7,632 | 896,042 |
| 17 | review:06-adr/0017-event-delivery-outbox-cloudevents-no-b… | ADR fast cycle | done | fable-5-1 | 09-23 10:06 | 3.8m | 17 | 9 | 484 | 154,337 | 995,885 | 11,935 | 1,162,641 |
| 18 | review:06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md | ADR fast cycle | done | fable-5-1 | 09-23 10:06 | 2.7m | 23 | 16 | 616 | 338,400 | 1,303,951 | 9,951 | 1,652,918 |
| 19 | review:06-adr/0019-chunk-size-tokenizer-defaults-and-reco… | ADR fast cycle | done | fable-5-1 | 09-23 10:06 | 3.8m | 24 | 12 | 708 | 170,052 | 1,715,584 | 10,085 | 1,896,429 |
| 20 | review:06-adr/0020-default-chunker-structure-aware-and-de… | ADR fast cycle | done | fable-5-1 | 09-23 10:08 | 3.7m | 20 | 12 | 490 | 306,342 | 1,010,641 | 8,065 | 1,325,538 |
| 21 | review:06-adr/0021-korean-analyzer-kiwi-promotion-and-int… | ADR fast cycle | done | fable-5-1 | 09-23 10:08 | 3.7m | 21 | 14 | 552 | 279,432 | 1,144,500 | 12,612 | 1,437,096 |
| 22 | review:06-adr/0022-observability-genai-semconv-pin-and-li… | ADR fast cycle | done | fable-5-1 | 09-23 10:09 | 2.3m | 21 | 16 | 552 | 231,301 | 902,215 | 7,327 | 1,141,395 |
| 23 | review:06-adr/0023-evaluation-qrels-answer-spans-and-line… | ADR fast cycle | done | fable-5-1 | 09-23 10:10 | 3.8m | 26 | 20 | 712 | 428,189 | 1,491,092 | 12,104 | 1,932,097 |
| 24 | review:06-adr/0024-context-pack-ordering-and-anthropic-se… | ADR fast cycle | done | fable-5-1 | 09-23 10:10 | 3.7m | 24 | 15 | 618 | 335,271 | 1,337,858 | 10,851 | 1,684,598 |
| 25 | review:06-adr/0025-mcp-cursor-pagination-and-tool-set.md | ADR fast cycle | done | fable-5-1 | 09-23 10:10 | 1.3m | 11 | 6 | 262 | 85,773 | 439,459 | 2,596 | 528,090 |
| 26 | review:06-adr/0026-index-commit-generation-saga-and-ledge… | ADR fast cycle | done | fable-5-1 | 09-23 10:11 | 3.1m | 24 | 17 | 648 | 320,838 | 1,363,162 | 8,860 | 1,693,508 |
| 27 | review:06-adr/0027-security-context-injection-and-acl-enf… | ADR fast cycle | done | fable-5-1 | 09-23 10:11 | 2.5m | 19 | 11 | 488 | 217,904 | 985,700 | 7,130 | 1,211,222 |
| 28 | review:06-adr/0028-tenant-isolation-tiering-policy.md | ADR fast cycle | done | fable-5-1 | 09-23 10:12 | 2.9m | 19 | 13 | 488 | 157,122 | 888,481 | 7,453 | 1,053,544 |
| 29 | review:06-adr/0029-three-text-rule-and-deterministic-cont… | ADR fast cycle | done | fable-5-1 | 09-23 10:12 | 3.2m | 17 | 12 | 424 | 293,491 | 787,332 | 8,817 | 1,090,064 |
| 30 | review:06-adr/0030-single-coordinate-system-and-score-led… | ADR fast cycle | done | fable-5-1 | 09-23 10:14 | 6.6m | 23 | 12 | 676 | 145,656 | 1,417,292 | 12,969 | 1,576,593 |
| 31 | review:06-adr/0031-profile-schema-extends-and-quality-gat… | ADR fast cycle | done | fable-5-1 | 09-23 10:14 | 4.4m | 22 | 16 | 584 | 508,897 | 1,400,739 | 12,024 | 1,922,244 |
| 32 | review:06-adr/0032-plugin-sdk-stage-protocol-and-conforma… | ADR fast cycle | done | fable-5-1 | 09-23 10:14 | 5.0m | 19 | 13 | 488 | 266,264 | 1,132,413 | 12,191 | 1,411,356 |
| 33 | review:06-adr/0033-sidecar-convert-contract-and-isolation… | ADR fast cycle | done | fable-5-1 | 09-23 10:14 | 7.2m | 23 | 14 | 646 | 210,226 | 1,497,691 | 14,232 | 1,722,795 |
| 34 | review:06-adr/0034-retrieval-hot-path-postgres-independen… | ADR fast cycle | done | fable-5-1 | 09-23 10:15 | 3.7m | 16 | 10 | 392 | 212,520 | 819,568 | 6,234 | 1,038,714 |
| 35 | review:06-adr/0035-python-version-and-toolchain-pins.md | ADR fast cycle | done | fable-5-1 | 09-23 10:15 | 3.9m | 18 | 11 | 486 | 113,398 | 898,132 | 9,143 | 1,021,159 |
| 36 | review:06-adr/0036-naming-and-identifier-conventions.md | ADR fast cycle | done | fable-5-1 | 09-23 10:18 | 3.4m | 17 | 11 | 454 | 203,497 | 942,384 | 7,733 | 1,154,068 |
| 37 | review:06-adr/0037-artifact-cache-scope-and-stage-key-com… | ADR fast cycle | done | fable-5-1 | 09-23 10:18 | 2.9m | 14 | 11 | 328 | 189,260 | 556,228 | 7,273 | 753,089 |
| 38 | review:06-adr/0038-outbound-egress-policy-and-webhook-sig… | ADR fast cycle | done | fable-5-1 | 09-23 10:19 | 4.5m | 18 | 13 | 456 | 249,462 | 802,920 | 9,955 | 1,062,793 |
| 39 | fix:06-adr/0014-sparse-representation-bge-m3-lexical-leg-… | ADR fast cycle | done | fable-5-1 | 09-23 10:19 | 3.1m | 43 | 27 | 1,256 | 386,338 | 2,766,825 | 13,714 | 3,168,133 |
| 40 | fix:06-adr/0015-graph-rag-external-plugin-raptor-core-opt… | ADR fast cycle | done | fable-5-1 | 09-23 10:20 | 4.3m | 25 | 13 | 680 | 413,603 | 1,553,910 | 16,798 | 1,984,991 |
| 41 | fix:06-adr/0016-llm-enrichment-default-off-and-budget-pol… | ADR fast cycle | done | fable-5-1 | 09-23 10:21 | 3.0m | 27 | 16 | 774 | 418,461 | 1,536,356 | 9,371 | 1,964,962 |
| 42 | fix:06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md | ADR fast cycle | done | fable-5-1 | 09-23 10:22 | 2.8m | 31 | 17 | 872 | 264,268 | 1,568,868 | 10,903 | 1,844,911 |
| 43 | fix:06-adr/0017-event-delivery-outbox-cloudevents-no-brok… | ADR fast cycle | done | fable-5-1 | 09-23 10:22 | 3.2m | 34 | 16 | 998 | 149,376 | 1,675,738 | 11,528 | 1,837,640 |
| 44 | fix:06-adr/0019-chunk-size-tokenizer-defaults-and-recount… | ADR fast cycle | done | fable-5-1 | 09-23 10:22 | 1.6m | 15 | 8 | 390 | 88,641 | 643,950 | 3,854 | 736,835 |
| 45 | fix:06-adr/0020-default-chunker-structure-aware-and-depen… | ADR fast cycle | done | fable-5-1 | 09-23 10:24 | 1.9m | 25 | 13 | 650 | 214,891 | 1,065,880 | 5,945 | 1,287,366 |
| 46 | fix:06-adr/0025-mcp-cursor-pagination-and-tool-set.md | ADR fast cycle | done | fable-5-1 | 09-23 10:24 | 2.4m | 33 | 21 | 936 | 546,135 | 2,097,617 | 8,566 | 2,653,254 |
| 47 | fix:06-adr/0021-korean-analyzer-kiwi-promotion-and-interi… | ADR fast cycle | done | fable-5-1 | 09-23 10:24 | 5.7m | 34 | 18 | 968 | 413,390 | 2,398,738 | 12,886 | 2,825,982 |
| 48 | fix:06-adr/0023-evaluation-qrels-answer-spans-and-linear-… | ADR fast cycle | done | fable-5-1 | 09-23 10:24 | 4.0m | 40 | 24 | 1,160 | 377,846 | 2,731,959 | 14,205 | 3,125,170 |
| 49 | fix:06-adr/0024-context-pack-ordering-and-anthropic-searc… | ADR fast cycle | done | fable-5-1 | 09-23 10:25 | 5.1m | 31 | 18 | 902 | 396,695 | 1,972,555 | 21,484 | 2,391,636 |
| 50 | fix:06-adr/0027-security-context-injection-and-acl-enforc… | ADR fast cycle | done | fable-5-1 | 09-23 10:25 | 3.3m | 23 | 12 | 616 | 184,877 | 978,788 | 23,363 | 1,187,644 |
| 51 | fix:06-adr/0028-tenant-isolation-tiering-policy.md | ADR fast cycle | done | fable-5-1 | 09-23 10:25 | 2.2m | 25 | 17 | 710 | 305,782 | 1,553,068 | 8,698 | 1,868,258 |
| 52 | fix:06-adr/0029-three-text-rule-and-deterministic-context… | ADR fast cycle | done | fable-5-1 | 09-23 10:26 | 1.0m | 10 | 5 | 260 | 60,216 | 396,078 | 3,020 | 459,574 |
| 53 | fix:06-adr/0034-retrieval-hot-path-postgres-independence-… | ADR fast cycle | done | fable-5-1 | 09-23 10:27 | 2.2m | 15 | 5 | 390 | 110,385 | 615,666 | 4,224 | 730,665 |
| 54 | fix:06-adr/0031-profile-schema-extends-and-quality-gates.… | ADR fast cycle | done | fable-5-1 | 09-23 10:28 | 3.8m | 43 | 29 | 1,226 | 839,023 | 3,720,913 | 16,563 | 4,577,725 |
| 55 | fix:06-adr/0032-plugin-sdk-stage-protocol-and-conformance… | ADR fast cycle | done | fable-5-1 | 09-23 10:28 | 2.6m | 27 | 19 | 774 | 250,620 | 1,736,386 | 9,161 | 1,996,941 |
| 56 | fix:06-adr/0035-python-version-and-toolchain-pins.md | ADR fast cycle | done | fable-5-1 | 09-23 10:29 | 8.7m | 43 | 24 | 1,226 | 449,840 | 2,972,622 | 22,394 | 3,446,082 |
| 57 | fix:06-adr/0030-single-coordinate-system-and-score-ledger… | ADR fast cycle | done | fable-5-1 | 09-23 10:30 | 3.1m | 23 | 15 | 586 | 411,434 | 1,229,870 | 11,707 | 1,653,597 |
| 58 | fix:06-adr/0037-artifact-cache-scope-and-stage-key-compos… | ADR fast cycle | done | fable-5-1 | 09-23 10:30 | 3.5m | 44 | 30 | 1,288 | 538,009 | 2,825,340 | 14,931 | 3,379,568 |
| 59 | fix:06-adr/0033-sidecar-convert-contract-and-isolation-la… | ADR fast cycle | done | fable-5-1 | 09-23 10:30 | 3.9m | 30 | 15 | 870 | 202,423 | 1,720,362 | 14,571 | 1,938,226 |
| 60 | fix:06-adr/0036-naming-and-identifier-conventions.md | ADR fast cycle | done | fable-5-1 | 09-23 10:31 | 4.2m | 24 | 12 | 678 | 168,219 | 1,263,392 | 16,890 | 1,449,179 |
| 61 | fix:06-adr/0038-outbound-egress-policy-and-webhook-signin… | ADR fast cycle | done | fable-5-1 | 09-23 10:31 | 3.6m | 29 | 18 | 868 | 154,287 | 1,797,654 | 11,899 | 1,964,708 |
| 62 | adr:index | ADR index | done | fable-5-1 | 09-23 10:37 | 17.5m | 58 | 27 | 1,616 | 589,199 | 4,610,975 | 50,588 | 5,252,378 |
| | **소계** | | | | | **4h 33m** | **1,953** | **1,273** | **55,296** | **26,450,728** | **145,942,398** | **948,468** | **173,396,890** |

#### wf_9464fd89-d43 — `wf_9464fd89-d43` · 36 에이전트 · 실제 경과 시간 09-23 12:44 → 09-23 16:20 (3h 35m) · 에이전트 활동 시간 합산 11h 0m · 합계 1,461,880,501 토큰(출력 2,773,748)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | t1:triage | T1 Triage | done | opus-5-5 | 09-23 12:44 | 16.5m | 76 | 43 | 152 | 493,451 | 11,724,145 | 98,535 | 12,316,283 |
| 2 | t2:bible-revision | T2 Bible Revision | done | opus-5-5 | 09-23 13:01 | 27.6m | 227 | 137 | 454 | 1,577,822 | 50,136,763 | 134,198 | 51,849,237 |
| 3 | t3:schema-sync | T3 Schema Sync | done | sonnet-5 | 09-23 13:29 | 29.4m | 278 | 154 | 556 | 704,612 | 56,859,292 | 113,241 | 57,677,701 |
| 4 | p1:group-1 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 24.6m | 170 | 106 | 340 | 751,018 | 35,096,153 | 118,238 | 35,965,749 |
| 5 | p1:group-2 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 14.5m | 153 | 82 | 306 | 479,300 | 26,898,341 | 65,230 | 27,443,177 |
| 6 | p1:group-3 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 9.1m | 143 | 90 | 286 | 390,167 | 16,493,782 | 40,267 | 16,924,502 |
| 7 | p1:group-5 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 29.2m | 334 | 193 | 668 | 700,967 | 78,579,039 | 118,474 | 79,399,148 |
| 8 | p1:group-4 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 29.1m | 358 | 202 | 716 | 665,521 | 76,106,995 | 110,037 | 76,883,269 |
| 9 | p1:group-6 | P1 Propagate | done | sonnet-5 | 09-23 13:58 | 23.1m | 269 | 153 | 538 | 510,931 | 48,359,508 | 96,643 | 48,967,620 |
| 10 | p1:group-7 | P1 Propagate | done | sonnet-5 | 09-23 14:07 | 17.1m | 179 | 106 | 358 | 491,568 | 29,326,848 | 72,305 | 29,891,079 |
| 11 | p1:group-8 | P1 Propagate | done | sonnet-5 | 09-23 14:13 | 28.0m | 311 | 178 | 622 | 779,413 | 88,070,440 | 106,261 | 88,956,736 |
| 12 | p1:group-9 | P1 Propagate | done | sonnet-5 | 09-23 14:21 | 20.1m | 251 | 148 | 502 | 693,128 | 46,107,098 | 81,340 | 46,882,068 |
| 13 | p1:group-10 | P1 Propagate | done | sonnet-5 | 09-23 14:23 | 22.6m | 242 | 132 | 484 | 670,914 | 51,409,863 | 83,477 | 52,164,738 |
| 14 | p1:group-11 | P1 Propagate | done | sonnet-5 | 09-23 14:24 | 32.4m | 349 | 197 | 698 | 820,852 | 102,864,086 | 132,762 | 103,818,398 |
| 15 | p1:group-12 | P1 Propagate | done | sonnet-5 | 09-23 14:27 | 44.3m | 439 | 249 | 878 | 940,739 | 142,008,278 | 180,290 | 143,130,185 |
| 16 | p1:group-13 | P1 Propagate | done | sonnet-5 | 09-23 14:27 | 17.9m | 177 | 105 | 354 | 754,515 | 34,477,817 | 78,997 | 35,311,683 |
| 17 | p1:group-14 | P1 Propagate | done | sonnet-5 | 09-23 14:41 | 9.0m | 98 | 60 | 196 | 373,720 | 10,369,406 | 37,157 | 10,780,479 |
| 18 | p1:group-15 | P1 Propagate | done | sonnet-5 | 09-23 14:41 | 18.4m | 220 | 128 | 440 | 594,809 | 36,944,564 | 77,844 | 37,617,657 |
| 19 | p1:group-16 | P1 Propagate | done | sonnet-5 | 09-23 14:45 | 11.4m | 131 | 79 | 262 | 467,290 | 16,188,918 | 50,115 | 16,706,585 |
| 20 | p1:group-17 | P1 Propagate | done | sonnet-5 | 09-23 14:45 | 24.2m | 340 | 184 | 680 | 560,201 | 67,139,157 | 98,237 | 67,798,275 |
| 21 | p1:group-18 | P1 Propagate | done | sonnet-5 | 09-23 14:50 | 17.1m | 182 | 102 | 364 | 455,404 | 27,747,471 | 73,744 | 28,276,983 |
| 22 | p1:group-19 | P1 Propagate | done | sonnet-5 | 09-23 14:57 | 25.5m | 301 | 173 | 602 | 663,878 | 69,246,339 | 104,290 | 70,015,109 |
| 23 | p1:group-20 | P1 Propagate | done | sonnet-5 | 09-23 14:57 | 15.0m | 188 | 108 | 376 | 426,572 | 28,775,508 | 61,772 | 29,264,228 |
| 24 | p1:group-21 | P1 Propagate | done | sonnet-5 | 09-23 15:00 | 18.4m | 176 | 110 | 352 | 663,234 | 29,097,684 | 87,434 | 29,848,704 |
| 25 | p1:group-22 | P1 Propagate | done | sonnet-5 | 09-23 15:07 | 7.5m | 56 | 30 | 112 | 200,858 | 4,935,744 | 32,886 | 5,169,600 |
| 26 | p2:trim-1 | P2 Trim | done | sonnet-5 | 09-23 15:22 | 28.4m | 253 | 141 | 506 | 919,005 | 78,768,448 | 121,137 | 79,809,096 |
| 27 | p2:trim-2 | P2 Trim | done | sonnet-5 | 09-23 15:22 | 26.2m | 225 | 126 | 450 | 804,547 | 62,431,849 | 110,120 | 63,346,966 |
| 28 | p2:trim-3 | P2 Trim | done | sonnet-5 | 09-23 15:22 | 37.1m | 238 | 136 | 476 | 821,669 | 64,989,798 | 157,360 | 65,969,303 |
| 29 | p3:review-1 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 2.3m | 35 | 19 | 70 | 329,007 | 3,616,184 | 7,381 | 3,952,642 |
| 30 | p3:review-2 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 3.0m | 49 | 30 | 98 | 527,111 | 6,880,912 | 11,314 | 7,419,435 |
| 31 | p3:review-3 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 2.0m | 37 | 20 | 74 | 238,706 | 3,550,741 | 6,381 | 3,795,902 |
| 32 | p3:review-4 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 2.8m | 36 | 21 | 72 | 319,155 | 3,966,983 | 10,182 | 4,296,392 |
| 33 | p3:review-5 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 4.3m | 61 | 34 | 122 | 339,839 | 7,908,921 | 13,549 | 8,262,431 |
| 34 | p3:review-6 | P3 Sample Verify | done | sonnet-5 | 09-23 15:59 | 3.7m | 34 | 19 | 68 | 234,839 | 2,752,015 | 7,486 | 2,994,408 |
| 35 | p3:review-7 | P3 Sample Verify | done | sonnet-5 | 09-23 16:01 | 2.5m | 26 | 17 | 52 | 278,648 | 2,184,888 | 12,163 | 2,475,751 |
| 36 | p4:residual | P4 Residual | done | sonnet-5 | 09-23 16:04 | 16.0m | 121 | 65 | 242 | 425,199 | 16,010,640 | 62,901 | 16,498,982 |
| | **소계** | | | | | **11h 0m** | **6,763** | **3,877** | **13,526** | **21,068,609** | **1,438,024,618** | **2,773,748** | **1,461,880,501** |

#### wf_19c804c1-495 — `wf_19c804c1-495` · 4 에이전트 · 실제 경과 시간 09-23 14:03 → 09-23 14:30 (26.1m) · 에이전트 활동 시간 합산 35.4m · 합계 32,092,949 토큰(출력 150,587)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | write:README.md | Write | done | sonnet-5 | 09-23 14:03 | 10.5m | 98 | 63 | 196 | 516,902 | 11,299,798 | 46,677 | 11,863,573 |
| 2 | write:CLAUDE.md | Write | done | sonnet-5 | 09-23 14:03 | 9.4m | 61 | 42 | 122 | 563,566 | 6,552,921 | 48,921 | 7,165,530 |
| 3 | review:root-docs | Review | done | sonnet-5 | 09-23 14:14 | 8.9m | 70 | 38 | 140 | 307,589 | 7,142,527 | 23,933 | 7,474,189 |
| 4 | fix:root-docs | Review | done | sonnet-5 | 09-23 14:23 | 6.7m | 60 | 36 | 120 | 355,503 | 5,202,978 | 31,056 | 5,589,657 |
| | **소계** | | | | | **35.4m** | **289** | **179** | **578** | **1,743,560** | **30,198,224** | **150,587** | **32,092,949** |

#### wf_25dbfe1b-97e — `wf_25dbfe1b-97e` · 3 에이전트 · 실제 경과 시간 09-23 14:05 → 09-23 14:31 (25.6m) · 에이전트 활동 시간 합산 35.9m · 합계 24,301,240 토큰(출력 102,515)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | s1:foundation | S1 Foundation | done | opus-5-5 | 09-23 14:05 | 15.2m | 71 | 40 | 142 | 339,956 | 9,157,109 | 34,499 | 9,531,706 |
| 2 | s2:contracts | S2 Contracts | running | sonnet-5 | 09-23 14:20 | 10.4m | 74 | 44 | 148 | 432,688 | 6,710,411 | 27,150 | 7,170,397 |
| 3 | s3:core | S3 Core | running | sonnet-5 | 09-23 14:20 | 10.3m | 71 | 49 | 142 | 534,582 | 7,023,547 | 40,866 | 7,599,137 |
| | **소계** | | | | | **35.9m** | **216** | **133** | **432** | **1,307,226** | **22,891,067** | **102,515** | **24,301,240** |

#### wf_8eef8c02-a6c — `wf_8eef8c02-a6c` · 6 에이전트 · 실제 경과 시간 09-23 14:32 → 09-23 16:52 (2h 21m) · 에이전트 활동 시간 합산 3h 26m · 합계 443,381,904 토큰(출력 696,724)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | s1:foundation | S1 Foundation | done | opus-5-5 | 09-23 14:32 | 12.6m | 80 | 51 | 160 | 372,122 | 9,770,473 | 48,187 | 10,190,942 |
| 2 | s2:contracts | S2 Contracts | done | sonnet-5 | 09-23 14:44 | 1h 10m | 479 | 283 | 958 | 1,129,397 | 148,048,429 | 211,020 | 149,389,804 |
| 3 | s3:core | S3 Core | done | sonnet-5 | 09-23 14:44 | 1h 6m | 557 | 339 | 1,114 | 1,167,888 | 212,416,701 | 260,184 | 213,845,887 |
| 4 | s4:handoff | S4 Handoff | done | sonnet-5 | 09-23 15:55 | 27.7m | 194 | 113 | 388 | 492,477 | 29,422,536 | 76,742 | 29,992,143 |
| 5 | s5:review | S5 Review | done | sonnet-5 | 09-23 16:22 | 9.0m | 115 | 67 | 230 | 278,495 | 12,492,481 | 18,938 | 12,790,144 |
| 6 | s5:fix | S5 Review | done | sonnet-5 | 09-23 16:31 | 21.0m | 168 | 98 | 336 | 578,960 | 26,512,035 | 81,653 | 27,172,984 |
| | **소계** | | | | | **3h 26m** | **1,593** | **951** | **3,186** | **4,019,339** | **438,662,655** | **696,724** | **443,381,904** |

#### wf_ac8680f5-c18 — `wf_ac8680f5-c18` · 2 에이전트 · 실제 경과 시간 09-23 16:23 → 09-23 16:31 (7.9m) · 에이전트 활동 시간 합산 11.5m · 합계 8,070,757 토큰(출력 58,274)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | edit:coding-standards | Edit | done | sonnet-5 | 09-23 16:23 | 7.9m | 44 | 25 | 88 | 369,184 | 3,833,940 | 40,639 | 4,243,851 |
| 2 | edit:roadmap-recalibration | Edit | done | sonnet-5 | 09-23 16:23 | 3.6m | 34 | 20 | 68 | 241,090 | 3,568,113 | 17,635 | 3,826,906 |
| | **소계** | | | | | **11.5m** | **78** | **45** | **156** | **610,274** | **7,402,053** | **58,274** | **8,070,757** |

#### wf_643ae098-82a — `wf_643ae098-82a` · 5 에이전트 · 실제 경과 시간 09-23 16:55 → 09-23 17:15 (20.7m) · 에이전트 활동 시간 합산 48.1m · 합계 62,676,667 토큰(출력 183,880)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | headers:group-1 | Header pass | done | sonnet-5 | 09-23 16:55 | 12.8m | 126 | 82 | 252 | 472,861 | 12,459,856 | 53,850 | 12,986,819 |
| 2 | headers:group-2 | Header pass | done | sonnet-5 | 09-23 16:55 | 8.5m | 81 | 55 | 162 | 266,133 | 7,143,248 | 38,376 | 7,447,919 |
| 3 | headers:group-3 | Header pass | done | sonnet-5 | 09-23 16:55 | 18.5m | 227 | 130 | 454 | 482,024 | 35,518,285 | 59,505 | 36,060,268 |
| 4 | headers:group-4 | Header pass | done | sonnet-5 | 09-23 16:55 | 6.2m | 55 | 36 | 110 | 275,379 | 4,658,170 | 26,967 | 4,960,626 |
| 5 | headers:verify | Verify | done | sonnet-5 | 09-23 17:13 | 2.1m | 27 | 17 | 54 | 82,906 | 1,132,893 | 5,182 | 1,221,035 |
| | **소계** | | | | | **48.1m** | **516** | **320** | **1,032** | **1,579,303** | **60,912,452** | **183,880** | **62,676,667** |

#### wf_0755d3ae-470 — `wf_0755d3ae-470` · 8 에이전트 · 실제 경과 시간 09-23 17:16 → 09-23 18:41 (1h 26m) · 에이전트 활동 시간 합산 3h 42m · 합계 256,529,370 토큰(출력 849,127)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | s0:deps | S0 Deps | done | sonnet-5 | 09-23 17:16 | 9.9m | 66 | 34 | 132 | 180,642 | 4,095,211 | 18,459 | 4,294,444 |
| 2 | 6b:kit-1 | 6B Conformance | done | sonnet-5 | 09-23 17:26 | 41.5m | 309 | 176 | 618 | 593,609 | 60,372,283 | 153,089 | 61,119,599 |
| 3 | 6b:kit-2 | 6B Conformance | done | sonnet-5 | 09-23 17:26 | 16.8m | 161 | 100 | 322 | 496,303 | 22,174,371 | 77,186 | 22,748,182 |
| 4 | 6b:kit-3 | 6B Conformance | done | sonnet-5 | 09-23 17:26 | 22.4m | 156 | 95 | 312 | 585,893 | 24,347,691 | 107,271 | 25,041,167 |
| 5 | 6d:hwpx | 6D Spikes | done | opus-5-5 | 09-23 17:26 | 44.3m | 214 | 128 | 428 | 778,855 | 49,824,462 | 188,389 | 50,792,134 |
| 6 | 6d:embedder | 6D Spikes | done | sonnet-5 | 09-23 17:26 | 30.5m | 231 | 140 | 462 | 606,580 | 48,645,573 | 121,305 | 49,373,920 |
| 7 | 6d:qdrant | 6D Spikes | done | opus-5-5 | 09-23 17:26 | 25.3m | 110 | 67 | 220 | 341,830 | 13,328,728 | 96,080 | 13,766,858 |
| 8 | verify:all | Verify | done | sonnet-5 | 09-23 18:10 | 31.4m | 215 | 151 | 430 | 409,439 | 28,895,849 | 87,348 | 29,393,066 |
| | **소계** | | | | | **3h 42m** | **1,462** | **891** | **2,924** | **3,993,151** | **251,684,168** | **849,127** | **256,529,370** |

#### wf_b7ec72fc-7e3 — `wf_b7ec72fc-7e3` · 7 에이전트 · 실제 경과 시간 09-23 18:48 → 09-23 20:02 (1h 13m) · 에이전트 활동 시간 합산 4h 4m · 합계 410,744,798 토큰(출력 997,509)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F1-01:fetch-fsspec-httpx | Implement | done | sonnet-5 | 09-23 18:48 | 25.0m | 177 | 103 | 354 | 695,758 | 40,353,566 | 121,538 | 41,171,216 |
| 2 | F1-02:format-detector-and-parse-router | Implement | done | sonnet-5 | 09-23 18:48 | 39.4m | 260 | 149 | 520 | 798,089 | 71,014,570 | 188,702 | 72,001,881 |
| 3 | F1-03:parse-text-markdown-csv | Implement | done | sonnet-5 | 09-23 18:48 | 50.5m | 323 | 185 | 646 | 1,551,258 | 108,602,093 | 164,092 | 110,318,089 |
| 4 | F1-04:parse-html-trafilatura | Implement | done | sonnet-5 | 09-23 18:48 | 33.4m | 221 | 139 | 442 | 895,516 | 59,432,315 | 153,941 | 60,482,214 |
| 5 | F1-05:parse-pdf-fast-pypdfium2 | Implement | done | sonnet-5 | 09-23 18:48 | 40.4m | 289 | 165 | 578 | 600,276 | 59,160,291 | 170,981 | 59,932,126 |
| 6 | F1-06:normalize-korean | Implement | done | sonnet-5 | 09-23 18:48 | 32.8m | 183 | 101 | 366 | 523,602 | 37,206,547 | 146,306 | 37,876,821 |
| 7 | F1:verify | Verify | done | sonnet-5 | 09-23 19:39 | 22.9m | 262 | 152 | 524 | 301,576 | 28,608,402 | 51,949 | 28,962,451 |
| | **소계** | | | | | **4h 4m** | **1,715** | **994** | **3,430** | **5,366,075** | **404,377,784** | **997,509** | **410,744,798** |

#### wf_9a81fe63-40d — `wf_9a81fe63-40d` · 4 에이전트 · 실제 경과 시간 09-23 20:03 → 09-23 20:52 (49.0m) · 에이전트 활동 시간 합산 1h 45m · 합계 159,735,652 토큰(출력 471,044)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F2-01:chunk-structure-aware | Implement | done | sonnet-5 | 09-23 20:03 | 26.0m | 165 | 100 | 330 | 648,102 | 34,351,463 | 127,461 | 35,127,356 |
| 2 | F2-02:chunk-table-rows-and-recount | Implement | done | sonnet-5 | 09-23 20:03 | 36.9m | 252 | 144 | 504 | 723,811 | 57,870,047 | 176,766 | 58,771,128 |
| 3 | F2-03:enrich-deterministic | Implement | done | sonnet-5 | 09-23 20:03 | 30.2m | 228 | 137 | 456 | 798,000 | 54,062,490 | 129,346 | 54,990,292 |
| 4 | F2:verify | Verify | done | sonnet-5 | 09-23 20:40 | 12.1m | 129 | 74 | 258 | 226,384 | 10,582,763 | 37,471 | 10,846,876 |
| | **소계** | | | | | **1h 45m** | **774** | **455** | **1,548** | **2,396,297** | **156,866,763** | **471,044** | **159,735,652** |

#### wf_52b111c5-c82 — `wf_52b111c5-c82` · 4 에이전트 · 실제 경과 시간 09-23 20:52 → 09-23 22:05 (1h 13m) · 에이전트 활동 시간 합산 2h 24m · 합계 290,239,778 토큰(출력 524,584)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F3-01:embed-stage-and-sparse-bm25 | Implement | done | sonnet-5 | 09-23 20:52 | 25.7m | 198 | 121 | 396 | 623,532 | 41,131,048 | 119,833 | 41,874,809 |
| 2 | F3-03:ingest-pipeline-e2e | Implement | done | sonnet-5 | 09-23 20:52 | 45.9m | 310 | 192 | 620 | 1,099,191 | 85,638,024 | 187,415 | 86,925,250 |
| 3 | F3-02:index-stage-and-commit-saga | Implement | done | sonnet-5 | 09-23 20:52 | 47.2m | 392 | 238 | 784 | 1,012,205 | 133,076,088 | 163,312 | 134,252,389 |
| 4 | F3:verify | Verify | done | sonnet-5 | 09-23 21:39 | 25.4m | 222 | 131 | 444 | 348,512 | 26,784,350 | 54,024 | 27,187,330 |
| | **소계** | | | | | **2h 24m** | **1,122** | **682** | **2,244** | **3,083,440** | **286,629,510** | **524,584** | **290,239,778** |

#### wf_a6cb70da-507 — `wf_a6cb70da-507` · 7 에이전트 · 실제 경과 시간 09-23 22:07 → 09-24 00:45 (2h 38m) · 에이전트 활동 시간 합산 4h 46m · 합계 547,162,287 토큰(출력 1,070,712)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F4-01:planner-and-filters | Implement | done | sonnet-5 | 09-23 22:07 | 48.8m | 285 | 160 | 570 | 837,930 | 84,323,526 | 187,689 | 85,349,715 |
| 2 | F4-02:channels-fusion-hydrate | Implement | done | sonnet-5 | 09-23 22:07 | 43.4m | 320 | 199 | 640 | 1,037,224 | 89,246,265 | 192,368 | 90,476,497 |
| 3 | F4-03:postprocess-and-pack | Implement | done | sonnet-5 | 09-23 22:07 | 42.9m | 290 | 185 | 580 | 864,740 | 79,469,774 | 198,510 | 80,533,604 |
| 4 | F4-04:render-and-query-pipeline | Implement | done | sonnet-5 | 09-23 22:07 | 41.9m | 297 | 183 | 594 | 838,693 | 72,911,674 | 162,923 | 73,913,884 |
| 5 | F4:verify | Verify | done | sonnet-5 | 09-23 22:55 | 1h 11m | 582 | 350 | 1,164 | 938,567 | 152,499,855 | 204,233 | 153,643,819 |
| 6 | F4:opus-review | Review | done | opus-5-5 | 09-24 00:06 | 8.4m | 82 | 47 | 164 | 350,499 | 9,881,592 | 28,776 | 10,261,031 |
| 7 | F4:review-fix | Review | done | sonnet-5 | 09-24 00:14 | 30.4m | 283 | 165 | 566 | 597,013 | 52,289,945 | 96,213 | 52,983,737 |
| | **소계** | | | | | **4h 46m** | **2,139** | **1,289** | **4,278** | **5,464,666** | **540,622,631** | **1,070,712** | **547,162,287** |

#### wf_6681bb3d-290 — `wf_6681bb3d-290` · 6 에이전트 · 실제 경과 시간 09-24 00:48 → 09-24 03:02 (2h 13m) · 에이전트 활동 시간 합산 3h 25m · 합계 413,760,109 토큰(출력 738,111)

| # | 에이전트(label) | 단계 | 상태 | 모델 | 시작(KST) | 소요 | API | 도구 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 합계 |
|--:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | F5-01:api-ingest-jobs-query | Implement | done | sonnet-5 | 09-24 00:48 | 38.6m | 308 | 183 | 616 | 753,597 | 73,605,728 | 155,953 | 74,515,894 |
| 2 | F5-02:mcp-server | Implement | done | sonnet-5 | 09-24 00:48 | 32.9m | 275 | 164 | 550 | 788,154 | 64,230,776 | 150,329 | 65,169,809 |
| 3 | F5-03:cli-and-full-e2e | Implement | done | sonnet-5 | 09-24 00:48 | 55.9m | 391 | 228 | 782 | 924,357 | 112,756,811 | 188,496 | 113,870,446 |
| 4 | F5:verify | Verify | done | sonnet-5 | 09-24 01:44 | 52.4m | 586 | 332 | 1,172 | 657,896 | 125,226,544 | 148,810 | 126,034,422 |
| 5 | F5:opus-review | Review | done | opus-5-5 | 09-24 02:37 | 3.5m | 28 | 18 | 56 | 237,403 | 2,117,244 | 14,964 | 2,369,667 |
| 6 | F5:review-fix | Review | done | sonnet-5 | 09-24 02:40 | 21.3m | 182 | 111 | 364 | 548,027 | 31,171,921 | 79,559 | 31,799,871 |
| | **소계** | | | | | **3h 25m** | **1,770** | **1,036** | **3,540** | **3,909,434** | **409,109,024** | **738,111** | **413,760,109** |

## 4. 산출 방법과 한계

- 각 에이전트 트랜스크립트(`agent-<id>.jsonl`)의 assistant 메시지 `usage` 필드를 합산했다. 재시도로 중복 과금된 호출이 있으면 실제 청구와 차이가 날 수 있다.
- 오케스트레이터 행은 메인 세션 트랜스크립트(`<session>.jsonl`) 기준이며, 컨텍스트 요약(compaction)으로 잘린 구간이 있으면 그 이전 호출은 포함되지 않을 수 있다.
- `running` 상태 에이전트는 보고 생성 시점까지의 부분 집계다. 워크플로우가 끝난 뒤 `node tools/usage-report.mjs --out PAYMENT.MD` 를 다시 실행하면 갱신된다.
- 소요 시간은 실제 경과 시간(첫 메시지~마지막 메시지)이며 대기·큐잉 시간을 포함한다. 워크플로우는 동시 실행(워크플로우당 최대 6)이므로 에이전트 소요 합계 ≠ 경과 시간.
