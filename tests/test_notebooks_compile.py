"""Every code cell in every notebook must be valid Python.

This exists because a notebook is the one artifact in this project with no feedback loop.
Editing `app/` breaks a test in seconds; editing a notebook breaks nothing until it is
uploaded to Colab, a GPU is allocated, dependencies install, and the run dies on a
`SyntaxError` -- by which point a session and an hour are gone.

The specific failure that prompted this: a patch applied through a shell heredoc turned
`\\n` escapes into real newlines, splitting three string literals across source lines. The
patch script *did* verify its work -- it checked that the JSON still parsed and that the
expected keywords were present -- and both checks passed on a notebook whose Python no
longer tokenized. Parsing the container tells you nothing about the code inside it.

`compile()` is the right depth here: it catches syntax and indentation errors without
importing torch, allocating a GPU, or needing any of the notebook's dependencies.
"""
import json
import unittest
from pathlib import Path

NOTEBOOKS = sorted((Path(__file__).resolve().parents[1] / 'notebooks').glob('*.ipynb'))


def _python_only(source: str) -> str:
    """Strip IPython magics, which are not Python and never compile.

    Blanked rather than dropped so reported line numbers still match the cell.
    """
    return '\n'.join(
        '' if line.strip().startswith(('%', '!')) else line
        for line in source.splitlines()
    )


class TestNotebooksCompile(unittest.TestCase):
    def test_at_least_one_notebook_is_checked(self):
        """A glob that silently matches nothing would make every test below vacuous."""
        self.assertTrue(NOTEBOOKS, 'no notebooks found -- has the directory moved?')

    def test_every_code_cell_compiles(self):
        for nb_path in NOTEBOOKS:
            doc = json.loads(nb_path.read_text(encoding='utf-8'))
            for index, cell in enumerate(doc.get('cells', [])):
                if cell.get('cell_type') != 'code':
                    continue
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                if not source.strip():
                    continue
                with self.subTest(notebook=nb_path.name, cell=index):
                    try:
                        compile(_python_only(source), f'{nb_path.name}[{index}]', 'exec')
                    except SyntaxError as exc:
                        self.fail(f'{nb_path.name} cell {index} does not compile:\n'
                                  f'  {type(exc).__name__}: {exc}\n'
                                  f'  line {exc.lineno}: {(exc.text or "").rstrip()}')

    def test_no_stray_backslash_n_in_notebook_source(self):
        """A literal two-character backslash-n outside a string is the mangling signature.

        Weaker than the compile check and kept anyway: a mangled escape can land somewhere
        that still parses, and then the damage is a wrong message rather than a crash.
        """
        for nb_path in NOTEBOOKS:
            doc = json.loads(nb_path.read_text(encoding='utf-8'))
            for index, cell in enumerate(doc.get('cells', [])):
                if cell.get('cell_type') != 'code':
                    continue
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                for lineno, line in enumerate(source.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    with self.subTest(notebook=nb_path.name, cell=index, line=lineno):
                        self.assertNotIn(
                            "\\\\n", line,
                            f'{nb_path.name} cell {index} line {lineno} has a doubled '
                            f'backslash-n, which is how heredoc mangling shows up',
                        )


class TestNotebook05Invariants(unittest.TestCase):
    """Constants a run depends on, which are easy to lose in an unrelated edit."""

    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'notebooks' / '05_lora_finetune.ipynb'
        doc = json.loads(path.read_text(encoding='utf-8'))
        cls.source = '\n'.join(
            ''.join(c['source']) if isinstance(c.get('source'), list) else c.get('source', '')
            for c in doc['cells'] if c.get('cell_type') == 'code'
        )

    def test_refuses_to_run_without_a_gpu(self):
        """A warning here scrolled past and the session died on RAM ten minutes later,
        which read as a memory bug and was a missing GPU (`DEC-063`)."""
        self.assertIn("if DEVICE != 'cuda':", self.source)
        self.assertIn('raise RuntimeError', self.source)

    def test_abstain_ratio_matches_vizwiz_natural_rate(self):
        """Run 1 used 0.45 and learned the prior rather than a decision rule
        (`DEC-060`); 0.28 is the training split's own rate."""
        self.assertIn('ABSTAIN_RATIO = 0.28', self.source)

    def test_adapter_is_checkpointed_during_training(self):
        """Training is ~100 minutes; a disconnect at step 1400 must not cost all of it."""
        self.assertEqual(self.source.count('model.save_pretrained(OUT_DIR)'), 2)

    def test_evaluation_set_is_streamed(self):
        """list() over 500 full-resolution images held several GB for the whole eval."""
        self.assertNotIn('len(val)', self.source)


if __name__ == '__main__':
    unittest.main()
