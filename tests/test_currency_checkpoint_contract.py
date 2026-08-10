"""The notebook writes the checkpoint; the app reads it. Nothing enforces that they agree.

A mismatch is invisible until after a training run: the notebook reports good accuracy,
saves, and the app then raises `KeyError` — or worse, silently falls back to a default that
was right for a different dataset. Wrong normalisation constants or a wrong `img_size` do
not crash at all; they just make every prediction quietly worse, which for Money mode means
a confidently wrong denomination.

These tests read the export cell of `notebooks/03_currency_classifier.ipynb` and check it
against what `app/engines/currency_cnn.py` actually looks up. They need neither torch nor a
trained checkpoint, so they run in the normal suite.
"""
import ast
import json
import unittest
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / 'notebooks' / '03_currency_classifier.ipynb'
ENGINE = Path(__file__).resolve().parents[1] / 'app' / 'engines' / 'currency_cnn.py'

# Read without a default in `_load`, so their absence is a hard failure.
REQUIRED_BY_APP = {'classes', 'state_dict'}

# Read with a fallback in `_preprocess`. Present in the checkpoint means the app uses the
# values training actually used; absent means it silently assumes ImageNet defaults, which
# is only correct by luck.
EXPECTED_BY_APP = {'img_size', 'mean', 'std'}


def saved_keys() -> set[str]:
    """String keys of the dict literal passed to torch.save in the notebook."""
    nb = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        source = cell['source']
        source = source if isinstance(source, str) else ''.join(source)
        if 'torch.save' not in source:
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == 'save' and node.args:
                blob = node.args[0]
                if isinstance(blob, ast.Dict):
                    return {k.value for k in blob.keys if isinstance(k, ast.Constant)}
    raise AssertionError('no torch.save({...}) call found in notebook 03')


def engine_source() -> str:
    return ENGINE.read_text(encoding='utf-8')


class TestCheckpointContract(unittest.TestCase):
    def test_notebook_saves_every_key_the_app_requires(self):
        missing = REQUIRED_BY_APP - saved_keys()
        self.assertFalse(
            missing,
            f'notebook 03 does not save {sorted(missing)}, which app/engines/currency_cnn.py '
            f'reads without a default -- the app would raise KeyError on a model that took '
            f'an hour to train',
        )

    def test_notebook_saves_the_preprocessing_the_app_would_otherwise_assume(self):
        """These have fallbacks, so a mismatch degrades predictions instead of crashing."""
        missing = EXPECTED_BY_APP - saved_keys()
        self.assertFalse(
            missing,
            f'notebook 03 does not save {sorted(missing)}; the app would fall back to '
            f'ImageNet defaults and preprocess differently from training, which shows up as '
            f'a confidently wrong denomination rather than an error',
        )

    def test_class_names_travel_in_the_checkpoint_not_the_code(self):
        """DEC-023: a hardcoded class order would relabel every prediction if the dataset
        folders ever changed -- 'Rs 500 reported as Rs 10' as a one-line mistake."""
        self.assertIn('classes', saved_keys())
        source = engine_source()
        self.assertIn("blob['classes']", source)
        for literal in ("'10'", '"10"', "'500'", '"500"'):
            self.assertNotIn(
                f'[{literal}',
                source,
                'currency_cnn.py appears to hardcode a class list; it must come from the '
                'checkpoint',
            )

    def test_background_class_is_understood_by_money_mode(self):
        """The dataset has a `background` class (DEC-039). If the notebook trains on it but
        the mode does not recognise it, the app says 'This is a background rupee note.'"""
        from app.modes.currency import BACKGROUND_LABEL, run  # noqa: F401

        organizer = (Path(__file__).resolve().parents[1]
                     / 'data' / 'scripts' / 'organize_currency.py').read_text(encoding='utf-8')
        self.assertIn(
            f'BACKGROUND_CLASS = "{BACKGROUND_LABEL}"',
            organizer,
            'the folder name the organizer writes must match the label money mode checks, '
            'or the "no note in frame" answer silently becomes a denomination',
        )


if __name__ == '__main__':
    unittest.main()
