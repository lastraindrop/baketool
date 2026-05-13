"""Multi-version Blender test runner for cross-version compatibility."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_BLENDER_PATHS = [
    r"D:\Program Files\blender-3.3\blender.exe",
    r"D:\Program Files\Blender-3.6\blender.exe",
    r"D:\Program Files\blender-4.2\blender.exe",
    r"D:\Program Files\blender-4.5\blender.exe",
    r"D:\Program Files\blender-5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
]

SUCCESS_MARKERS = ("CONSOLIDATED SUITES PASSED", "ALL TESTS PASSED")
current_dir = Path(__file__).resolve().parent
runner_script = str(current_dir / "cli_runner.py")


def _split_paths(value):
    if not value:
        return []
    return [segment.strip() for segment in value.split(os.pathsep) if segment.strip()]


def _normalize_path(value):
    if not value:
        return None
    return os.path.normcase(str(Path(value).expanduser()))


def _dedupe_preserve_order(paths):
    deduped = []
    seen = set()
    for path in paths:
        normalized = _normalize_path(path)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(path)
    return deduped


def _load_paths_file(path):
    file_path = Path(path)
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    if file_path.suffix.lower() == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            data = data.get("paths", [])
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
        return []

    return [line.strip() for line in content.splitlines() if line.strip()]


def load_blender_paths(extra_paths=None, paths_file=None, env=None):
    """Collect candidate Blender executables from args, env, and defaults."""
    env = env or os.environ

    collected = []
    if extra_paths:
        collected.extend(extra_paths)

    collected.extend(_split_paths(env.get("BLENDER_PATHS", "")))

    env_paths_file = env.get("BLENDER_PATHS_FILE", "")
    if env_paths_file:
        collected.extend(_load_paths_file(env_paths_file))

    if paths_file:
        collected.extend(_load_paths_file(paths_file))

    if not extra_paths and not paths_file and not env_paths_file:
        collected.extend(DEFAULT_BLENDER_PATHS)
    return _dedupe_preserve_order(collected)


def get_blender_version(path):
    """Return the version string from a Blender executable."""
    try:
        res = subprocess.run(
            [path, "--version"], capture_output=True, text=True, check=True
        )
        return res.stdout.splitlines()[0]
    except Exception:
        return "Unknown Version"


def build_cli_command(
    blender_path,
    suite="all",
    category=None,
    verification=False,
    json_output=None,
):
    """Build the Blender CLI invocation for cli_runner.py."""
    cmd = [
        blender_path,
        "--background",
        "--factory-startup",
        "--python",
        runner_script,
        "--",
    ]

    if verification:
        cmd.extend(["--suite", "verification"])
    else:
        if suite != "all":
            cmd.extend(["--suite", suite])
        if category and category != "all":
            cmd.extend(["--category", category])

    if json_output:
        cmd.extend(["--json", str(json_output)])

    return cmd


def summarize_cli_result(returncode, stdout, parsed_report):
    """Derive success and a failure reason from the runner output."""
    if parsed_report:
        summary = parsed_report.get("summary", {})
        total = int(summary.get("total", 0))
        failures = int(summary.get("failures", 0))
        errors = int(summary.get("errors", 0))
        success = returncode == 0 and total > 0 and failures == 0 and errors == 0
        if success:
            return True, "ok"
        if total == 0:
            return False, "runner_error"
        return False, "test_fail"

    if returncode == 0 and any(marker in stdout for marker in SUCCESS_MARKERS):
        return True, "ok"

    return False, "runner_error"


def run_tests_on_blender(
    blender_path,
    suite="all",
    category=None,
    verification=False,
    timeout=300,
):
    """Run tests on a specific Blender version."""
    with tempfile.NamedTemporaryFile(
        prefix="baketool_cli_", suffix=".json", delete=False
    ) as temp_report:
        report_path = Path(temp_report.name)

    cmd = build_cli_command(
        blender_path,
        suite=suite,
        category=category,
        verification=verification,
        json_output=report_path,
    )
    test_env = os.environ.copy()
    test_env["PYTHONIOENCODING"] = "utf-8"

    try:
        process = subprocess.run(
            cmd, capture_output=True, env=test_env, check=False, timeout=timeout
        )
        stdout = process.stdout.decode("utf-8", errors="replace")
        stderr = process.stderr.decode("utf-8", errors="replace")

        parsed_report = None
        stdout_tail = []
        if report_path.exists() and report_path.stat().st_size > 0:
            try:
                parsed_report = json.loads(report_path.read_text(encoding="utf-8"))
                stdout_tail = []
            except (OSError, json.JSONDecodeError):
                parsed_report = None
                stdout_tail = stdout.splitlines()[-10:] if stdout else []

        success, failure_reason = summarize_cli_result(
            process.returncode, stdout, parsed_report
        )
        return {
            "success": success,
            "stdout": stdout,
            "stdout_tail": stdout_tail,
            "stderr": stderr,
            "returncode": process.returncode,
            "failure_reason": failure_reason,
            "report": parsed_report,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stdout_tail": [],
            "stderr": f"Timeout after {timeout} seconds",
            "returncode": -1,
            "failure_reason": "timeout",
            "report": None,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stdout_tail": [],
            "stderr": str(e),
            "returncode": -1,
            "failure_reason": "launcher_error",
            "report": None,
        }
    finally:
        try:
            report_path.unlink(missing_ok=True)
        except OSError:
            pass


def write_summary_reports(
    results,
    report_dir,
    mode_label,
    suite,
    category,
    json_output_path=None,
):
    """Write test results to text and JSON summary reports in the report directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    report_dir.mkdir(parents=True, exist_ok=True)

    if json_output_path:
        json_path = Path(json_output_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        report_path = json_path.with_suffix(".txt")
    else:
        report_path = report_dir / f"cross_version_report_{timestamp}.txt"
        json_path = report_dir / f"cross_version_report_{timestamp}.json"

    total_pass = sum(1 for item in results if item["success"])
    total_fail = len(results) - total_pass

    payload = {
        "timestamp": datetime.now().isoformat(),
        "test_mode": mode_label,
        "suite": suite,
        "category": category,
        "summary": {"pass": total_pass, "fail": total_fail},
        "results": results,
    }

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("BAKENEXUS v1.0.0 CROSS-VERSION TEST REPORT\n")
        handle.write("=" * 60 + "\n")
        handle.write(f"Generated: {payload['timestamp']}\n")
        handle.write(f"Test Mode: {mode_label}\n")
        handle.write("=" * 60 + "\n\n")
        handle.write("RESULTS:\n")
        for item in results:
            handle.write(f"\n[{item['status']}] {item['version']}\n")
            handle.write(f"  Path: {item['path']}\n")
            handle.write(f"  Reason: {item['failure_reason']}\n")

            # Include error details for failed runs
            if not item.get('success', False):
                report_summary = item.get('report_summary', {})
                if report_summary:
                    failures = report_summary.get('failures', 0)
                    errors = report_summary.get('errors', 0)
                    handle.write(f"  Summary: Failures={failures}, Errors={errors}\n")

                # Include full failure details from parsed report
                parsed = item.get('report') or {}
                details = parsed.get('details', {})
                if details:
                    failure_list = details.get('failures', [])
                    error_list = details.get('errors', [])
                    if failure_list:
                        handle.write(f"  Failures:\n")
                        for f in failure_list[:10]:
                            handle.write(f"    {f[:200]}\n")
                    if error_list:
                        handle.write(f"  Errors:\n")
                        for e in error_list[:10]:
                            handle.write(f"    {e[:200]}\n")

                # Include stderr if available
                stderr_text = item.get('stderr', '')
                if stderr_text:
                    handle.write(f"  Stderr Tail: {stderr_text[-1000:]}\n")

                # Include last few lines of stdout for context
                stdout_tail = item.get('stdout_tail', [])
                if stdout_tail:
                    handle.write(f"  Last Output:\n")
                    for line in stdout_tail[-3:]:
                        handle.write(f"    {line}\n")
        handle.write("\n" + "=" * 60 + "\n")
        handle.write(f"SUMMARY: {total_pass} PASS | {total_fail} FAIL\n")

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    return report_path, json_path


def main():
    """Entry point: discover Blender versions, run tests, collect and report results."""
    parser = argparse.ArgumentParser(description="BakeNexus Multi-Version Test Runner")
    parser.add_argument(
        "--suite",
        type=str,
        default="all",
        help="Test suite to run (all, memory, export, etc.)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Test category to run (core, memory, export, etc.)",
    )
    parser.add_argument(
        "--verification",
        action="store_true",
        help="Run comprehensive verification suite",
    )
    parser.add_argument(
        "--json", type=str, default=None, help="Save final summary as JSON"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available Blender versions"
    )
    parser.add_argument(
        "--blender",
        action="append",
        default=[],
        help="Explicit Blender executable path; may be passed multiple times",
    )
    parser.add_argument(
        "--paths-file",
        type=str,
        default=None,
        help="Optional text/JSON file containing Blender executable paths",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-version timeout in seconds",
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="Directory for generated summary reports",
    )

    args, _unknown = parser.parse_known_args()

    report_dir = (
        Path(args.report_dir).resolve()
        if args.report_dir
        else current_dir.parent / "reports"
    )
    blender_paths = load_blender_paths(
        extra_paths=args.blender, paths_file=args.paths_file, env=os.environ
    )
    valid_paths = [path for path in blender_paths if Path(path).exists()]
    missing_paths = [path for path in blender_paths if not Path(path).exists()]

    print("\n" + "=" * 80)
    print("      BAKENEXUS v1.0.0 CROSS-VERSION TEST SUITE")
    print("=" * 80)
    print(f"  Test Mode: {'Verification' if args.verification else 'Unit Tests'}")
    if args.suite != "all":
        print(f"  Suite: {args.suite}")
    if args.category:
        print(f"  Category: {args.category}")
    print("=" * 80)

    if args.list:
        print("\n>>> Searching for Blender installations...")
        if valid_paths:
            print("\n  Found Blender versions:")
            for path in valid_paths:
                print(f"    - {get_blender_version(path)}: {path}")
        else:
            print("\n  No Blender installations found in configured paths.")
        if missing_paths:
            print("\n  Missing paths:")
            for path in missing_paths:
                print(f"    - {path}")
        return True

    if not valid_paths:
        print("\n[ERROR] No valid Blender executables found.")
        print(
            "Set BLENDER_PATHS, BLENDER_PATHS_FILE, pass --blender, or use --paths-file."
        )
        if missing_paths:
            print("Configured but missing paths:")
            for path in missing_paths:
                print(f"  - {path}")
        return False

    print(f"\n>>> Testing {len(valid_paths)} Blender versions...\n")
    print(f"{'Blender Version':<40} | {'Status':<10} | {'Reason':<14}")
    print("-" * 80)

    results = []
    for path in valid_paths:
        full_ver = get_blender_version(path)
        ver_short = full_ver[:35] if len(full_ver) > 35 else full_ver

        result = run_tests_on_blender(
            path,
            suite=args.suite,
            category=args.category,
            verification=args.verification,
            timeout=args.timeout,
        )

        if result["success"]:
            status = "PASS"
            status_color = "\033[92m"
        else:
            status = "FAIL"
            status_color = "\033[91m"

        reason = result["failure_reason"]
        print(f"{ver_short:<40} | {status_color}{status:<10}\033[0m | {reason:<14}")

        if not result["success"]:
            if result["stderr"]:
                print(f"    | Stderr Snippet: {result['stderr'][:200]}...")
            elif result["stdout"]:
                tail = result["stdout"].splitlines()[-5:]
                print(f"    | Last Output: {tail}")

        report_summary = (result.get("report") or {}).get("summary", {})
        results.append(
            {
                "version": full_ver,
                "path": path,
                "status": status,
                "success": result["success"],
                "failure_reason": reason,
                "returncode": result["returncode"],
                "stderr": result["stderr"],
                "stdout_tail": result["stdout_tail"],
                "report_summary": report_summary,
                "report": result.get("report", {}),
                "timestamp": datetime.now().isoformat(),
            }
        )

    print("-" * 80)
    total_pass = sum(1 for item in results if item["success"])
    total_fail = len(results) - total_pass
    print(f"\n  SUMMARY: {total_pass} PASS | {total_fail} FAIL")

    report_path, json_path = write_summary_reports(
        results=results,
        report_dir=report_dir,
        mode_label="verification" if args.verification else "unit_tests",
        suite=args.suite,
        category=args.category,
        json_output_path=args.json,
    )

    print(f"\n>>> Reports saved:")
    print(f"    Text: {report_path.resolve()}")
    print(f"    JSON: {json_path.resolve()}")
    print("=" * 80 + "\n")

    return total_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
