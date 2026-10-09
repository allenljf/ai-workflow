# Checklist · 碰到 RxJava 既有程式碼

專案有 **194 個檔案** import `io.reactivex`，RxJava2 已於 2021-02-28 EOL。你幾乎一定會碰到。

**核心原則：收斂邊界，不要整段重寫。**

## 先判斷你在哪一層

| 你要改的地方 | 做法 |
|-------------|------|
| 新功能，完全不碰既有 Rx | 全用 Coroutine / Flow，不要 import `io.reactivex` — `no-new-rxjava` |
| 新程式碼要**呼叫**既有 Rx API | 在 Repository 邊界用 `.await()` / `.asFlow()` 收斂，往上只暴露 suspend / Flow |
| 要改既有 Rx 鏈的**內容** | 維持 Rx，只改你要改的部分。不要順手轉 Flow |
| 既有 Rx 鏈**整段要重寫** | 這是獨立任務，不要塞在功能 PR 裡 |

## 邊界規則

- [ ] **Rx 型別不得出現在 domain 層的簽章**（`:domain:contract` / `:domain:usecase`）
- [ ] **Rx 型別不得出現在 ViewModel 對 UI 的公開 API**
- [ ] 允許 Rx 存在的位置：既有 `:data` 層實作內部、既有 Presenter、既有 `KKdayService`
- [ ] 新的 Repository 介面方法一律 `suspend fun` 或 `Flow<T>`，即使實作內部包了 Rx

## 收斂寫法

- [ ] 用 `kotlinx-coroutines-rx2` 的 interop：
      `Single<T>.await()`、`Observable<T>.asFlow()`、`Completable.await()`
- [ ] 收斂點放在 **Repository 實作內**，不要放在 ViewModel
- [ ] 收斂後的錯誤要轉成 domain error，不要讓 Rx 的 `OnErrorNotImplementedException` 往上跑

## 生命週期

- [ ] **`CompositeDisposable` 與 `viewModelScope` 不得混用在同一個類別**（兩套取消機制會互相看不見）
- [ ] 既有類別已用 `CompositeDisposable` → 新增的非同步也走 Rx，或整個類別一起改
- [ ] 新類別 → 只用 `viewModelScope` / 注入的 scope
- [ ] `Disposable` 有在正確時機 `dispose()`（`onCleared` / `onDestroyView`）
- [ ] 沒有訂閱後不管的 `subscribe()`（洩漏來源）

## 特別注意 `BaseViewModel`

`libs/base/.../BaseViewModel.kt` 內建 `CompositeDisposable` 與 `Observable.subscribeWithAutoDispose()` 擴充，**繼承它就會被綁進 RxJava2**。

- [ ] 新 ViewModel **不要**繼承 `libs/base` 的 `BaseViewModel`
- [ ] 直接繼承 `androidx.lifecycle.ViewModel`
- [ ] loading 狀態自己放進 UiState，不要用它的 `showLoading`（那是 public MutableLiveData，87 檔共用）

## 網路層

- [ ] 新 endpoint 加在新的 `*ApiService`（suspend），**不要**加進 `KKdayService.kt`
      （該檔 1451 行、199 個 Rx endpoint，是最大的 Rx 來源）
- [ ] 既有 Rx endpoint 若要新增欄位 → 改 DTO 即可，不用改 endpoint 型別

## Reductor 相關

Reductor 對 UI 的唯一出口就是 `Observable<AppState>`（61 個 Presenter 靠它）。

- [ ] **不要**為了去 Rx 而動 Reductor 的 store/subscribe 機制
- [ ] 新畫面用 MVVM + UDF，不接 `Observable<AppState>`（紅線 D4）
- [ ] 混血畫面（`setContent` + Presenter，共 30 個）：新增的 Compose 區塊用 ViewModel，不要從 Presenter 拉狀態

## 收尾

- [ ] 沒有新增 `import io.reactivex`（除非是既有 Rx 檔案的內部修改）
- [ ] 編譯 + detekt + 測試通過
- [ ] 本次未收斂的 Rx 邊界已登記 `90-migration-ledger.md#m-09`
