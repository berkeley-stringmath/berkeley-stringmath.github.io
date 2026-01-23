#!/usr/bin/env python3
import csv
import io
import pathlib
import re
import argparse
import sys
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX_OLD = ROOT / "index-old.html"
DATA_DIR = ROOT / "data"


def read_text(path):
    return path.read_text(encoding="utf-8")


def find_default_config():
    if not INDEX_OLD.exists():
        raise RuntimeError("index-old.html not found; pass prefix and gid explicitly.")
    text = read_text(INDEX_OLD)
    m_prefix = re.search(r'PUBLISHED_PREFIX\s*=\s*"([^"]+)"', text)
    m_gid = re.search(r'CONFIG_GID\s*=\s*"([^"]+)"', text)
    if not m_prefix or not m_gid:
        raise RuntimeError("Could not find PUBLISHED_PREFIX or CONFIG_GID in index-old.html.")
    return m_prefix.group(1), m_gid.group(1)


def fetch_csv_text(url):
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def parse_csv_objects(text):
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    header = [h.strip().lower() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not r or all((c or "").strip() == "" for c in r):
            continue
        obj = {}
        for i, key in enumerate(header):
            if not key:
                continue
            obj[key] = (r[i] if i < len(r) else "").rstrip()
        out.append(obj)
    return out


def csv_url(prefix, gid):
    return f"{prefix}?gid={gid}&single=true&output=csv"


def build_talk_block(t):
    date = (t.get("date") or "").strip()
    speaker = (t.get("speaker") or "").strip()
    affiliation = (t.get("affiliation") or "").strip()
    title = (t.get("title") or "").strip()
    abstract = (t.get("abstract") or "").rstrip()

    parts = [date]
    if speaker:
        parts.append(speaker)
        if affiliation:
            parts.append(f"*{affiliation}*")
    header = " \u2014 ".join(p for p in parts if p)

    lines = [f"## {header}"]
    if title:
        lines.append(f"**Title:** {title}")
    if abstract:
        lines.append("")
        lines.append("Abstract:")
        lines.extend(abstract.splitlines())
    return lines


def build_md(organizers, time, location, talks):
    lines = []
    if organizers:
        lines.append(f"Organizers: {organizers}")
    if time:
        lines.append(f"Time: {time}")
    if location:
        lines.append(f"Location: {location}")
    lines.append("")
    lines.append("---")
    lines.append("")

    first = True
    for t in talks:
        if not (t.get("date") or "").strip():
            continue
        if not first:
            lines.append("")
            lines.append("---")
            lines.append("")
        first = False
        lines.extend(build_talk_block(t))
    lines.append("")
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser(description="Generate semester markdown files from the Google Sheet.")
    parser.add_argument(
        "-f",
        "--semester",
        action="append",
        dest="semesters",
        default=[],
        help="Semester slug to regenerate (can be repeated). Example: -f 2021-fall",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available semester slugs from the config sheet and exit.",
    )
    args = parser.parse_args(argv)

    prefix, config_gid = find_default_config()
    config_url = csv_url(prefix, config_gid)
    config_text = fetch_csv_text(config_url)
    config_rows = parse_csv_objects(config_text)
    if not config_rows:
        raise RuntimeError("Config CSV is empty.")

    DATA_DIR.mkdir(exist_ok=True)

    want = set(s.strip() for s in args.semesters if s and s.strip())
    if args.list:
        for row in config_rows:
            semester = (row.get("semester") or "").strip()
            if semester:
                print(semester)
        return

    for row in config_rows:
        semester = (row.get("semester") or "").strip()
        gid = (row.get("gid") or "").strip()
        if not semester or not gid:
            continue
        if want and semester not in want:
            continue

        organizers = (row.get("organizers") or "").strip()
        time = (row.get("time") or "").strip()
        location = (row.get("location") or "").strip()

        talks_url = csv_url(prefix, gid)
        talks_text = fetch_csv_text(talks_url)
        talks = parse_csv_objects(talks_text)

        md = build_md(organizers, time, location, talks)
        out_path = DATA_DIR / f"{semester}.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
