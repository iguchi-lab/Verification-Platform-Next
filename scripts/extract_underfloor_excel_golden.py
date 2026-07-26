"""Extract the reviewable underfloor Excel golden series from floor14.

The source workbook is intentionally not committed.  This script reads cached
OOXML values without opening Excel and writes the compact numeric fixture used
by the integration test.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS}
CELL_RE = re.compile(r"([A-Z]+)(\d+)")
EXPECTED_SHA256 = (
    "e36bc62f5ce46c358e957e85fe9a01f264f0693952840851fab79a1c0e0d385c"
)

SERIES = {
    "q_hat_hs": ("負荷計算", "CG", 5),
    "v_dash_supply_1": ("負荷計算", "CI", 5),
    "v_dash_supply_2": ("負荷計算", "CJ", 5),
    "theta_star_nr": ("負荷計算", "CP", 5),
    "theta_hs_out": ("負荷計算", "FE", 5),
    "v_supply_1": ("負荷計算", "FF", 5),
    "v_supply_2": ("負荷計算", "FG", 5),
    "theta_supply_1": ("負荷計算", "FM", 5),
    "theta_supply_2": ("負荷計算", "FN", 5),
    "theta_hbr_1": ("負荷計算", "FT", 5),
    "theta_hbr_2": ("負荷計算", "FU", 5),
    "theta_nr": ("負荷計算", "FZ", 5),
    "l_star_cs_1": ("負荷計算", "DE", 5),
    "l_star_cs_2": ("負荷計算", "DF", 5),
    "l_star_h_1": ("負荷計算", "DL", 5),
    "l_star_h_2": ("負荷計算", "DM", 5),
    "heating_target": ("床下計算④", "G", 6),
    "cooling_target": ("床下計算④", "R", 6),
    "floor_transfer_temperature": ("床下計算⑤", "P", 6),
    "actual_floor_temperature": ("床下温度", "T", 8774),
    "ground_response": ("床下温度", "AG", 8774),
}


def _sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    targets = {
        relationship.attrib["Id"]: relationship.attrib["Target"].replace(
            "\\", "/"
        )
        for relationship in relationships.findall(
            f"{{{PKG_REL_NS}}}Relationship"
        )
    }
    result = {}
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        target = targets[sheet.attrib[f"{{{REL_NS}}}id"]]
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = f"xl/{target}"
        result[sheet.attrib["name"]] = target
    return result


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def _cell_value(cell: ET.Element, strings: list[str]) -> str | float | None:
    value = cell.find(f"{{{MAIN_NS}}}v")
    if value is None or value.text is None:
        return None
    if cell.attrib.get("t") == "s":
        return strings[int(value.text)]
    if cell.attrib.get("t") == "str":
        return value.text
    return float(value.text)


def _extract_sheet(
    archive: zipfile.ZipFile,
    sheet_path: str,
    requests: dict[str, tuple[str, int]],
    strings: list[str],
) -> dict[str, list[str | float]]:
    columns = {
        column: (name, first_row, first_row + 8759)
        for name, (column, first_row) in requests.items()
    }
    result: dict[str, list[str | float | None]] = {
        name: [None] * 8760 for name in requests
    }
    with archive.open(sheet_path) as stream:
        for _, cell in ET.iterparse(stream, events=("end",)):
            if cell.tag != f"{{{MAIN_NS}}}c":
                continue
            match = CELL_RE.fullmatch(cell.attrib["r"])
            assert match is not None
            cell_column, row_text = match.groups()
            row = int(row_text)
            request = columns.get(cell_column)
            if request is not None:
                name, first_row, last_row = request
                if first_row <= row <= last_row:
                    result[name][row - first_row] = _cell_value(
                        cell,
                        strings,
                    )
            cell.clear()
    complete: dict[str, list[str | float]] = {}
    for name, values in result.items():
        if any(value is None for value in values):
            first_row = requests[name][1]
            missing = [
                first_row + index
                for index, value in enumerate(values)
                if value is None
            ]
            raise ValueError(f"{name} has missing cells: {missing[:5]}")
        complete[name] = [value for value in values if value is not None]
    return complete
def extract(source: Path) -> dict[str, np.ndarray]:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(
            f"unexpected workbook SHA-256: {digest}; "
            f"expected {EXPECTED_SHA256}"
        )

    with zipfile.ZipFile(source) as archive:
        paths = _sheet_paths(archive)
        strings = _shared_strings(archive)
        requests_by_sheet: dict[str, dict[str, tuple[str, int]]] = {}
        for name, (sheet, column, first_row) in SERIES.items():
            requests_by_sheet.setdefault(sheet, {})[name] = (
                column,
                first_row,
            )
        requests_by_sheet["負荷計算"]["season"] = ("L", 5)

        extracted: dict[str, list[str | float]] = {}
        for sheet, requests in requests_by_sheet.items():
            extracted.update(
                _extract_sheet(
                    archive,
                    paths[sheet],
                    requests,
                    strings,
                )
            )
        result = {
            name: np.asarray(extracted[name], dtype=np.float64)
            for name in SERIES
        }
        seasons = extracted["season"]
        result["season_code"] = np.asarray(
            [
                {"中間期": 0, "暖房": 1, "冷房": 2}[str(value)]
                for value in seasons
            ],
            dtype=np.int8,
        )
    return result
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    arrays = extract(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **arrays)
    print(
        f"wrote {args.output} "
        f"({len(arrays)} series, {args.output.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    main()
