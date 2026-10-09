# 架構總覽

## 系統架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GitHub Actions CI                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │ Unit Tests   │    │ JaCoCo       │    │ Python Scripts           │   │
│  │ (Gradle)     │───▶│ Report       │───▶│ • parse_jacoco.py        │   │
│  └──────────────┘    │ (XML)        │    │ • parse_test_results.py  │   │
│                      └──────────────┘    └────────────┬─────────────┘   │
│                                                       │                  │
│                                                       ▼                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Output Channels                                │   │
│  ├──────────────────┬───────────────────┬───────────────────────────┤   │
│  │ PR Comment       │ Job Summary       │ Artifacts                 │   │
│  │ (JaCoCo Report)  │ (GitHub Actions)  │ (coverage-report)         │   │
│  └──────────────────┴───────────────────┴───────────────────────────┘   │
│                                                       │                  │
└───────────────────────────────────────────────────────┼──────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    App Health Dashboard (Docker)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐              ┌──────────────────┐                 │
│  │ Python Collector │              │ TimescaleDB      │                 │
│  │ (自動收集        │─────────────▶│ (時序資料庫)      │                 │
│  │  GitHub Artifacts)│              │ Port: 5432       │                 │
│  └──────────────────┘              └────────┬─────────┘                 │
│                                             │                            │
│                                             ▼                            │
│                                    ┌──────────────────┐                 │
│                                    │ Grafana          │                 │
│                                    │ (Dashboard)      │                 │
│                                    │ Port: 3000       │                 │
│                                    └────────┬─────────┘                 │
│                                             │                            │
│                                             ▼                            │
│                                    ┌──────────────────┐                 │
│                                    │ Alerting         │                 │
│                                    │ (Slack/Email)    │                 │
│                                    └──────────────────┘                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 數據流向

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Code    │────▶│ Tests   │────▶│ Reports │────▶│Artifacts│────▶│ Storage │
│ Change  │     │ Run     │     │ Parse   │     │ Upload  │     │ Query   │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │               │               │               │
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  PR/Push      testDevelop      JSON files      GitHub          Grafana
              DebugUnitTest    coverage.json    Actions         Dashboard
                               test.json       Artifacts
                                                   │
                                                   ▼
                                            Python Collector
                                            (auto-fetch)
                                                   │
                                                   ▼
                                             TimescaleDB
```

## 技術堆疊

| 層級 | 技術 | 說明 |
|------|------|------|
| 測試執行 | Gradle + JaCoCo | 執行 Unit Test 並收集覆蓋率 |
| 報告解析 | Python 3 | 解析 XML 報告，輸出 JSON |
| 數據傳輸 | GitHub Actions Artifacts | 儲存報告供 Collector 取用 |
| 數據收集 | Python Collector | 自動從 Artifacts 收集數據 |
| 時序資料庫 | TimescaleDB | 儲存 metrics 數據 |
| 視覺化 | Grafana | Dashboard 與 Alerting |
| PR 整合 | madrapps/jacoco-report | PR 覆蓋率 Comment |

## 元件職責

### CI 端

| 元件 | 職責 |
|------|------|
| `jacocoTestReport` task | 生成 JaCoCo XML 覆蓋率報告 |
| `parse_jacoco.py` | 解析覆蓋率數據，輸出 JSON |
| `parse_test_results.py` | 解析測試結果，輸出 JSON |
| `jacoco-report` action | 在 PR 留言顯示覆蓋率 |
| GitHub Actions Artifacts | 儲存報告供後續收集 |

### Collector 端

| 元件 | 職責 |
|------|------|
| Python Collector | 定期從 GitHub Artifacts 收集報告 |
| JUnit Reports Collector | 解析 JUnit/JaCoCo XML |
| TimescaleDB | 儲存時序數據 |
| Grafana | 視覺化 Dashboard |
| Grafana Alerting | 覆蓋率異常告警 |

## Metrics 命名規範

| Metric Name | 類型 | 說明 |
|-------------|------|------|
| `line_coverage` | float | 行覆蓋率 (%) |
| `branch_coverage` | float | 分支覆蓋率 (%) |
| `method_coverage` | float | 方法覆蓋率 (%) |
| `tests_total` | int | 總測試數 |
| `tests_passed` | int | 通過數 |
| `tests_failed` | int | 失敗數 |
| `tests_skipped` | int | 跳過數 |
| `execution_time_ms` | int | 執行時間 (毫秒) |

## Resource Attributes

| Attribute | 說明 |
|-----------|------|
| `app_id` | 應用程式 ID |
| `test_type` | `unit` / `e2e` / `integration` |
| `branch` | 分支名稱 |
| `commit_sha` | Commit SHA |
