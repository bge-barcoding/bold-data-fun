"""
BOLD Curation Report Generator

Takes a folder of log files and a BOLD data package TSV, and generates
a curation report for each log file.

Usage:
    python bold_curation_report.py <log_folder> <bold_data_package.tsv> [--output_dir <dir>] [--initials XX]

Output:
    One report TSV per log file, named:
        <N>_bold_curation_report_<YYYYMMDD>_<HHMM>_<initials>.txt
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# The BOLD data package contains very large fields (e.g. nucleotide
# sequences in the 'nuc' column) that exceed Python's default CSV field
# size limit of 131072 bytes.  Raise it to handle any field size.
csv.field_size_limit(sys.maxsize)


# ---------------------------------------------------------------------------
# 1. Parse a single log file into per-process-ID consolidated changes
# ---------------------------------------------------------------------------

# Regex for the header line of each log entry
#   2025-07-23T20:20:03.045Z - Process ID: BBIOP3958-24, Action: Updated
_HEADER_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s*-\s*"
    r"Process ID:\s*(?P<pid>[A-Za-z0-9]+-\d+),\s*Action:\s*(?P<action>.+)$"
)

# Regex for a field-change line (indented)
#   species: Cis nitidus -> Cis castaneus
_FIELD_RE = re.compile(
    r"^\s+(?P<field>[A-Za-z_]+):\s*(?P<old>.*?)\s*->\s*(?P<new>.*)$"
)


def parse_log_file(log_path: str) -> dict:
    """
    Parse a log file and return a dict keyed by processid.

    For each processid the value is a dict:
        {
            "fields": { field_name: (old_value, new_value, timestamp), ... },
            "first_ts": <datetime>,   # earliest entry for ordering
        }

    When the same field appears more than once for a processid the entry with
    the *latest* timestamp wins (most-recent-value rule).
    """
    records: dict[str, dict] = {}

    with open(log_path, "r", encoding="utf-8") as fh:
        current_pid = None
        current_ts = None

        for raw_line in fh:
            line = raw_line.rstrip("\n\r")
            if not line:
                continue

            hdr = _HEADER_RE.match(line)
            if hdr:
                current_ts = hdr.group("timestamp")
                current_pid = hdr.group("pid")

                if current_pid not in records:
                    records[current_pid] = {
                        "fields": {},
                        "first_ts": current_ts,
                    }
                continue

            fld = _FIELD_RE.match(line)
            if fld and current_pid is not None:
                field_name = fld.group("field")
                old_val = fld.group("old").strip()
                new_val = fld.group("new").strip()

                existing = records[current_pid]["fields"].get(field_name)
                # Keep the change with the latest timestamp
                if existing is None or current_ts >= existing[2]:
                    records[current_pid]["fields"][field_name] = (
                        old_val,
                        new_val,
                        current_ts,
                    )

    return records


# ---------------------------------------------------------------------------
# 2. Build a lookup of processid -> needed BOLD columns from the data package
# ---------------------------------------------------------------------------

# Columns we need from the data package for each matched processid
_BOLD_LOOKUP_COLS = ["sampleid", "identification", "order"]


def build_bold_lookup(
    bold_path: str, process_ids: set[str]
) -> dict[str, dict]:
    """
    Stream through the (potentially huge) BOLD data package TSV and extract
    the rows whose processid is in *process_ids*.

    Uses csv.reader (not DictReader) with index-based column access for
    performance on very large files (20M+ rows).

    Returns { processid: { "sampleid": ..., "identification": ..., "order": ... } }
    """
    lookup: dict[str, dict] = {}
    remaining = set(process_ids)
    lines_read = 0
    report_every = 2_000_000

    with open(bold_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")

        # Read header and build column-index map
        header = next(reader)
        col_idx: dict[str, int] = {}
        for col_name in ["processid"] + _BOLD_LOOKUP_COLS:
            try:
                col_idx[col_name] = header.index(col_name)
            except ValueError:
                print(f"    WARNING: column '{col_name}' not found in data package header")

        pid_col = col_idx.get("processid")
        if pid_col is None:
            print("    ERROR: 'processid' column missing from data package – cannot look up rows")
            return lookup

        for row in reader:
            lines_read += 1
            if lines_read % report_every == 0:
                print(f"    … {lines_read:,} rows scanned, {len(lookup):,} matched, {len(remaining):,} remaining")

            if len(row) <= pid_col:
                continue

            pid = row[pid_col].strip()
            if pid in remaining:
                entry = {}
                for col_name in _BOLD_LOOKUP_COLS:
                    idx = col_idx.get(col_name)
                    if idx is not None and idx < len(row):
                        entry[col_name] = row[idx].strip()
                    else:
                        entry[col_name] = ""
                lookup[pid] = entry
                remaining.discard(pid)
                if not remaining:
                    break  # found everything, stop early

    print(f"    … {lines_read:,} rows scanned total")
    return lookup


# ---------------------------------------------------------------------------
# 3. Map log changes to the output report row
# ---------------------------------------------------------------------------

def _determine_flag(fields: dict) -> str:
    """
    Derive the ``flag|reason`` column directly from the ``status`` field
    in the log.  Returns the most-recent new value, or empty string.
    """
    status = fields.get("status")
    if status:
        return status[1]  # new value (e.g. "valid record", "invalid record", …)
    return ""


def _determine_rank(fields: dict) -> str:
    """
    Derive the ``updated_rank`` column.  If a species-level change happened,
    rank is 'species'.  Can be extended for genus / subfamily etc.
    """
    if "species" in fields:
        return "species"
    return ""


def build_report_row(
    pid: str,
    fields: dict,
    bold_info: dict | None,
) -> dict:
    """
    Build a single output row dict for one processid.
    """
    bold = bold_info or {}
    sampleid = bold.get("sampleid", "")
    identification_bold = bold.get("identification", "")
    order_bold = bold.get("order", "")

    species_change = fields.get("species")  # (old, new, ts) or None
    status_change = fields.get("status")
    curator_notes_change = fields.get("curator_notes")

    # identification = always from the BOLD data package
    identification = identification_bold

    # updated_id = the NEW species value from the log, if species was changed
    updated_id = species_change[1] if species_change else ""

    flag = _determine_flag(fields)
    updated_rank = _determine_rank(fields)

    curator_note = ""
    if curator_notes_change:
        curator_note = curator_notes_change[1]  # new value

    # additionalStatus – pass through the most-recent new value from the log
    additional_status_change = fields.get("additionalStatus")
    additional_status = additional_status_change[1] if additional_status_change else ""

    return {
        "sampleid": sampleid,
        "processid": pid,
        "identification": identification,
        "flag|reason": flag,
        "additionalStatus": additional_status,
        "updated_order": order_bold,
        "updated_rank": updated_rank,
        "updated_id": updated_id,
        "flag_user": "",          # placeholder – filled from log filename
        "identification_method": "",
        "curator_note": curator_note,
        "reference": "",
    }


# ---------------------------------------------------------------------------
# 4. Write the report
# ---------------------------------------------------------------------------

_REPORT_COLUMNS = [
    "sampleid",
    "processid",
    "identification",
    "flag|reason",
    "additionalStatus",
    "updated_order",
    "updated_rank",
    "updated_id",
    "flag_user",
    "identification_method",
    "curator_note",
    "reference",
]


def write_report(rows: list[dict], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=_REPORT_COLUMNS, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------

def _user_from_filename(log_path: str) -> str:
    """
    Extract the curator name from the log filename.
    Takes everything before the first underscore in the stem.
    e.g.  "Bezdek_Ciidae.log"  ->  "Bezdek"
          "BenPrice_Megaloptera_2025.log"  ->  "BenPrice"
    """
    stem = Path(log_path).stem  # filename without extension
    return stem.split("_", 1)[0]


def generate_report_for_log(
    log_path: str,
    records: dict,
    bold_lookup: dict[str, dict],
    output_dir: str,
    log_index: int,
    user_initials: str,
) -> str:
    """
    Build and write the report for a single log file, using the
    pre-built BOLD lookup (shared across all logs).
    """
    user_name = _user_from_filename(log_path)

    rows: list[dict] = []
    for pid in sorted(records, key=lambda p: records[p]["first_ts"]):
        fields = records[pid]["fields"]
        bold_info = bold_lookup.get(pid)
        row = build_report_row(pid, fields, bold_info)
        row["flag_user"] = user_name
        rows.append(row)

    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")
    out_name = f"{log_index}_bold_curation_report_{date_str}_{time_str}_{user_initials}.txt"
    out_path = os.path.join(output_dir, out_name)

    write_report(rows, out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate BOLD curation reports from log files and a BOLD data package."
    )
    parser.add_argument(
        "log_folder",
        help="Path to folder containing .log files",
    )
    parser.add_argument(
        "bold_data_package",
        help="Path to BOLD data package TSV file",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Directory for output reports (default: same as log_folder)",
    )
    parser.add_argument(
        "--initials",
        default="XX",
        help="Initials for the output filename suffix (e.g. CH, BP)",
    )

    args = parser.parse_args()

    log_folder = args.log_folder
    bold_path = args.bold_data_package
    output_dir = args.output_dir or log_folder
    user_initials = args.initials

    os.makedirs(output_dir, exist_ok=True)

    # Collect log files
    log_files = sorted(
        p for p in Path(log_folder).glob("*.log") if p.is_file()
    )

    if not log_files:
        print(f"No .log files found in {log_folder}")
        sys.exit(1)

    print(f"Found {len(log_files)} log file(s) in {log_folder}")
    print(f"BOLD data package: {bold_path}")
    print(f"Output directory:  {output_dir}")
    print()

    # --- Phase 1: parse ALL log files and collect every process ID ----------
    all_log_records: list[tuple[Path, dict]] = []
    all_pids: set[str] = set()

    for log_path in log_files:
        print(f"  Parsing {log_path.name} …")
        records = parse_log_file(str(log_path))
        print(f"    {len(records)} unique process IDs")
        all_log_records.append((log_path, records))
        all_pids.update(records.keys())

    print(f"\n  Total unique process IDs across all logs: {len(all_pids):,}")

    # --- Phase 2: single scan of the BOLD data package ---------------------
    print(f"\n  Scanning BOLD data package (single pass) …")
    bold_lookup = build_bold_lookup(bold_path, all_pids)
    print(f"    {len(bold_lookup):,} / {len(all_pids):,} process IDs found in data package")

    # --- Phase 3: generate one report per log file -------------------------
    print()
    for idx, (log_path, records) in enumerate(all_log_records, start=1):
        if not records:
            print(f"  [{idx}/{len(log_files)}] {log_path.name} – no records, skipping")
            continue

        user_name = _user_from_filename(str(log_path))
        out_path = generate_report_for_log(
            str(log_path),
            records,
            bold_lookup,
            output_dir,
            idx,
            user_initials,
        )
        matched = sum(1 for pid in records if pid in bold_lookup)
        print(
            f"  [{idx}/{len(log_files)}] {log_path.name}  "
            f"user={user_name}  rows={len(records)}  "
            f"bold_matched={matched}  ->  {out_path}"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
