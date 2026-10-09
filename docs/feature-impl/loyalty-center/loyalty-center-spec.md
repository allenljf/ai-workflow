# 會員禮遇中心（Loyalty Center）- Android 開發 Spec

> Branch: `feature/KKAPP-5042/member_loyalty`
> 來源：[Figma](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-58781&m=dev) / [SA/SD](https://kkday.atlassian.net/wiki/spaces/APP/pages/1759838737) / [PRD](https://docs.google.com/document/d/1S96XRWlTsNStaRyj87HBeHe4CgPzcvXY2pHSieEnkaA)

---

## 1. 頁面概覽

全新 Compose 頁面，取代現有 `LoyaltyActivity`（MVP + RecyclerView）。
頁面位於 Member Activity 內，透過 Navigation 切換（非獨立 Activity）。

### 頁面結構（由上至下）

```
┌─────────────────────────────────┐
│  TopAppBar（← 會員禮遇中心  ⓘ）  │
├─────────────────────────────────┤
│  等級進度條 Tab（白銀/黃金/白金/黑鑽）│  ← sticky
├─────────────────────────────────┤
│  主視覺動畫區（依等級切換 resource）  │
├─────────────────────────────────┤
│  會員等級資訊卡                    │
├─────────────────────────────────┤
│  福利權益區塊（Benefit Cards）      │
├─────────────────────────────────┤
│  任務區塊（最多 2 項）              │
├─────────────────────────────────┤
│  常見問題（3 項 Row → WebView）    │
└─────────────────────────────────┘
```

### 頁面進入方式
- 會員頁點擊「會籍禮遇」→ Navigation 切換
- Deeplink 支援（行銷需要）
- 未登入時點擊 deeplink → 導向登入頁

---

## 2. 各區塊規格

### 2.1 TopAppBar
| 元素 | 規格 |
|------|------|
| 左側 | 返回箭頭 `←` |
| 標題 | 「會員禮遇中心」 |
| 右側 | ⓘ icon → 點擊開啟會籍禮遇中心 SEO（inapp webview） |

### 2.2 等級進度條 / Tab

**顯示：** 白銀會員 → 黃金會員 → 白金會員 → 黑鑽會員（4 個 tier）

**三種狀態的文字：**
| 狀態 | 文字 | lokalise key |
|------|------|-------------|
| 超過等級 | 「您目前等級是[等級名稱]」 | `LoyaltyPg_TierWithName` |
| 當前等級 | 「您目前的等級」 | `LoyaltyPg_TierNow` |
| 未達到等級 | 「待解鎖」 | `LoyaltyPg_TierLocked` |

**交互：**
- 左右滑動可切換等級
- 點擊箭頭可切換等級
- **頁面向下滑動超過進度條 → 改為 sticky tab 顯示**
  - 用戶左右切換時 tab 也須跟著切換
  - 滑超過福利區塊時 tab 收起

**主視覺動畫（等級 icon 區）：**
- 依等級顯示不同動畫 resource（Lottie 或 image）
- 先用白銀等級 resource 開發，後續根據等級切換

### 2.3 會員等級資訊卡（Level Card）

**三種狀態：**

| 狀態 | 顯示內容 | lokalise key |
|------|---------|-------------|
| 超過等級 | 「您已高於該等級」 | `LoyaltyPg_FinshText` |
| 當前等級（白銀/黃金/白金） | 「還需消費約 [幣別][金額] 可升級 [下個等級] 會員」+ 經驗進度條 + 有效日期 | `LoyaltyPg_UpgradeText` |
| 當前等級（黑鑽） | 「還需消費約 [幣別][金額] 可保級黑鑽會員」+ 經驗進度條 + 有效日期 | `LoyaltyPg_DiamondText` |
| 未達到等級 | 同當前等級文字（跳級也顯示相同，ex: 白銀看黑鑽 → 顯示到黃金的金額） | `LoyaltyPg_UpgradeText` |

**經驗值進度條：**
- 字串：「[當前 exp] / [目標 exp] 經驗值明細」
- lokalise key: `LoyaltyPg_ExpDetail`
- 以下個等級的經驗值為分母
- 點擊「經驗值明細」→ 跳轉經驗值明細頁面（僅當前等級可點擊）

**有效日期：**
| 條件 | 顯示 | lokalise key |
|------|------|-------------|
| 白銀 | 「無期限」 | `LoyaltyPg_NoLimit` |
| 黃金/白金/黑鑽 | 「有效時間：」+ 「[年] 年 2月底」 | `LoyaltyPg_UpgradeTime` / `LoyaltyPg_Endtime` |

**金額換算邏輯：**
- 10 經驗值 = 1 USD
- 前端判斷在地化幣別，後端給金額
- 使用既有匯率 API

**各會員門檻：**
| 等級 | GMV (USD) | EXP |
|------|-----------|-----|
| 白銀 | 0 | 0 |
| 黃金 | $250 | 2,500 |
| 白金 | $500 | 5,000 |
| 黑鑽 | $1,500 | 15,000 |

### 2.4 福利權益區塊（Benefit Cards）

**Title：** 「您可享權益 [N] 項」

**三種等級狀態下的顯示：**

| 狀態 | 福利卡行為 | 按鈕 |
|------|----------|------|
| 超過等級 | 改為描述類福利呈現（靜態 Row），順序：福利卡在上、靜態在下 | 無按鈕 |
| 當前等級 | 正常卡片顯示 | 「領取」→ 領取後變「去使用」 |
| 未達到等級 | 卡片帶鎖 icon | btn disabled + 「待解鎖」, 點擊展開 tooltip |

**Coupon 領取邏輯：**
- 單張 Coupon → 自動領取
- 多張 Coupon → 開啟 BottomSheet 選擇
- 領取後按鈕變為「去使用」→ 點擊開啟 coupon bottom sheet

**福利卡數量規則：**
- 最多顯示 10 個（不會超過）
- 大於 2 個：可左右滑動，但不影響等級切換
- 數量會影響顯示的排版樣式（1個/2個/3個以上）

**交互：**
- 左右滑動可切換 tab，上方進度條隨之移動
- 向下滑動超過進度條 → tab 顯示
- 滑超過福利區塊 → tab 收起

### 2.5 任務區塊

**Title：** 「做任務獎勵」（`LoyaltyPg_MissionTitle`）
**Subtitle：** 「升級可接更多任務」（`LoyaltyPg_MissionSubtitle`）

**顯示規則：**
- 最多顯示 2 項任務
- 只顯示會員可參與的任務（依等級）
- 顯示條件：
  - 存在於「任務挑戰」
  - start_time / end_time 有效期間內
  - `mission.is_visible = TRUE`
  - 用戶當前等級的任務
  - 無論需要接單或不接單都顯示
- 排序：mission system 排序 > start_time > mission_id（大在前）
- 已領取、已完成、已過期 → 不顯示
- 為空：「目前沒有新任務，請敬啟期待！」（`LoyaltyPg_MissionNone`）

**交互：**
- 不在左右切換的範圍內（福利權利滑動不影響任務區）
- 點擊 → 進到任務頁面（inapp webview），統一進到任務挑戰 tab

**任務 API：** `GET v2/mission/list/status`（帶 `statuses[]=NEW&statuses[]=PROG`）

### 2.6 常見問題

**交互：**
- 不在左右切換範圍內
- 顯示 3 個常見問題 Row
- 點擊 → 進到幫助中心（inapp webview）

---

## 3. API 清單

| API | 用途 | 狀態 |
|-----|------|------|
| `GET /v2/loyalty/member/info` | 取得會員資訊（等級、經驗、到期日） | 既有，需新增 tier 等級 |
| `GET /v2/loyalty/tier/benefit` | 取得會籍權益 | 既有 |
| `GET /v2/loyalty/tiers/benefit_reward` | 取得會籍權益獎勵實體 | 既有或新增 |
| `GET /v2/mission/list/status` | 依狀態取得會員任務列表 | 既有 |
| `GET /v2/member/coupons/claimed` | 查詢折扣券會員是否已領取 | 新增 |
| `GET /v2/member/points` | 取得 KKPoints（換算金額用） | 既有 |

> API 都還沒好，邊做邊討論

---

## 4. Lokalise 字串清單

| key | 文字 | 用途 |
|-----|------|------|
| `LoyaltyPg_TierWithName` | 您目前等級是%s | 超過等級提示 |
| `LoyaltyPg_TierNow` | 您目前的等級 | 當前等級提示 |
| `LoyaltyPg_TierLocked` | 待解鎖 | 未達等級提示 |
| `LoyaltyPg_FinshText` | 您已高於該等級 | 超過等級資訊卡 |
| `LoyaltyPg_UpgradeText` | 還需消費約 %s%d 可升級 %s 會員 | 升等提示 |
| `LoyaltyPg_DiamondText` | 還需消費約 %s%d 可保級黑鑽會員 | 黑鑽保級提示 |
| `LoyaltyPg_UpgradeTime` | 有效時間： | 有效日期標題 |
| `LoyaltyPg_Endtime` | %d 年 2月底 | 到期日 |
| `LoyaltyPg_NoLimit` | 無期限 | 白銀無期限 |
| `LoyaltyPg_ExpDetail` | %d / %d 經驗值明細 | 經驗進度條 |
| `LoyaltyPg_MissionTitle` | 做任務獎勵 | 任務區標題 |
| `LoyaltyPg_MissionSubtitle` | 升級可接更多任務 | 任務區副標題 |
| `LoyaltyPg_MissionNone` | 目前沒有新任務，請敬啟期待！ | 任務為空 |
| `LoyaltyPg_MissionMoreBtn` | 查看更多任務 | 查看更多按鈕 |

---

## 5. 現有架構分析 & 遷移策略

### 現有（需取代）
```
LoyaltyActivity (MVP + RecyclerView)
├── LoyaltyPresenter
├── LoyaltyAdapter + 多個 Delegate
├── LoyaltyMvpView
└── LoyaltyViewInfoConverter
```

### 新架構（Compose + MVVM）
```
app/src/main/java/com/kkday/member/view/user/loyalty/
├── LoyaltyCenterScreen.kt          # 主 Composable
├── LoyaltyCenterViewModel.kt       # ViewModel + StateFlow
├── components/
│   ├── TierProgressBar.kt          # 等級進度條 + sticky tab
│   ├── TierVisualSection.kt        # 主視覺動畫區
│   ├── LevelCard.kt                # 會員等級資訊卡
│   ├── BenefitSection.kt           # 福利權益區塊
│   ├── BenefitCard.kt              # 單張福利卡
│   ├── MissionSection.kt           # 任務區塊
│   └── FaqSection.kt               # 常見問題
├── model/
│   └── LoyaltyCenterUiState.kt     # UI State data classes
```

### 進入方式改造
- 現有：`LoyaltyActivity.launch(context)` （獨立 Activity）
- 新增：在 Member Activity 的 Navigation Graph 新增 route
- `MemberPageFragment` → Navigation → `LoyaltyCenterScreen`
- 保留 deeplink 支援

### Data Layer
- 既有 model 可複用：`LoyaltyMemberInfo`, `LoyaltyTierBenefits`, `LoyaltyTierBenefitInfo`, `TierBenefitItem`
- 新增 model：Coupon claimed 狀態、benefit_reward 實體
- 既有 API：`KKdayService` 已有 `getLoyaltyMemberInfo()`, `getLoyaltyTierBenefits()`
- 新增 API：`benefit_reward`, `coupons/claimed`

### UseCase
- 既有可複用：`GetLoyaltyMemberInfoUseCase`
- 新增：
  - `GetTierBenefitRewardUseCase`
  - `GetMissionListUseCase`
  - `ClaimCouponUseCase`
  - `GetCouponClaimedStatusUseCase`

---

## 6. 任務拆分

### Phase 1：基礎架構 & 頁面骨架
| # | Task | 預估 |
|---|------|------|
| 1.1 | 建立 `LoyaltyCenterScreen` + `LoyaltyCenterViewModel` 骨架 | 0.5d |
| 1.2 | Navigation route 設定（Member Activity 內切換） | 0.5d |
| 1.3 | Deeplink 支援 | 0.5d |
| 1.4 | UI State data class 定義（`LoyaltyCenterUiState`） | 0.25d |

### Phase 2：主視覺 & 等級切換
| # | Task | 預估 |
|---|------|------|
| 2.1 | `TierProgressBar` 元件（4 tier 顯示 + 箭頭切換） | 0.5d |
| 2.2 | `TierProgressBar` sticky tab 行為（滑動超過進度條時變 tab，超過福利區收起） | 1d |
| 2.3 | `TierVisualSection` 主視覺區（先用白銀 resource，後續依等級切換） | 0.5d |
| 2.4 | HorizontalPager 左右滑動切換等級邏輯 | 0.5d |

### Phase 3：等級資訊卡
| # | Task | 預估 |
|---|------|------|
| 3.1 | `LevelCard` 元件（超過等級 / 當前等級 / 未達等級 三態） | 0.5d |
| 3.2 | 經驗進度條 UI + 金額換算邏輯（EXP → USD → 在地化幣別） | 0.5d |
| 3.3 | 有效日期顯示邏輯（無期限 / 年 2月底） | 0.25d |
| 3.4 | 串接 `GetLoyaltyMemberInfoUseCase`（復用既有） | 0.25d |

### Phase 4：福利權益
| # | Task | 預估 |
|---|------|------|
| 4.1 | `BenefitSection` + `BenefitCard` 元件（三態：超過/當前/未達） | 1d |
| 4.2 | 福利卡數量響應式排版（1個/2個/3+水平滾動） | 0.5d |
| 4.3 | Coupon 領取邏輯（單張自動領取 / 多張 BottomSheet） | 0.5d |
| 4.4 | 串接 `benefit` + `benefit_reward` API | 0.5d |
| 4.5 | Coupon claimed 狀態 API 串接 | 0.25d |

### Phase 5：任務 & 常見問題
| # | Task | 預估 |
|---|------|------|
| 5.1 | `MissionSection` 元件（顯示最多 2 項任務） | 0.5d |
| 5.2 | 串接 `GET v2/mission/list/status` API | 0.5d |
| 5.3 | 任務排序與篩選邏輯 | 0.25d |
| 5.4 | `FaqSection` 元件（3 個 Row → WebView） | 0.25d |

### Phase 6：整合 & 打磨
| # | Task | 預估 |
|---|------|------|
| 6.1 | ViewModel 整合所有 API，合併 UI State | 0.5d |
| 6.2 | Loading / Error / Empty 各狀態處理 | 0.5d |
| 6.3 | 頁面滑動交互統整（進度條 sticky / tab 切換 / 福利滑動獨立） | 0.5d |
| 6.4 | 等級動畫 resource 切換（依後續提供的 resource） | 0.25d |
| 6.5 | 埋點（待補充） | 0.5d |

### Phase 7：測試
| # | Task | 預估 |
|---|------|------|
| 7.1 | ViewModel 單元測試 | 0.5d |
| 7.2 | UseCase 單元測試 | 0.5d |
| 7.3 | API 串測 | 1d |
| 7.4 | 自測 | 1d |

---

## 7. 疑問清單

### 架構 & 導航
1. **Navigation 方式確認**：新頁面是用 Jetpack Navigation Compose 還是維持 Activity 啟動？你提到「與 member 在同一個 activity 用 nav 切換」，目前 `MemberPageFragment` 是 Fragment，新頁面是要 Fragment host Compose 還是全 Compose Navigation？
2. **舊 `LoyaltyActivity` 處理**：是保留共存（feature flag 切換）還是直接取代？

### API & 資料
3. **`GET /v2/loyalty/tiers/benefit_reward` API 格式**：SA/SD 提到此 API 但沒有 response schema，需要確認回傳格式
4. **`GET /v2/member/coupons/claimed` API 格式**：SA/SD 有示範 `{"COUPON_1": true, "COUPON_2": false}`，確認是否最終格式？
5. **Coupon 領取 API**：領取 Coupon 的 POST API endpoint 是什麼？（SA/SD 未定義）
6. **金額換算 API**：匯率轉換使用哪隻既有 API？`toUsdRate` 是在 points API 回傳的嗎？

### UI & 設計
7. **主視覺動畫 resource**：白銀等級的動畫 resource 格式（Lottie JSON / GIF / 靜態圖）？其他等級的 resource 何時提供？
8. **福利卡圖片**：`TierBenefitItem.image_url` 是遠端圖片還是本地 resource？
9. **常見問題的 3 個 FAQ 連結**：是固定 URL 還是從 API 取得？

### 字串 & i18n
10. **Lokalise key 是否都已建立**？還是需要 PM 先補上？目前 `strings.xml` 不可修改，是否走 Lokalise → 自動同步流程？

### 交互細節
11. **sticky tab 的觸發位置**：「向下滑動超過等級進度條」的精確位置是進度條底部嗎？「超過福利區塊收起」的精確位置？
12. **未登入狀態**：禮遇中心是否支援未登入瀏覽？PRD 提到「未登入的功能統一都改為顯示，但點擊開啟登入頁」
