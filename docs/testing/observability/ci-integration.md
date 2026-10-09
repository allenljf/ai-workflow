# CI/CD 整合

## Workflow 架構

```
CI-UnitTest-Baseline.yml  ─┐
CI-UnitTest-Feature.yml   ─┼─► CI-UnitTest.yml (可重用 workflow)
CI-UnitTest-Release.yml   ─┘
```

## 觸發條件

| Workflow | 事件 | 條件 |
|----------|------|------|
| CI-UnitTest-Baseline | push | master, develop 分支 |
| CI-UnitTest-Baseline | schedule | 每日 03:00 UTC |
| CI-UnitTest-Feature | pull_request | 非 release/* 分支 |
| CI-UnitTest-Release | pull_request | release/* → master |

## 監控路徑

只有以下路徑變更時才會觸發：

```yaml
paths:
  - "app/src/**"
  - "domain/**"
  - "data/**"
  - "feature/**"
  - "shared/**"
  - "build.gradle.kts"
  - "app/build.gradle.kts"
```

## 執行步驟

```
1. Checkout repository
2. Setup JDK 17
3. Setup Gradle (with caching)
4. Run Unit Tests with Coverage
5. Parse Coverage Report
6. Parse Test Results
7. Upload Coverage Report (artifact)
8. Upload Test Results (artifact)
9. JaCoCo Report PR Comment (PR only)
10. Job Summary
```

## 數據收集

Metrics 數據由 `app-health-dashboard/collector` 自動從 GitHub Actions Artifacts 收集，無需手動推送。

Collector 會定期：
1. 掃描 GitHub Actions artifacts
2. 下載 coverage-report 和 test-results
3. 解析 JaCoCo/JUnit XML
4. 寫入 TimescaleDB

## PR Comment

在 PR 會自動留言顯示覆蓋率：

```markdown
## 📊 Unit Test 覆蓋率報告

| Overall Coverage | Changed Files Coverage |
|------------------|------------------------|
| 72.5% ✅         | 85.3% ✅               |

### 變更檔案覆蓋率
| File | Coverage |
|------|----------|
| LoginUseCase.kt | 92% |
| UserRepository.kt | 78% |
```

### 門檻設定

| 類型 | Overall | Changed Files |
|------|---------|---------------|
| Unit Test | 60% | 80% |
| E2E | 50% | 60% |

低於門檻顯示 ❌，通過顯示 ✅

## Artifacts

每次執行會上傳以下 artifacts（保留 7 天）：

| Artifact Name | 內容 |
|---------------|------|
| `coverage-report` | JaCoCo HTML/XML 報告 + metrics JSON |
| `test-results` | JUnit XML 測試結果 |

Collector 會自動從這些 artifacts 收集數據。

## Job Summary

執行完成後會在 Actions 頁面顯示摘要：

| Metric | Value |
|--------|-------|
| Tests | 109 |
| Passed | 100 |
| Failed | 9 |
| Line Coverage | 75.5% |
| Branch Coverage | 68.3% |
