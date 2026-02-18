#!/bin/bash
# Seed database if empty (first boot)
python -c "
import sqlite3, os
db_path = 'agentjobs.db'
if not os.path.exists(db_path):
    print('No DB found, will be created on startup')
else:
    conn = sqlite3.connect(db_path)
    count = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
    conn.close()
    if count == 0:
        print('DB empty, scraper will run on startup')
    else:
        print(f'DB has {count} jobs, ready to serve')
" 2>/dev/null || true

uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
