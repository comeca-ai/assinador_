import contextlib
import os
import sqlite3
from pathlib import Path

class Database:
    def __init__(self, path):
        self.path=Path(path)
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with self.tx() as db:
            db.executescript(Path(__file__).with_name('schema.sql').read_text())
        os.chmod(self.path,0o600)

    @contextlib.contextmanager
    def tx(self):
        db=sqlite3.connect(self.path,timeout=20,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=20000')
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
