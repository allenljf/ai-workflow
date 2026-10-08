# Spring Boot 本機 API 對照

這是合成資料的教學模組。Controller→Service→Repository 分開 schema、業務與交易；服務端 token→tenant，body 不接受 tenant。SQLite schema v1 與 Python JobStore 相同，可讓 Python worker 對同一檔案操作；Java API 不會自己啟動 worker。公開契約在 `../contracts/openapi.yaml`。

## 執行

需要 Java 21–26、Maven 3.9.x。於本模組執行 `mvn verify`；再執行 `mvn spring-boot:run`。預設 loopback 8080，只有 `/health` 不需要身份。以環境變數 `FDE_TOKEN_ONE`、`FDE_TOKEN_TWO` 設定兩個不同的本機測試 token，分別映射 one/two；不要用公司正式 token。`FDE_DB_PATH` 指向忽略的 runtime 路徑。沒有配置 token 時所有業務端點回 401。

POST `/jobs` body `{"operation":"import"}`，header `Authorization: Bearer …`、`Idempotency-Key: …`。同 key/同 body 回相同 id；不同 body 409。GET `/jobs/id`；POST `/jobs/id/cancel`。POST `/rag/query` body `{"query":"refund"}` 回合成政策引用；其他問題拒答。SQLite migrate 只接受版本 0/1，未知版本拒絕啟動；先備份 DB 再改 schema。

## 選配 Spring AI

加 JVM properties `-Dfde.provider=ollama -Dfde.ollama.model=<已安裝模型>`（啟動 jar 時放在 `-jar` 前）。endpoint 預設 `http://127.0.0.1:11434`，只允許 loopback HTTP，5 秒連線/30 秒讀取 timeout，不 follow redirect、不自動拉 model。Spring AI OllamaChatModel 輸出另做狀態、答案、授權引用檢查；格式合法仍不證明語義正確。模組只用合成政策，不是文件搜尋引擎；完整版本化檢索請用 Python lab。fixture 是預設，真模型推論與品質尚未驗證。長任務 worker 的外部呼叫仍須用 begin_external_step/receipt 契約，不能將網路失敗自動視為可重試。

## 固定版本與驗證

查核 2026-10-08：[Spring Boot 4.1.1 Java 相容範圍](https://docs.spring.io/spring-boot/system-requirements.html)、[Spring AI 2.x 與 Boot 4.x](https://github.com/spring-projects/spring-ai/blob/main/spring-ai-docs/src/main/antora/modules/ROOT/pages/getting-started.adoc)、[Maven 官方下載與 SHA512](https://maven.apache.org/download.cgi)、[SQLite JDBC releases](https://github.com/xerial/sqlite-jdbc/releases)。pom 固定 Boot 4.1.1、AI BOM 2.0.1、SQLite JDBC 3.53.4.0；前兩者 Apache-2.0，JDBC Apache-2.0/BSD-2-Clause。工具 Maven 3.9.16 tar 已比對官方 SHA512；依賴由 Maven Central 解析，未 vendor 第三方 binary。

JUnit 使用真 loopback HTTP 與 SQLite，驗證 401、跨租戶 404、201/200/409、取消與非法輸出；fixture 結果只證明契約，不宣稱企業 pilot、效能或雲端部署完成。DB、憑證與 target 不加入 Git。
