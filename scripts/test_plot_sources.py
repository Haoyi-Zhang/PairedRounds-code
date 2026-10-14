"""Retained width lineage and optional route checks; no scheduling runs."""
from pathlib import Path
import ast
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('plot_retained', ROOT / 'scripts/plot_retained.py')
ROUTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE)

class PlotSources(unittest.TestCase):
    def test_retained_widths_bind_validation(self):
        validation = json.loads((ROOT / 'results/validation.json').read_text())
        data = ROUTE.read_data(ROOT / 'results/figure-sources/widths.csv')
        self.assertEqual(data, list(enumerate(validation['sharp_widths'], 1)))
        self.assertEqual(data, [(k, k + 1) for k in range(1, 13)])

    def test_retained_export_copies_agree(self):
        self.assertEqual(ROUTE.read_data(ROOT / 'results/figure-sources/widths.csv'),
                         ROUTE.read_data(ROOT / 'results/reproduction-figure-sources/widths.csv'))

    def test_optional_route_is_plot_only(self):
        source = (ROOT / 'scripts/plot_retained.py').read_text()
        for option in ('--input', '--output-dir', '--tex-font-root', '--tex-font-map-dir', '--tex-bin-dir'):
            self.assertIn(option, source)
        self.assertNotIn('from solver', source)
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id == 'solve' for n in ast.walk(tree)))

if __name__ == '__main__':
    unittest.main()
