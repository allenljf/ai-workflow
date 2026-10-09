# 觀測數據平台

測試覆蓋率與測試狀態監控系統文件

## 目錄

1. [架構總覽](./architecture.md)
2. [開發指南](./development-guide.md)
3. [CI/CD 整合](./ci-integration.md)

## 快速連結

- [GitHub Issues Epic](https://github.com/kkday-it/kkday-android-member/issues/6650)
- [執行計劃](https://github.com/kkday-it/kkday-android-member/issues/6666)

## 相關 Scripts

| Script | 說明 |
|--------|------|
| `scripts/parse_jacoco.py` | 解析 JaCoCo XML 報告 |
| `scripts/parse_test_results.py` | 解析 JUnit XML 測試結果 |

## CI Workflows

| Workflow | 觸發條件 |
|----------|----------|
| `CI-UnitTest-Baseline` | push master/develop, schedule |
| `CI-UnitTest-Feature` | PR (非 release/*) |
| `CI-UnitTest-Release` | PR (release/* → master) |

## 數據收集架構

數據收集由 `app-health-dashboard/collector` 自動處理：
- 從 GitHub Actions artifacts 收集 JUnit/JaCoCo 報告
- 數據儲存於 TimescaleDB
- Grafana 視覺化 Dashboard
