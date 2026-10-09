# 開發指南

## Scripts 使用方式

### 1. 解析 JaCoCo 覆蓋率報告

```bash
# 基本使用
python3 scripts/parse_jacoco.py app/build/reports/jacoco/test/jacocoTestReport.xml

# 指定報告類型並格式化輸出
python3 scripts/parse_jacoco.py \
  app/build/reports/jacoco/test/jacocoTestReport.xml \
  -t unit \
  --pretty

# 輸出到檔案
python3 scripts/parse_jacoco.py \
  app/build/reports/jacoco/test/jacocoTestReport.xml \
  -t unit \
  -o coverage-metrics.json
```

**輸出範例：**

```json
{
  "line_coverage": 75.5,
  "branch_coverage": 68.3,
  "method_coverage": 82.1,
  "instruction_coverage": 80.0,
  "lines_covered": 1234,
  "lines_total": 1635,
  "branches_covered": 500,
  "branches_total": 732,
  "report_type": "unit",
  "timestamp": "2026-01-17T08:30:00+00:00"
}
```

### 2. 解析測試結果

```bash
# 基本使用（支援 glob 模式）
python3 scripts/parse_test_results.py \
  'app/build/test-results/testDevelopDebugUnitTest/*.xml'

# 指定類型並格式化
python3 scripts/parse_test_results.py \
  'app/build/test-results/testDevelopDebugUnitTest/*.xml' \
  -t unit \
  --pretty

# 輸出到檔案
python3 scripts/parse_test_results.py \
  'app/build/test-results/testDevelopDebugUnitTest/*.xml' \
  -t unit \
  -o test-metrics.json
```

**輸出範例：**

```json
{
  "total": 109,
  "passed": 100,
  "failed": 9,
  "skipped": 0,
  "errors": 0,
  "execution_time_seconds": 5.064,
  "test_suites": 21,
  "test_type": "unit",
  "timestamp": "2026-01-17T08:30:00+00:00",
  "failed_tests": [
    {
      "class": "com.kkday.member.LoginUseCaseTest",
      "method": "testLoginFailure",
      "message": "Expected 401 but was 500",
      "type": "AssertionError"
    }
  ]
}
```

## 本地開發流程

### 執行測試並生成覆蓋率報告

```bash
# 1. 執行 Unit Test 並生成報告
./gradlew testDevelopDebugUnitTest jacocoTestReport

# 2. 報告位置
# HTML: app/build/reports/jacoco/test/html/index.html
# XML:  app/build/reports/jacoco/test/jacocoTestReport.xml

# 3. 解析報告
python3 scripts/parse_jacoco.py \
  app/build/reports/jacoco/test/jacocoTestReport.xml \
  --pretty
```

## 數據收集架構

數據收集由 `app-health-dashboard/collector` 自動處理：

1. **GitHub Actions** 執行測試並上傳 artifacts
2. **Python Collector** 定期從 GitHub API 收集 artifacts
3. **JUnit Reports Collector** 解析 JaCoCo/JUnit XML
4. **TimescaleDB** 儲存時序數據
5. **Grafana** 視覺化 Dashboard

### Collector 設定

```bash
# 啟動 Dashboard 服務
cd app-health-dashboard
docker compose up -d

# 查看 collector 日誌
docker compose logs collector --tail 50

# 手動執行 collector
docker compose exec collector python main.py --once
```

## 單元測試

```bash
# 執行所有 script 測試
cd scripts
python3 test_parse_jacoco.py -v
python3 test_parse_test_results.py -v
```
