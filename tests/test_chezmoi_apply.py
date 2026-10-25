"""Exercise actual deployment in an isolated destination without install scripts."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SURFACES = [
    "AGENTS.md", ".claude/CLAUDE.md", ".codex/AGENTS.md",
    ".cursor/rules/general-guidelines.mdc", ".kiro/steering/general-guidelines.md",
    ".gemini/GEMINI.md", ".copilot/copilot-instructions.md", ".pi/agent/AGENTS.md",
]
TARGETS = SURFACES + [
    ".agents/DELEGATION-HINT.md", ".agents/DELEGATION.md", ".agents/DELEGATION-CLI.md",
    ".agents/skills/delegate/SKILL.md", ".cursor/rules/agentic-workflow.mdc",
    ".config/opencode/opencode.jsonc", ".local/bin/agent-capacity",
    ".local/bin/agent-tools-update", ".local/lib/agent_capacity",
]


class ChezmoiApplyTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("chezmoi"), "chezmoi is required")
    def test_targeted_apply_is_idempotent_and_preserves_local_codex_guidance(self):
        with tempfile.TemporaryDirectory(prefix="agentic-apply-") as directory:
            base = Path(directory)
            target = base / "home"
            (target / ".codex").mkdir(parents=True)
            local = "Machine-local instruction to preserve.\n"
            (target / ".codex/AGENTS.md").write_text(local)
            command = [
                "chezmoi", "--source", str(ROOT), "--destination", str(target),
                "--persistent-state", str(base / "state"), "--cache", str(base / "cache"),
                "--refresh-externals=never", "apply", "--exclude=scripts", "--parent-dirs",
            ] + [str(target / name) for name in TARGETS]
            first = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = {str(p.relative_to(target)): p.read_bytes()
                      for p in target.rglob("*") if p.is_file()}
            second = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(second.returncode, 0, second.stderr)
            after = {str(p.relative_to(target)): p.read_bytes()
                     for p in target.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            hint = (target / ".agents/DELEGATION-HINT.md").read_text().strip()
            for name in SURFACES:
                with self.subTest(surface=name):
                    rendered = (target / name).read_text()
                    self.assertEqual(rendered.count(hint), 1)
                    self.assertEqual(rendered.count("<!-- shared-delegation:start -->"), 1)
            self.assertIn(local, (target / ".codex/AGENTS.md").read_text())
            self.assertTrue((target / ".local/bin/agent-tools-update").stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
