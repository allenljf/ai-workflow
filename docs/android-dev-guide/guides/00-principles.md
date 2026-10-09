# 00 · 核心原則

這份檔案定義「為什麼要這樣寫」的八條原則，每次動手前都讀一次。
它**不定義任何可稽核的規則**——具體條文由各領域檔負責，每條原則末尾標了落實它的檔案。
違反原則不必然違反某條規則，但幾乎都會在幾個月後變成回不去的技術債。

| 想找 | 去哪 |
|---|---|
| 不可協商的紅線清單、實作順序 | [../AGENTS.md](../AGENTS.md) |
| 分層邊界、依賴方向、「這段邏輯放哪一層」判斷表 | [01-architecture.md](01-architecture.md) |
| 全部規則（機器可讀：id / level / enforce / check） | [../rules.yaml](../rules.yaml) |

---

## 1 · 關注點分離

每個類別只有一個改變的理由。畫面元件負責把狀態畫出來、把使用者操作回報出去；「資料從哪來、怎麼組合、失敗了怎麼辦」是別人的責任。
系統可以隨時銷毀 Activity、Fragment 或 Composable，任何被塞在它們裡面的邏輯會跟著消失，也無法在純 JVM 測試中執行。
症狀：Composable 或 Activity 裡出現網路呼叫、快取判斷、欄位驗證。

落實於：[01-architecture](01-architecture.md)、`08-ui-state`

## 2 · Data driven UI

畫面是狀態的函式：`UI = f(state)`。同一份狀態必須畫出同一個畫面，不允許有藏在 View 或 Composable 內部的第二份真相。
一旦改成命令式地一格一格改畫面（顯示這個、隱藏那個），狀態組合數會爆炸，最後出現「只有從某個入口進來才會壞」這種無法重現的 bug。
症狀：用一連串 `setVisibility` / `setText` 拼出畫面；Composable 內部自己 `remember` 了一份不同步的資料副本。

落實於：`08-ui-state`、`09-compose-api`、`10-compose-state`

## 3 · 單一資料來源（SSOT）

每一種資料只有一個可寫入的擁有者，其他人只能觀察它公開的 `Flow`，要改資料只能呼叫擁有者提供的方法。
同一份資料被多處各存一份的當下不會壞，壞的是三個月後——列表已刪除但詳情頁還在、下拉刷新後兩個畫面數字不一致。
症狀：ViewModel、Repository、某個 Manager 各自持有一份可寫入的清單。

落實於：`05-data-layer`、`07-persistence`

## 4 · 單向資料流（UDF）

狀態只往下流（Data → ViewModel → UI），事件只往上傳（UI 呼叫 ViewModel 的方法）。中間任何一段都不得逆向寫入。
UDF 的價值在於除錯：狀態變成錯的，一定是某個往下流的環節算錯，可以單向回推。雙向寫入則沒有這個保證，你得同時懷疑所有持有者。
症狀：Composable 直接改 ViewModel 的欄位或直接呼叫資料層。

落實於：[01-architecture](01-architecture.md)、`08-ui-state`

## 5 · 依賴反轉

上層依賴抽象、下層提供實作，由組裝點（DI）綁定兩者。ViewModel 認識的是 `OrderRepository` 介面，不是 `DefaultOrderRepository`，更不是 `OrderApiService`。
這條決定了「換掉一個實作要動幾個檔案」。依賴具體型別時，換資料來源、加一層快取、在測試裡塞假資料，都會擴散成跨模組的大改。
症狀：建構子參數是實作類別；測試必須起真的網路或資料庫才跑得動。

落實於：[01-architecture](01-architecture.md)、`03-dependency-injection`

## 6 · 不可變狀態

對外公開的一律不可變：欄位用 `val`、集合用唯讀型別、狀態用 `StateFlow` 而非 `MutableStateFlow`。要改狀態就產生新的實例，由擁有者寫回。
可變狀態被非擁有者偷改時，沒有任何一行程式碼可以指認兇手；Compose 也無法靠等值比較判斷「這次沒變」而跳過重組。
症狀：public `var`、公開的 `MutableList`、對外暴露的 `MutableStateFlow`。

落實於：`05-data-layer`、`08-ui-state`

## 7 · 明確的錯誤處理

錯誤是預期中的分支，不是意外。每個跨層邊界都要先決定「這裡的失敗長什麼樣、由誰翻譯」——技術例外在資料層邊界收斂成語意化的錯誤型別，UI 只面對它能顯示的東西。
沒有明確定義的錯誤會用兩種方式報復你：被空的 `catch` 吞掉變成永遠轉圈的畫面，或原封不動衝到 UI 變成使用者看不懂的訊息。取消（`CancellationException`）不是失敗，被當成失敗處理會在使用者離開畫面後彈出錯誤。
症狀：`catch (e: Exception) {}`；UI 層 import 了網路框架的例外型別。

落實於：`05-data-layer`、`12-coroutines-flow`

## 8 · 可測試性是設計約束

介面定下來的那一刻就要能回答「這個怎麼測」。需要注入 dispatcher 嗎？依賴換得成 fake 嗎？時間、亂數、目前使用者是不是也該注入？答案會反過來改變介面設計。
事後才問，就只剩下 Robolectric、`Thread.sleep`、以及 mock 五個東西才跑得起來的測試——那是設計問題，不是測試問題。
症狀：為了測一個函式必須先建立整個 Android 環境。

落實於：`15-testing`、`03-dependency-injection`

---

## 原則互相衝突時

會衝突的通常是「SSOT／不可變」與「效能」，或「分層」與「這次只是個小功能」。處理順序：

1. 先滿足正確性與可測試性——這兩項的債最貴。
2. 效能問題要先量測再破例，不要憑感覺提前優化（見 `16-performance`）。
3. 真的要偏離，在 PR 說明「偏離哪一條、為什麼、什麼條件下會改回來」。**不要無聲偏離。**
