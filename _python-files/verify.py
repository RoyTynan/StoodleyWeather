"""
Project verifier — auto-detects the tech stack from repo contents and runs
appropriate checks. No per-project config required.

Supports:
  TypeScript       — tsc --noEmit
  React            — tsc --noEmit + ESLint (if configured)
  React Native     — tsc --noEmit + ESLint (if configured)
  C++ (CMake)      — cmake --build build/
  C++ (Make)       — make -j4
  C++ (raw)        — clang-tidy on .cpp files (if available)

Used by the verify_project MCP tool in server.py.
"""

import glob as glob_module
import json
import os
import subprocess
from dataclasses import dataclass, field


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    output: str


@dataclass
class VerifyResult:
    repo: str
    stacks: list[str]
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def summary(self) -> str:
        lines = [
            f"Repo:     {self.repo}",
            f"Detected: {', '.join(self.stacks) if self.stacks else 'unknown — no checks run'}",
        ]
        if not self.checks:
            lines.append("\nNo checks could be determined for this project.")
            return "\n".join(lines)
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"\n[{status}] {check.name}")
            if not check.passed and check.output.strip():
                out = check.output.strip()
                if len(out) > 3000:
                    out = out[:3000] + "\n... [truncated]"
                lines.append(out)
        overall = "All checks passed." if self.passed else "One or more checks failed — see above."
        lines.append(f"\n{overall}")
        return "\n".join(lines)


# ── Stack detection ──────────────────────────────────────────────────────────

_JS_SUBDIRS = ["frontend", "client", "web", "app", "ui"]


def find_js_root(repo_path: str) -> str:
    """Return the directory containing package.json — repo root or a known subdirectory."""
    if os.path.exists(os.path.join(repo_path, "package.json")):
        return repo_path
    for sub in _JS_SUBDIRS:
        candidate = os.path.join(repo_path, sub)
        if os.path.exists(os.path.join(candidate, "package.json")):
            return candidate
    return repo_path


def detect_stacks(repo_path: str) -> list[str]:
    """
    Inspect repo_path and return detected stack identifiers.
    More specific stacks are listed before general ones.
    """
    stacks: list[str] = []

    js_root = find_js_root(repo_path)
    pkg_path = os.path.join(js_root, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg = json.load(f)
            deps: dict = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            if "react-native" in deps:
                stacks.append("react-native")
            elif "react" in deps:
                stacks.append("react")

            has_ts = (
                "typescript" in deps
                or os.path.exists(os.path.join(js_root, "tsconfig.json"))
            )
            if has_ts and "typescript" not in stacks:
                stacks.append("typescript")
        except (json.JSONDecodeError, OSError):
            pass
    elif os.path.exists(os.path.join(js_root, "tsconfig.json")):
        stacks.append("typescript")

    # C++ — CMake takes priority over a bare Makefile
    if os.path.exists(os.path.join(repo_path, "CMakeLists.txt")):
        stacks.append("cpp-cmake")
    elif glob_module.glob(os.path.join(repo_path, "[Mm]akefile")):
        stacks.append("cpp-make")
    elif glob_module.glob(os.path.join(repo_path, "**/*.cpp"), recursive=True):
        stacks.append("cpp")

    return stacks


# ── Individual checks ────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str, timeout: int = 60) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except FileNotFoundError as e:
        return False, f"Command not found: {e}"
    except subprocess.TimeoutExpired:
        return False, f"Check timed out after {timeout}s"


def check_tsc(repo_path: str) -> CheckResult:
    passed, output = _run(
        ["npx", "--no-install", "tsc", "--noEmit"],
        cwd=repo_path,
        timeout=90,
    )
    return CheckResult(name="TypeScript — tsc --noEmit", passed=passed, output=output)


def check_eslint(repo_path: str) -> CheckResult | None:
    """Only runs if an ESLint config file is present in the repo root."""
    config_files = [
        ".eslintrc", ".eslintrc.js", ".eslintrc.cjs",
        ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml",
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    ]
    if not any(os.path.exists(os.path.join(repo_path, f)) for f in config_files):
        return None
    src_dir = "src" if os.path.isdir(os.path.join(repo_path, "src")) else "app" if os.path.isdir(os.path.join(repo_path, "app")) else "."
    passed, output = _run(
        ["npx", "--no-install", "eslint", src_dir,
         "--ext", ".ts,.tsx,.js,.jsx", "--max-warnings", "0"],
        cwd=repo_path,
        timeout=60,
    )
    return CheckResult(name="ESLint", passed=passed, output=output)


def check_cmake(repo_path: str) -> CheckResult:
    build_dir = os.path.join(repo_path, "build")
    if not os.path.isdir(build_dir):
        return CheckResult(
            name="C++ — cmake --build",
            passed=False,
            output=(
                f"Build directory not found: {build_dir}\n"
                "Run `cmake -B build` to configure the project first."
            ),
        )
    passed, output = _run(
        ["cmake", "--build", build_dir, "--parallel"],
        cwd=repo_path,
        timeout=180,
    )
    return CheckResult(name="C++ — cmake --build", passed=passed, output=output)


def check_make(repo_path: str) -> CheckResult:
    passed, output = _run(["make", "-j4"], cwd=repo_path, timeout=180)
    return CheckResult(name="C++ — make", passed=passed, output=output)


def check_clang_tidy(repo_path: str) -> CheckResult | None:
    """Runs clang-tidy on .cpp files when no build system is detected."""
    ok, _ = _run(["which", "clang-tidy"], cwd=repo_path, timeout=5)
    if not ok:
        return None
    cpp_files = glob_module.glob(os.path.join(repo_path, "**/*.cpp"), recursive=True)
    if not cpp_files:
        return None
    passed, output = _run(
        ["clang-tidy", "--quiet"] + cpp_files[:20],
        cwd=repo_path,
        timeout=120,
    )
    return CheckResult(name="C++ — clang-tidy", passed=passed, output=output)


# ── Main entry point ─────────────────────────────────────────────────────────

def verify(repo_path: str, repo_name: str) -> VerifyResult:
    """
    Detect the stack at repo_path and run all applicable checks.
    Returns a VerifyResult with pass/fail status and any error output.
    """
    stacks = detect_stacks(repo_path)
    js_root = find_js_root(repo_path)
    checks: list[CheckResult] = []

    needs_tsc = any(s in stacks for s in ("typescript", "react", "react-native"))

    if needs_tsc:
        checks.append(check_tsc(js_root))
        eslint = check_eslint(js_root)
        if eslint is not None:
            checks.append(eslint)

    if "cpp-cmake" in stacks:
        checks.append(check_cmake(repo_path))
    elif "cpp-make" in stacks:
        checks.append(check_make(repo_path))
    elif "cpp" in stacks:
        tidy = check_clang_tidy(repo_path)
        if tidy is not None:
            checks.append(tidy)

    return VerifyResult(repo=repo_name, stacks=stacks, checks=checks)
