"""
Unit test file.
"""

from pathlib import Path

import unittest



HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.parent.resolve()

class Fb2Tester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), f"Expected {pyproject_path} to exist.")

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
        # ai - please implement this
        pass
        


if __name__ == "__main__":
    unittest.main()
