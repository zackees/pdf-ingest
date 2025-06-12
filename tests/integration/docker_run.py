"""
Unit test file.
"""

from pathlib import Path

import os
import unittest


# os.system('docker compose down --rmi=all')
# os.system('docker compose up --build --no-start')

# os.system('docker compose run --rm --service-ports --entrypoint /bin/bash app')


class EpubTester(unittest.TestCase):
    """Main tester class."""

    @classmethod
    def setUpClass(cls) -> None:
        here = Path(__file__).parent.resolve()
        project_root = here.parent.parent.resolve()
        os.chdir(project_root)

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        os.system("docker compose down --rmi=all")
        os.system("docker compose up --build")

        


if __name__ == "__main__":
    unittest.main()
