"""Declared optional drawing imports do not relax the core dependency boundary."""
import ast
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('repository_integrity',ROOT/'scripts/check_repository_integrity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ImportBoundaries(unittest.TestCase):
    def check(self,source,path='scripts/plot_retained.py',requirements=None):
        tree=ast.parse(source);node=next(n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)))
        return module.declared_plot_import(node,tree,path,'matplotlib',{'matplotlib==3.10.8'} if requirements is None else requirements)

    def test_declared_entry_function_allowed(self):
        self.assertTrue(self.check('def main():\n    import matplotlib\n'))

    def test_eager_and_core_imports_rejected(self):
        self.assertFalse(self.check('import matplotlib\n'))
        self.assertFalse(self.check('def main():\n    import matplotlib\n',path='src/solver.py'))
        self.assertFalse(self.check('def run_campaign():\n    import matplotlib\n'))

    def test_missing_changed_or_extra_requirement_rejected(self):
        for requirements in (set(),{'matplotlib==3.10.7'},{'matplotlib==3.10.8','unknown-package'}):
            with self.subTest(requirements=requirements):
                self.assertFalse(self.check('def main():\n    import matplotlib\n',requirements=requirements))


if __name__=='__main__':unittest.main()
