"""Every third-party module `app/` imports must be declared somewhere installable.

This gap has bitten three times, always the same way: `setup.ps1` completes, the suite
passes because it runs on fakes, and the failure appears the first time a real engine is
used -- which on this project means the demo laptop.

  * `torchvision` -- currency mode, missing entirely from requirements.txt
  * `accelerate`  -- scene/ask, installed by the Colab notebooks but never listed here
  * `paddleocr`   -- staged, and only discoverable from a comment

Declared means either a requirement line or a documented staged install, because the
staging is deliberate (`requirements.txt` explains why: each stage pulls models on first
use and a failure is easier to attribute when isolated). The test only insists it is
written down somewhere a person following the README would find it.

Import-scanning cannot catch a runtime-only dependency like `accelerate`, which nothing in
`app/` imports directly -- transformers demands it when `device_map` is set. That one is
covered by `setup.ps1`'s verification step instead.
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
REQUIREMENTS = ROOT / 'requirements.txt'

# Import name -> distribution name, where they differ.
DISTRIBUTION = {
    'PIL': 'pillow',
    'paddle': 'paddlepaddle',
    'cv2': 'opencv-python',
    'yaml': 'pyyaml',
}

STDLIB_OK = set(getattr(__import__('sys'), 'stdlib_module_names', ()))


def imported_modules() -> set[str]:
    """Top-level module names imported anywhere under app/, including inside functions."""
    found: set[str] = set()
    for path in APP.rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    found.add(node.module.split('.')[0])
    return {m for m in found if m not in STDLIB_OK and m != 'app'}


class TestRequirementsCoverImports(unittest.TestCase):
    def setUp(self):
        self.text = REQUIREMENTS.read_text(encoding='utf-8').lower()

    def test_every_import_is_declared(self):
        missing = []
        for module in sorted(imported_modules()):
            name = DISTRIBUTION.get(module, module).lower()
            # A bare word match: requirement lines and the staged-install comments both
            # name the distribution, and either counts as "written down".
            if not re.search(rf'(?m)^[^#\n]*\b{re.escape(name)}\b|#.*\b{re.escape(name)}\b',
                             self.text):
                missing.append(f'{module} (install as {name})')

        self.assertFalse(
            missing,
            'app/ imports these but requirements.txt never mentions them:\n  '
            + '\n  '.join(missing)
            + '\n\nsetup.ps1 will report success and the engine will fail on first real '
              'use.',
        )

    def test_transformers_stays_pinned_below_5(self):
        """IndicTransToolkit imports transformers.tokenization_utils, removed in v5, so an
        unpinned install silently breaks Marathi and Hindi speech (DEC-009)."""
        self.assertRegex(self.text, r'transformers\s*<\s*5')

    def test_torch_comes_from_the_cpu_index(self):
        """The laptop has no NVIDIA GPU; the default index would pull a CUDA build worth
        gigabytes that cannot be used."""
        self.assertIn('download.pytorch.org/whl/cpu', self.text)


if __name__ == '__main__':
    unittest.main()
