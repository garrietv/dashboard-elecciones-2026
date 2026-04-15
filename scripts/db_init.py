#!/usr/bin/env python3
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DB = DATA / 'onpe_history.db'

SCHEMA = '''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS captures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  captured_at TEXT NOT NULL,
  source_last_update TEXT,
  national_pct REAL,
  total_actas INTEGER,
  actas_contabilizadas INTEGER,
  tracking_last_update TEXT,
  tracking_pct REAL,
  live_last_update TEXT,
  live_pct REAL,
  tracking_count INTEGER,
  raw_tracking_json TEXT NOT NULL,
  raw_onpe_live_json TEXT NOT NULL,
  model_input_json TEXT,
  predictions_json TEXT,
  unique_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS tracking_cuts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  capture_id INTEGER NOT NULL,
  ts TEXT,
  pct REAL,
  fujimori REAL,
  rla REAL,
  nieto REAL,
  belmont REAL,
  sanchez REAL,
  jee INTEGER,
  contabilizadas INTEGER,
  FOREIGN KEY(capture_id) REFERENCES captures(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS regional_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  capture_id INTEGER NOT NULL,
  region_name TEXT,
  pct_actas REAL,
  vv REAL,
  fujimori_pct REAL,
  fujimori_votes INTEGER,
  rla_pct REAL,
  rla_votes INTEGER,
  nieto_pct REAL,
  nieto_votes INTEGER,
  belmont_pct REAL,
  belmont_votes INTEGER,
  sanchez_pct REAL,
  sanchez_votes INTEGER,
  FOREIGN KEY(capture_id) REFERENCES captures(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS prediction_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  capture_id INTEGER NOT NULL,
  generated_at TEXT,
  national_pct REAL,
  live_pct REAL,
  tracking_pct REAL,
  rla_prob INTEGER,
  nieto_prob INTEGER,
  sanchez_prob INTEGER,
  belmont_prob INTEGER,
  source TEXT,
  probabilities_json TEXT NOT NULL,
  projection_table_json TEXT,
  FOREIGN KEY(capture_id) REFERENCES captures(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_captures_source_last_update ON captures(source_last_update);
CREATE INDEX IF NOT EXISTS idx_tracking_cuts_capture_id ON tracking_cuts(capture_id);
CREATE INDEX IF NOT EXISTS idx_regional_results_capture_id ON regional_results(capture_id);
CREATE INDEX IF NOT EXISTS idx_prediction_runs_capture_id ON prediction_runs(capture_id);
'''


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        print(DB)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
