#!/usr/bin/env python3
"""Android 開發準則稽核器 — 獨立執行，不依賴任何 AI 工具。

規則定義在 ../rules.yaml，本腳本只是執行器。新增規則不需要改這支程式。

用法：
    python3 check-rules.py                    # 稽核 git 工作區有改動的 .kt
    python3 check-rules.py --staged           # 稽核 git staged 的 .kt（適合 pre-commit）
    python3 check-rules.py --diff origin/main # 稽核與某個 ref 的差異（適合 CI）
    python3 check-rules.py --all              # 稽核整個專案（第一次導入時看全貌）
    python3 check-rules.py --files A.kt B.kt  # 稽核指定檔案
    python3 check-rules.py --self-check       # 只檢查指南自身一致性（rules.yaml ↔ guides/）

輸出：
    --format text（預設）人類可讀
    --format json        給 CI 或其他工具消費
    --format github      GitHub Actions 的 annotation 格式

離開碼：
    0  無 MUST/MUST_NOT 違規
    1  有必須修正的違規
    2  執行錯誤（設定檔缺失等）

行內豁免：
    val d = Dispatchers.IO  // guide-ignore: hardcoded-dispatcher
豁免必須在 code review 說明理由。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDE_ROOT = HERE.parent
RULES_YAML = GUIDE_ROOT / "rules.yaml"
GUIDES_DIR = GUIDE_ROOT / "guides"

BLOCKING_LEVELS = {"MUST", "MUST_NOT"}
IGNORE_RE = re.compile(r"//\s*guide-ignore:\s*([a-z0-9-]+(?:\s*,\s*[a-z0-9-]+)*)")


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        sys.stderr.write(
            "需要 PyYAML 才能讀取規則定義：\n    pip3 install pyyaml\n"
        )
        sys.exit(2)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.stderr.write(f"找不到規則檔：{path}\n")
        sys.exit(2)
    except yaml.YAMLError as e:
        sys.stderr.write(f"規則檔語法錯誤：{e}\n")
        sys.exit(2)


@dataclass
class Rule:
    id: str
    level: str
    enforce: str
    owner: str
    check: str
    pattern: str | None = None
    message: str = ""
    applies_to: list[str] = field(default_factory=lambda: ["**/*.kt"])
    exclude: list[str] = field(default_factory=list)
    source: str = ""
    # 需要看整份檔案才能判定的規則，用具名的內建處理器
    file_check: str | None = None

    @property
    def blocking(self) -> bool:
        return self.level in BLOCKING_LEVELS


@dataclass
class Finding:
    rule: Rule
    file: str
    line: int
    snippet: str

    def to_dict(self):
        return {
            "rule": self.rule.id,
            "level": self.rule.level,
            "enforce": self.rule.enforce,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "message": self.rule.message,
            "guide": f"guides/{self.rule.owner}",
        }


# ---------------------------------------------------------------------------
# 檔案級檢查：單行 regex 判定不了的規則
# 在 rules.yaml 用 `check: file` + `file_check: <名稱>` 指定
# ---------------------------------------------------------------------------
def fc_compose_view_strategy(content: str, path: str):
    """ComposeView 建立後必須設定 ViewCompositionStrategy。"""
    for m in re.finditer(r"\bComposeView\s*\(", content):
        tail = content[m.end() : m.end() + 600]
        if "setViewCompositionStrategy" not in tail:
            yield content[: m.start()].count("\n") + 1
            return


def fc_mixed_json_annotations(content: str, path: str):
    """同一檔案混用 kotlinx.serialization 與 Gson 的欄位註解。"""
    if "@Serializable" in content and "@SerializedName" in content:
        m = re.search(r"@SerializedName", content)
        yield content[: m.start()].count("\n") + 1


def fc_test_without_assertion(content: str, path: str):
    """@Test 函式沒有任何斷言。"""
    assert_re = re.compile(
        r"\bassert\w*\s*\(|\bverify\s*[({]|\bshouldBe\w*\b|\bexpect\w*\s*\(|"
        r"\bawaitItem\s*\(|\bawaitComplete\s*\(|\bassertThat\s*\(|\bfail\s*\(|"
        r"\.assertIsDisplayed\s*\(|\.assertExists\s*\("
    )
    for m in re.finditer(r"@Test\b[\s\S]{0,4000}?(?=\n\s*@Test\b|\Z)", content):
        if not assert_re.search(m.group(0)):
            yield content[: m.start()].count("\n") + 1


FILE_CHECKS = {
    "compose_view_strategy": fc_compose_view_strategy,
    "mixed_json_annotations": fc_mixed_json_annotations,
    "test_without_assertion": fc_test_without_assertion,
}


# ---------------------------------------------------------------------------
def parse_rules() -> list[Rule]:
    raw = load_yaml(RULES_YAML)
    if not isinstance(raw, list):
        sys.stderr.write("rules.yaml 頂層必須是 list\n")
        sys.exit(2)
    rules = []
    for r in raw:
        if not isinstance(r, dict) or "id" not in r:
            continue
        rules.append(
            Rule(
                id=r["id"],
                level=r.get("level", "SHOULD"),
                enforce=r.get("enforce", "migrate"),
                owner=r.get("owner", ""),
                check=str(r.get("check", "manual")),
                pattern=r.get("pattern"),
                message=r.get("message", ""),
                applies_to=r.get("applies_to") or ["**/*.kt"],
                exclude=r.get("exclude") or [],
                source=r.get("source", ""),
                file_check=r.get("file_check"),
            )
        )
    return rules


def path_matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def git(*args) -> list[str]:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [l for l in out.splitlines() if l.strip()]


# 會被稽核的檔案類型。規則自己的 applies_to glob 才決定它套用到哪些檔案，
# 這裡只負責「哪些檔案值得掃」——含 .kts / .gradle 是因為模組化與建置類規則的目標就是建置腳本。
SOURCE_SUFFIXES = (".kt", ".kts", ".gradle")
SOURCE_NAMES = ("gradle.properties",)


def is_source(path: str) -> bool:
    return path.endswith(SOURCE_SUFFIXES) or Path(path).name in SOURCE_NAMES


def collect_files(args) -> list[str]:
    if args.files:
        return args.files
    if args.all:
        out = []
        for suffix in SOURCE_SUFFIXES:
            out += [
                str(p)
                for p in Path(".").rglob(f"*{suffix}")
                if "/build/" not in str(p) and not str(p).startswith("build/")
            ]
        for name in SOURCE_NAMES:
            out += [str(p) for p in Path(".").rglob(name) if "/build/" not in str(p)]
        return sorted(set(out))
    if args.staged:
        return [f for f in git("diff", "--cached", "--name-only", "--diff-filter=AMR") if is_source(f)]
    if args.diff:
        return [f for f in git("diff", args.diff, "--name-only", "--diff-filter=AMR") if is_source(f)]
    return [f for f in git("diff", "HEAD", "--name-only", "--diff-filter=AMR") if is_source(f)]


def scan_file(path: str, rules: list[Rule]) -> list[Finding]:
    p = Path(path)
    if not p.is_file():
        return []
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = content.splitlines()
    findings: list[Finding] = []

    for rule in rules:
        if not path_matches(path, rule.applies_to):
            continue
        if rule.exclude and path_matches(path, rule.exclude):
            continue

        hits: list[int] = []
        if rule.check == "file" and rule.file_check:
            fn = FILE_CHECKS.get(rule.file_check)
            if fn:
                hits = list(fn(content, path))
        elif rule.check == "regex" and rule.pattern:
            try:
                for m in re.finditer(rule.pattern, content, re.MULTILINE):
                    hits.append(content[: m.start()].count("\n") + 1)
            except re.error as e:
                sys.stderr.write(f"規則 {rule.id} 的 pattern 無效：{e}\n")
                continue
        else:
            continue  # manual / detekt 交給人或其他工具

        for line_no in hits:
            raw = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            stripped = raw.lstrip()
            # 註解行不計（除非規則本身就是要抓註解掉的程式碼）
            if rule.file_check != "commented_out" and (
                stripped.startswith("//") or stripped.startswith("*")
            ):
                continue
            m = IGNORE_RE.search(raw)
            if m and rule.id in [s.strip() for s in m.group(1).split(",")]:
                continue
            findings.append(Finding(rule, path, line_no, stripped[:130]))

    return findings


def self_check(rules: list[Rule]) -> list[str]:
    """檢查 rules.yaml 與 guides/ 是否一致。"""
    errors = []
    seen: dict[str, str] = {}
    for r in rules:
        if r.id in seen:
            errors.append(f"規則 id 重複：{r.id}")
        seen[r.id] = r.owner
        if not r.owner:
            errors.append(f"{r.id} 缺少 owner")
        elif not (GUIDES_DIR / r.owner).exists():
            errors.append(f"{r.id} 的 owner 指向不存在的檔案：guides/{r.owner}")
        if r.level not in {"MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY"}:
            errors.append(f"{r.id} 的 level 無效：{r.level}")
        if r.enforce not in {"new-only", "on-touch", "new-only+on-touch", "migrate", "exempt"}:
            errors.append(f"{r.id} 的 enforce 無效：{r.enforce}")
        if r.check == "regex" and not r.pattern:
            errors.append(f"{r.id} 宣告 check: regex 但沒有 pattern")
        if r.check == "file" and r.file_check not in FILE_CHECKS:
            errors.append(f"{r.id} 的 file_check 無對應實作：{r.file_check}")
        if r.check in ("regex", "file") and not r.message:
            errors.append(f"{r.id} 可自動檢查但缺少 message（違規時要告訴人怎麼修）")

    # guides/ 裡的規則段落必須在 rules.yaml 有登記
    heading_re = re.compile(r"^###\s+([a-z0-9][a-z0-9-]*)\s*(?:·|\|)")
    for md in sorted(GUIDES_DIR.glob("*.md")):
        for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            m = heading_re.match(line)
            if not m:
                continue
            rid = m.group(1)
            if rid not in seen:
                errors.append(f"{md.name}:{n} 定義了 `{rid}`，但 rules.yaml 沒有登記")
            elif seen[rid] != md.name:
                errors.append(
                    f"{md.name}:{n} 定義了 `{rid}`，但 rules.yaml 說 owner 是 {seen[rid]}"
                )
    return errors


def report_text(findings: list[Finding], scanned: int) -> None:
    if not findings:
        print(f"稽核通過：{scanned} 個檔案，無違規")
        return
    blocking = [f for f in findings if f.rule.blocking]
    advisory = [f for f in findings if not f.rule.blocking]

    def block(title, items):
        print(f"\n{title}（{len(items)} 處）")
        by_file: dict[str, list[Finding]] = {}
        for f in items:
            by_file.setdefault(f.file, []).append(f)
        for path, fs in by_file.items():
            print(f"\n  {path}")
            for f in sorted(fs, key=lambda x: x.line):
                print(f"    L{f.line}  [{f.rule.id}]  {f.snippet}")
                if f.rule.message:
                    print(f"          → {f.rule.message}")
                print(f"          參見 guides/{f.rule.owner}")

    if blocking:
        block("必須修正", blocking)
    if advisory:
        block("建議修正", advisory)
    print(
        f"\n掃描 {scanned} 個檔案：必須修正 {len(blocking)} 處、建議修正 {len(advisory)} 處"
    )
    if blocking:
        print("確認為誤報時，在該行加 `// guide-ignore: <rule-id>` 並於 code review 說明理由。")


def main() -> int:
    ap = argparse.ArgumentParser(description="Android 開發準則稽核器")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--all", action="store_true", help="稽核整個專案")
    src.add_argument("--staged", action="store_true", help="稽核 git staged 檔案")
    src.add_argument("--diff", metavar="REF", help="稽核與指定 ref 的差異")
    src.add_argument("--files", nargs="+", help="稽核指定檔案")
    ap.add_argument("--self-check", action="store_true", help="只檢查指南自身一致性")
    ap.add_argument("--format", choices=["text", "json", "github"], default="text")
    args = ap.parse_args()

    rules = parse_rules()

    if args.self_check:
        errors = self_check(rules)
        if errors:
            for e in errors:
                print(f"  ✗ {e}")
            print(f"\n指南不一致：{len(errors)} 個問題")
            return 1
        print(f"指南一致性檢查通過：{len(rules)} 條規則")
        return 0

    files = collect_files(args)
    if not files:
        print("沒有需要稽核的 .kt 檔案")
        return 0

    findings: list[Finding] = []
    for f in files:
        findings.extend(scan_file(f, rules))

    if args.format == "json":
        print(json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2))
    elif args.format == "github":
        for f in findings:
            lvl = "error" if f.rule.blocking else "warning"
            msg = f"[{f.rule.id}] {f.rule.message}"
            print(f"::{lvl} file={f.file},line={f.line}::{msg}")
    else:
        report_text(findings, len(files))

    return 1 if any(f.rule.blocking for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
