"""`python -m mod_personnel_db.cli`のエントリポイント。"""

import sys

from mod_personnel_db.cli.app import main

if __name__ == "__main__":
    sys.exit(main())
