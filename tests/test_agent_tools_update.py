"""Offline ownership and failure checks for the explicit updater."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "dot_local/bin/executable_agent-tools-update"
LOADER = importlib.machinery.SourceFileLoader("agent_tools_update", str(SOURCE))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
updater = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(updater)


def result(ok=True, stdout="", reason=None):
    return {"ok": ok, "stdout": stdout, "code": 0 if ok else 1,
            "reason": reason if reason else None if ok else "command_failed"}


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.directory).resolve()
        self.paths = {}
        self.calls = []
        self.packages = {}
        self.npm_root = self.root / "lib/node_modules"

    def binary(self, name, destination=None):
        target = Path(destination) if destination else self.root / "bin" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        self.paths[name] = str(target)
        return target

    def npm_package(self, package):
        self.binary("npm")
        self.packages[package] = {"version": "999.0.0"}
        self.binary(updater.NPM_TOOLS[package], self.npm_root / package / "bin/cli.js")

    def runner(self, argv, timeout):
        self.calls.append((argv, timeout))
        if argv[1:] == ["list", "--global", "--depth=0", "--json"]:
            return result(stdout=json.dumps({"dependencies": self.packages}))
        if argv[1:] == ["root", "--global"]:
            return result(stdout=str(self.npm_root))
        if argv[-1] == "--help":
            return result(stdout="Commands:\n  update [flags]  Update installation\n")
        return result()

    def plan(self, runner=None):
        return updater.plan(which=self.paths.get, runner=runner or self.runner, home=self.root)

    def test_npm_batch_only_installed_supported_active_packages(self):
        for package in ("@earendil-works/pi-coding-agent", "gh-axi", "cavemem", "tasks-axi"):
            self.npm_package(package)
        self.packages.update({"npm": {}, "corepack": {}, "pyright": {}})
        report = self.plan()
        self.assertEqual(report["manual"], [])
        self.assertEqual(len(report["actions"]), 1)
        argv = report["actions"][0]["argv"]
        self.assertEqual(argv[:3], [self.paths["npm"], "install", "--global"])
        self.assertEqual(set(argv[3:]), {name + "@latest" for name in (
            "@earendil-works/pi-coding-agent", "gh-axi", "cavemem", "tasks-axi")})
        self.assertTrue(all(timeout <= 20 for _, timeout in self.calls))

    def test_npm_inventory_with_problem_entries_still_updates_owned_tools(self):
        self.npm_package("@openai/codex")
        inventory = json.dumps({"dependencies": self.packages, "problems": ["invalid: example@1.0.0"]})

        def runner(argv, timeout):
            if argv[1:] == ["list", "--global", "--depth=0", "--json"]:
                return result(False, stdout=inventory)
            return self.runner(argv, timeout)

        report = self.plan(runner=runner)
        self.assertEqual(report["manual"], [])
        self.assertEqual(report["actions"][0]["argv"][3:], ["@openai/codex@latest"])

    def test_unparseable_npm_inventory_is_manual_even_when_listing_exits_zero(self):
        self.npm_package("@openai/codex")
        report = self.plan(runner=lambda argv, timeout: result(stdout="not json") if argv[1:] == ["list", "--global", "--depth=0", "--json"] else self.runner(argv, timeout))
        self.assertEqual(report["actions"], [])
        self.assertEqual({row["reason"] for row in report["manual"]}, {"global_inventory_unavailable", "installation_owner_unknown"})

    def test_shadowed_npm_package_is_manual_not_updated(self):
        self.npm_package("@openai/codex")
        self.binary("codex", self.root / "unknown/codex")
        report = self.plan()
        self.assertEqual(report["actions"], [])
        self.assertIn("global_package_inactive_or_shadowed", {row["reason"] for row in report["manual"]})
        self.assertIn("installation_owner_unknown", {row["reason"] for row in report["manual"]})

    def test_homebrew_preserves_cask_and_formula_ownership(self):
        prefix = self.root / "homebrew"
        brew = prefix / "bin/brew"
        brew.parent.mkdir(parents=True)
        brew.touch()
        self.binary("codex", prefix / "Caskroom/codex/999.0/codex")
        self.binary("claude", prefix / "Caskroom/claude-code/999.0/claude")
        self.binary("opencode", prefix / "Cellar/opencode/999.0/bin/opencode")
        report = self.plan()
        self.assertEqual(report["manual"], [])
        commands = [row["argv"] for row in report["actions"]]
        self.assertEqual(commands, [[str(brew), "update"],
                                   [str(brew), "upgrade", "--cask", "claude-code", "codex"],
                                   [str(brew), "upgrade", "--formula", "opencode"]])
        self.assertTrue(all(row["requires"] == report["actions"][0]["id"]
                            for row in report["actions"][1:]))

    def test_brew_owned_native_tool_uses_brew(self):
        prefix = self.root / "homebrew"
        brew = prefix / "bin/brew"
        brew.parent.mkdir(parents=True)
        brew.touch()
        self.binary("treehouse", prefix / "Cellar/treehouse/999/bin/treehouse")
        report = self.plan()
        self.assertEqual(report["actions"][-1]["argv"], [str(brew), "upgrade", "--formula", "treehouse"])
        self.assertFalse(any("--help" in argv for argv, _ in self.calls))

    def test_native_updates_use_advertised_command_without_force(self):
        for name in updater.NATIVE_TOOLS:
            self.binary(name)
        report = self.plan()
        self.assertEqual(report["manual"], [])
        self.assertEqual({tuple(row["argv"]) for row in report["actions"]},
                         {(self.paths[name], "update") for name in updater.NATIVE_TOOLS})
        self.assertFalse(any("--version" in argv for argv, _ in self.calls))

    def test_unknown_native_capability_is_manual(self):
        self.binary("kiro-cli")
        report = self.plan(runner=lambda argv, timeout: result(stdout="No update command"))
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["manual"][0]["reason"], "native_update_not_advertised")

    def test_native_full_help_is_followed_when_advertised(self):
        executable = self.binary("kiro-cli")

        def runner(argv, timeout):
            self.calls.append((argv, timeout))
            return result(stdout="Use --help-all for all commands" if argv[-1] == "--help"
                          else "Commands:\n  update  Update Kiro\n")

        report = self.plan(runner=runner)
        self.assertEqual(report["manual"], [])
        self.assertEqual(report["actions"][0]["argv"], [str(executable), "update"])
        self.assertEqual([argv[-1] for argv, _ in self.calls], ["--help", "--help-all"])

    def test_inventory_failure_is_visible_and_does_not_assume_npm_native(self):
        self.binary("npm")
        self.binary("treehouse", self.npm_root / "treehouse/bin/cli.js")
        report = self.plan(runner=lambda argv, timeout: result(False))
        self.assertEqual(report["actions"], [])
        self.assertEqual({row["reason"] for row in report["manual"]},
                         {"global_inventory_unavailable", "npm_owner_unverified"})

    def test_brew_update_failure_skips_dependent_upgrades(self):
        report = {"actions": [{"id": "metadata", "argv": ["brew", "update"]},
                              {"id": "upgrade", "argv": ["brew", "upgrade", "--cask", "codex"],
                               "requires": "metadata"}], "manual": []}
        calls = []

        def fail(argv, timeout):
            calls.append(argv)
            return result(False, stdout="SECRET MUST NOT LEAK")

        applied = updater.apply(report, runner=fail)
        self.assertEqual(calls, [["brew", "update"]])
        self.assertEqual(applied["results"][1]["reason"], "dependency_failed")
        self.assertFalse(applied["commands_exited_successfully"])
        self.assertNotIn("SECRET", json.dumps(applied))

    def test_native_active_run_refusal_is_preserved(self):
        report = {"actions": [{"id": "native-no-mistakes", "argv": ["no-mistakes", "update"]}], "manual": []}
        applied = updater.apply(report, runner=lambda argv, timeout: result(False))
        self.assertFalse(applied["commands_exited_successfully"])
        self.assertEqual(applied["results"][0]["reason"], "command_failed")

    def test_commands_exit_status_is_the_only_success_signal(self):
        report = {"actions": [{"id": "npm", "argv": ["npm", "install", "--global", "gh-axi@latest"]}], "manual": []}
        applied = updater.apply(report, runner=self.runner)
        self.assertTrue(applied["commands_exited_successfully"])
        report["manual"] = [{"tool": "claude", "reason": "installation_owner_unknown"}]
        self.assertTrue(updater.apply(report, runner=self.runner)["commands_exited_successfully"])

    def test_default_cli_is_plan_and_incomplete_apply_exits_nonzero(self):
        report = {"mode": "plan", "actions": [], "manual": [], "commands_exited_successfully": False}
        with patch.object(updater, "plan", return_value=report), patch.object(updater, "apply") as apply:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(updater.main(["--json"]), 0)
            apply.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())["mode"], "plan")
        report["manual"] = [{"tool": "codex", "reason": "installation_owner_unknown"}]
        with patch.object(updater, "plan", return_value=report), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.main(["--apply", "--json"]), 1)

    def test_timeout_and_unavailable_are_sanitized(self):
        import subprocess
        for exception, reason in ((subprocess.TimeoutExpired("private", 1, output="SECRET"), "timeout"),
                                  (OSError("SECRET"), "unavailable")):
            with self.subTest(reason=reason), patch.object(updater.subprocess, "run", side_effect=exception):
                observed = updater.run(["fake"], 1)
                self.assertFalse(observed["ok"])
                self.assertEqual(observed["reason"], reason)
                self.assertNotIn("SECRET", json.dumps(observed))

    def test_live_runner_inherits_stdin_and_sends_both_streams_to_stderr(self):
        with patch.object(updater.subprocess, "Popen") as popen:
            popen.return_value.wait.return_value = 0
            self.assertTrue(updater.run_live(["fake", "update"], 17)["ok"])
        self.assertIsNone(popen.call_args.kwargs["stdin"])
        self.assertIs(popen.call_args.kwargs["stdout"], sys.stderr)
        self.assertIs(popen.call_args.kwargs["stderr"], sys.stderr)
        self.assertEqual(popen.call_args.kwargs["start_new_session"], os.name == "posix")
        popen.return_value.wait.assert_called_once_with(timeout=17)

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup")
    def test_live_timeout_kills_process_group_and_bounds_cleanup(self):
        for cleanup_times_out in (False, True):
            with self.subTest(cleanup_times_out=cleanup_times_out), \
                    patch.object(updater.subprocess, "Popen") as popen, \
                    patch.object(updater.os, "killpg") as killpg:
                process = popen.return_value
                process.pid = 12345
                process.wait.side_effect = [subprocess.TimeoutExpired("fake", 1),
                                           subprocess.TimeoutExpired("fake", 2) if cleanup_times_out else 0]
                observed = updater.run_live(["fake"], 1)
                killpg.assert_called_once_with(12345, signal.SIGKILL)
                self.assertEqual(process.wait.call_args_list[-1].kwargs, {"timeout": 2})
                self.assertEqual(observed["reason"], "timeout_cleanup_unverified" if cleanup_times_out else "timeout")

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup")
    def test_keyboard_interrupt_cleans_up_group_and_stops_remaining_updates(self):
        with patch.object(updater.subprocess, "Popen") as popen, \
                patch.object(updater.os, "killpg") as killpg:
            process = popen.return_value
            process.pid = 12345
            process.wait.side_effect = [KeyboardInterrupt(), 0]
            with self.assertRaises(KeyboardInterrupt):
                updater.run_live(["fake", "update"], 10)
            killpg.assert_called_once_with(12345, signal.SIGKILL)
            self.assertEqual(process.wait.call_args_list[-1].kwargs, {"timeout": 2})
        report = {"mode": "plan", "actions": [], "manual": []}
        with patch.object(updater, "plan", return_value=report), \
                patch.object(updater, "apply", side_effect=KeyboardInterrupt()), \
                contextlib.redirect_stdout(io.StringIO()) as output, \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(updater.main(["--apply", "--json"]), 130)
        self.assertTrue(json.loads(output.getvalue())["interrupted"])
        self.assertFalse(json.loads(output.getvalue())["commands_exited_successfully"])
        self.assertIn("remaining updates were not started", errors.getvalue())

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup")
    def test_timeout_stops_grandchild_from_mutating_after_return(self):
        marker = self.root / "late-mutation"
        grandchild = "import time; from pathlib import Path; time.sleep(1); Path(" + repr(str(marker)) + ").touch()"
        parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', " + repr(grandchild) + "]); time.sleep(10)"
        observed = updater.run_live([sys.executable, "-c", parent], 0.3)
        self.assertEqual(observed["reason"], "timeout")
        time.sleep(1.1)
        self.assertFalse(marker.exists())

    def test_live_cancel_prompt_preserves_json_stdout_and_is_not_latest_proof(self):
        child = "import sys; print('Confirm update?', flush=True); answer = input(); print('Update cancelled: ' + answer, file=sys.stderr)"
        program = (
            "import importlib.machinery, importlib.util; loader = importlib.machinery.SourceFileLoader('u', " + repr(str(SOURCE)) + "); "
            "spec = importlib.util.spec_from_loader('u', loader); u = importlib.util.module_from_spec(spec); loader.exec_module(u); "
            "u.plan = lambda: {'mode':'plan', 'manual':[], 'actions':[{'id':'fake', 'argv':" +
            repr([sys.executable, "-c", child]) + "}]}; raise SystemExit(u.main(['--apply', '--json']))")
        completed = subprocess.run([sys.executable, "-c", program], input="cancel\n",
                                   capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertIn("Confirm update?", completed.stderr)
        self.assertIn("Update cancelled: cancel", completed.stderr)
        self.assertTrue(report["commands_exited_successfully"])

    def test_windows_scope_is_explicit_manual_action(self):
        with patch.object(updater.os, "name", "nt"):
            report = self.plan()
        self.assertEqual(report["actions"], [])
        self.assertIn("windows_shims_unverified", report["manual"][0]["reason"])

    def test_firstmate_clean_checkout_with_upstream_gets_ff_only_pull(self):
        (self.root / "firstmate/.git").mkdir(parents=True)
        git = self.binary("git")

        def runner(argv, timeout):
            self.calls.append((argv, timeout))
            return result(stdout="origin/main\n" if "rev-parse" in argv else "")

        report = self.plan(runner=runner)
        self.assertEqual(report["manual"], [])
        self.assertEqual(report["actions"][0]["argv"],
                         [str(git), "-C", str(self.root / "firstmate"), "pull", "--ff-only"])
        self.assertFalse(any("pull" in argv or "fetch" in argv for argv, _ in self.calls))

    def test_firstmate_dirty_or_missing_upstream_requires_manual_action(self):
        (self.root / "firstmate/.git").mkdir(parents=True)
        self.binary("git")
        for dirty, upstream_ok in ((True, True), (False, False)):
            def runner(argv, timeout):
                return result(ok=upstream_ok, stdout="origin/main") if "rev-parse" in argv else result(stdout=" M README.md" if dirty else "")
            report = self.plan(runner=runner)
            self.assertEqual(report["actions"], [])
            self.assertEqual(report["manual"][0]["reason"], "checkout_dirty_or_upstream_unavailable")


if __name__ == "__main__":
    unittest.main()
