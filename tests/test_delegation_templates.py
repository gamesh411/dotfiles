import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HINT_PATH = ROOT / ".chezmoitemplates" / "delegation-hint.md"
SURFACES = [
    "AGENTS.md.tmpl",
    "dot_agents/DELEGATION-HINT.md.tmpl",
    "dot_claude/CLAUDE.md.tmpl",
    "dot_cursor/rules/general-guidelines.mdc.tmpl",
    "dot_kiro/steering/general-guidelines.md.tmpl",
    "dot_gemini/GEMINI.md.tmpl",
    "dot_copilot/copilot-instructions.md.tmpl",
    "dot_pi/agent/AGENTS.md.tmpl",
]


class DelegationTemplatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chezmoi = shutil.which("chezmoi")
        if cls.chezmoi is None:
            raise unittest.SkipTest("chezmoi is required to verify rendered instruction output")

    def render(self, source):
        with tempfile.TemporaryDirectory() as td:
            return subprocess.run([
                self.chezmoi, "--source", str(ROOT), "--persistent-state", str(Path(td) / "state"),
                "--cache", str(Path(td) / "cache"), "execute-template", "--file", str(ROOT / source),
            ], check=True, text=True, capture_output=True).stdout

    def test_native_instruction_surfaces_render_same_hint(self):
        hint = HINT_PATH.read_text().rstrip()
        for source in SURFACES:
            with self.subTest(source=source):
                rendered = self.render(source)
                self.assertEqual(rendered.count(hint), 1)
                self.assertEqual(rendered.count("<!-- shared-delegation:start -->"), 1)
                self.assertEqual(rendered.count("<!-- shared-delegation:end -->"), 1)
                self.assertIn("AGENT_DELEGATION_DEPTH=1", rendered)
                self.assertIn("DELEGATED_WORKER", rendered)
                self.assertLess(rendered.index(hint), len(rendered) // 2)
        cursor = self.render("dot_cursor/rules/general-guidelines.mdc.tmpl")
        frontmatter = cursor.split("---", 2)[1]
        self.assertIn("alwaysApply: true", frontmatter)
        self.assertIn("description:", frontmatter)
        kiro = self.render("dot_kiro/steering/general-guidelines.md.tmpl")
        self.assertIn("inclusion: always", kiro.split("---", 2)[1])

    def test_opencode_loads_the_standalone_shared_hint(self):
        config = json.loads(self.render("dot_config/opencode/opencode.jsonc.tmpl"))
        self.assertEqual(len(config["instructions"]), 1)
        self.assertEqual(Path(config["instructions"][0]).name, "DELEGATION-HINT.md")
        self.assertEqual(Path(config["instructions"][0]).parent.name, ".agents")
        self.assertEqual(self.render("dot_agents/DELEGATION-HINT.md.tmpl").strip(), HINT_PATH.read_text().strip())

    def test_codex_modifier_renders_idempotently_and_keeps_local_text(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "modify.py"
            script.write_text(self.render("dot_codex/modify_AGENTS.md.py.tmpl"))
            local = "# Machine local\nKeep this exact text.\n"
            first = subprocess.run(["python3", str(script)], input=local, text=True, check=True, capture_output=True).stdout
            second = subprocess.run(["python3", str(script)], input=first, text=True, check=True, capture_output=True).stdout
            self.assertEqual(first, second)
            self.assertTrue(first.startswith(HINT_PATH.read_text().rstrip() + "\n\n"))
            self.assertIn(local, first)
            self.assertEqual(first.count("<!-- shared-delegation:start -->"), 1)
            self.assertIn("AGENT_DELEGATION_DEPTH=1", first)

    def test_codex_modifier_rejects_malformed_markers(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "modify.py"
            script.write_text(self.render("dot_codex/modify_AGENTS.md.py.tmpl"))
            for value in ("<!-- shared-delegation:start -->\nonly start\n", "<!-- shared-delegation:start -->\na\n<!-- shared-delegation:start -->\nb\n<!-- shared-delegation:end -->\n"):
                result = subprocess.run(["python3", str(script)], input=value, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Expected exactly one managed delegation section", result.stderr)


if __name__ == "__main__":
    unittest.main()
