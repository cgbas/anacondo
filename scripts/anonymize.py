#!/usr/bin/env python3
"""
ANACONDO — Anonymizer for LGPD compliance
==========================================

Reads  : exports/csv/
Writes : exports/csv_public/

Privacy rules applied
---------------------
- `complemento` column (extratos.csv): redacts apartment numbers, personal names,
  company names, and utility meter IDs using regex + optional data dictionary.
- All other columns: passed through unchanged (no PII identified).

Data dictionary
---------------
Create exports/private/data_dictionary.json with a mapping of real entity names
to pseudonyms.  The file is gitignored and never committed.  If it does not exist,
only structural regex-based patterns are applied (apartment numbers and meter IDs).

Usage
-----
    python3 scripts/anonymize.py [--dry-run]

    --dry-run  Print diff stats without writing files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CSV_DIR = ROOT / "exports" / "csv"
PUBLIC_DIR = ROOT / "exports" / "csv_public"
DICT_PATH = ROOT / "exports" / "private" / "data_dictionary.json"

# ── Regex patterns (structural — no sensitive data encoded here) ───────────────
# "Apto 1008 BL B"  |  "Apto 0504"  |  "APTO 0201 BL A"  |  "AP.0303"
_RE_APTO = re.compile(
    r"""
    (?i)                    # case insensitive
    \b(?:Apto?|AP)          # Apto / Apt / AP
    \.?\s*                  # optional dot + whitespace
    (\d{4}[A-Z]?)           # 4-digit unit number (+ optional suffix A/B)
    (?:\s+BL\s+([AB]))?     # optional "BL A" or "BL B"
    \b
    """,
    re.VERBOSE,
)

# Electricity meter installation IDs: I.4954556
_RE_MEDIDOR_E = re.compile(r"\bI\.(\d{5,7})\b")

# Water meter / consumption references: R.690.457
_RE_MEDIDOR_A = re.compile(r"\bR\.(\d{3}\.\d{3})\b")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pseudonym_ap(unit: str, bloco: str | None) -> str:
    """
    Deterministic pseudonym for an apartment unit.
    Same AP always maps to the same 4-char token so aggregations remain consistent.
    """
    key = f"AP{unit}BL{bloco or 'X'}"
    token = hashlib.md5(key.encode()).hexdigest()[:4].upper()
    if bloco:
        return f"[AP:{token} BL {bloco}]"
    return f"[AP:{token}]"


def _build_entity_map(dict_path: Path) -> list[tuple[re.Pattern, str]]:
    """
    Load the private data dictionary and compile case-insensitive regex patterns.
    Returns an empty list if the file doesn't exist.
    """
    if not dict_path.exists():
        print(f"  [warn] data_dictionary.json not found at {dict_path}. "
              "Only structural patterns will be applied.")
        return []

    with dict_path.open(encoding="utf-8") as fh:
        raw: dict = json.load(fh)

    entities: dict[str, str] = raw.get("entities", {})
    # Sort longest-first to avoid partial replacements (e.g. "CDM MOTOBOMBAS" before "CDM")
    pairs = sorted(entities.items(), key=lambda kv: -len(kv[0]))
    return [
        (re.compile(re.escape(real), re.IGNORECASE), pseudo)
        for real, pseudo in pairs
    ]


def _anonymize_value(value: object, entity_patterns: list) -> str:
    """Apply all anonymization rules to a single cell value."""
    if not isinstance(value, str) or not value.strip():
        return value  # type: ignore[return-value]

    result = value

    # 1. Named entities (companies / persons) — dictionary-based
    for pattern, pseudo in entity_patterns:
        result = pattern.sub(pseudo, result)

    # 2. Apartment numbers — regex (deterministic pseudonym)
    result = _RE_APTO.sub(
        lambda m: _pseudonym_ap(m.group(1), m.group(2)),
        result,
    )

    # 3. Utility meter IDs
    result = _RE_MEDIDOR_E.sub("[MEDIDOR_E]", result)
    result = _RE_MEDIDOR_A.sub("[MEDIDOR_A]", result)

    return result


def _anonymize_df(df: pd.DataFrame, entity_patterns: list) -> tuple[pd.DataFrame, int]:
    """
    Anonymize PII columns in a dataframe.
    Returns (anonymized_df, number_of_cells_changed).
    """
    df_out = df.copy()
    changed = 0

    pii_cols = [c for c in df_out.columns if c.lower() in ("complemento",)]

    for col in pii_cols:
        original = df_out[col].astype(str)
        anonymized = df_out[col].apply(
            lambda v: _anonymize_value(v, entity_patterns)
        )
        mask = (original != anonymized) & df_out[col].notna()
        changed += int(mask.sum())
        df_out[col] = anonymized

    return df_out, changed


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    print("ANACONDO — Anonymizer LGPD")
    print(f"  Source : {CSV_DIR}")
    print(f"  Output : {PUBLIC_DIR}")
    print(f"  Dict   : {DICT_PATH} ({'found' if DICT_PATH.exists() else 'NOT FOUND — partial mode'})")
    print(f"  Mode   : {'DRY RUN' if dry_run else 'WRITE'}\n")

    entity_patterns = _build_entity_map(DICT_PATH)
    print(f"  Loaded {len(entity_patterns)} entity mappings from dictionary.\n")

    csv_files = sorted(CSV_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSVs found in {CSV_DIR}")
        sys.exit(1)

    total_changed = 0

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path, low_memory=False)
        except Exception as exc:
            print(f"  [skip] {csv_path.name}: {exc}")
            continue

        df_anon, changed = _anonymize_df(df, entity_patterns)
        total_changed += changed

        out_path = PUBLIC_DIR / csv_path.name
        status = f"{changed:4d} cells redacted" if changed else "  no changes"
        print(f"  {csv_path.name:<55} {status}")

        if not dry_run:
            df_anon.to_csv(out_path, index=False)

    print(f"\nTotal cells redacted : {total_changed}")
    if dry_run:
        print("DRY RUN — no files written.")
    else:
        print(f"Public CSVs written to: {PUBLIC_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LGPD anonymizer for ANACONDO CSVs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
