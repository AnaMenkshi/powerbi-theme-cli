"""
Local PBIX Client — No Azure, No REST API, No secrets.
Works directly with your .pbix file on disk.

A .pbix file is a ZIP archive containing:
  - Report/Layout          <- page/visual definitions (JSON)
  - Report/StaticResources/RegisteredResources/  <- theme files
  - DataModel              <- compressed data model
  - [Content_Types].xml
  - SecurityBindings
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime


class PBIClient:
    """
    Reads and writes .pbix files directly — zero Azure dependency.
    All operations are local and offline.
    """

    def __init__(self, pbix_path: str = None, *args, **kwargs):
        # Accept and ignore any Azure args so main file needs minimal changes
        self.pbix_path    = pbix_path
        self.workspace_id = "local"
        self._layout      = None  # cached parsed layout

    # ── File selection ────────────────────────────────────────────────────────

    def set_pbix(self, path: str):
        """Point the client at a .pbix file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix.lower() != ".pbix":
            raise ValueError(f"Expected a .pbix file, got: {path.suffix}")
        self.pbix_path = str(path)
        self._layout   = None
        print(f"   Loaded: {path.name}  ({path.stat().st_size // 1024} KB)")

    def find_pbix_files(self, search_dir: str = None) -> list:
        """Scan common locations for .pbix files and return a list of paths."""
        search_dirs = []
        if search_dir:
            search_dirs.append(Path(search_dir))
        home = Path.home()
        search_dirs += [
            home / "Documents",
            home / "Desktop",
            home / "Downloads",
            home / "OneDrive" / "Documents",
            home / "OneDrive" / "Desktop",
        ]
        found = []
        for d in search_dirs:
            if d.exists():
                found += list(d.rglob("*.pbix"))
        return list(set(found))

    # ── Layout reading ────────────────────────────────────────────────────────

    def _read_layout(self) -> dict:
        """Extract and parse the Report/Layout JSON from the .pbix ZIP."""
        if self._layout:
            return self._layout
        with zipfile.ZipFile(self.pbix_path, "r") as z:
            names        = z.namelist()
            layout_entry = next((n for n in names if n == "Report/Layout"), None)
            if not layout_entry:
                raise ValueError("Could not find Report/Layout inside the .pbix file.")
            raw = z.read(layout_entry)
            # Power BI stores Layout as UTF-16-LE
            try:
                text = raw.decode("utf-16-le")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            text          = text.lstrip("\ufeff")
            self._layout  = json.loads(text)
        return self._layout

    def list_reports(self) -> list:
        """Return a single-item list representing the local .pbix file."""
        if not self.pbix_path:
            return []
        name = Path(self.pbix_path).stem
        return [{"id": "local", "name": name, "path": self.pbix_path}]

    def list_pages(self, report_id: str = "local") -> list:
        """Read page names directly from Report/Layout."""
        layout = self._read_layout()
        pages  = layout.get("sections", [])
        result = []
        for p in pages:
            result.append({
                "name":        p.get("name", ""),
                "displayName": p.get("displayName", p.get("name", "Page")),
                "order":       p.get("ordinal", 0),
            })
        return sorted(result, key=lambda x: x["order"])

    def list_visuals(self, report_id: str, page_name: str) -> list:
        """Return visuals for a given page."""
        layout = self._read_layout()
        for section in layout.get("sections", []):
            if section.get("name") == page_name or section.get("displayName") == page_name:
                visuals = []
                for vc in section.get("visualContainers", []):
                    cfg_raw = vc.get("config", "{}")
                    try:
                        cfg = json.loads(cfg_raw) if isinstance(cfg_raw, str) else cfg_raw
                    except Exception:
                        cfg = {}
                    v_type = cfg.get("singleVisual", {}).get("visualType", "unknown")
                    visuals.append({
                        "id":     vc.get("name", ""),
                        "type":   v_type,
                        "x":      vc.get("x", 0),
                        "y":      vc.get("y", 0),
                        "width":  vc.get("width", 0),
                        "height": vc.get("height", 0),
                    })
                return visuals
        return []

    def get_dataset_schema(self, dataset_id: str = "local") -> dict:
        """Try to read table/column info from DataModelSchema if present."""
        with zipfile.ZipFile(self.pbix_path, "r") as z:
            names         = z.namelist()
            schema_entry  = next((n for n in names if "DataModelSchema" in n), None)
            if not schema_entry:
                return {}
            raw = z.read(schema_entry)
            try:
                text = raw.decode("utf-16-le").lstrip("\ufeff")
                return json.loads(text)
            except Exception:
                return {}

    # ── Theme injection ───────────────────────────────────────────────────────

    def apply_theme(self, report_id: str, theme_json: dict) -> bool:
        """
        Inject a theme JSON into the .pbix file directly.
        Creates a timestamped backup first, then rebuilds the ZIP.
        Returns True on success.
        """
        if not self.pbix_path:
            return False

        pbix_path      = Path(self.pbix_path)
        safe_name      = theme_json.get("name", "PBIAgentTheme").replace(" ", "_").replace("\u2014","").replace("/","")
        theme_filename = f"{safe_name}.json"
        theme_entry    = f"Report/StaticResources/RegisteredResources/{theme_filename}"

        # Backup
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = pbix_path.with_name(f"{pbix_path.stem}_backup_{ts}.pbix")
        shutil.copy2(pbix_path, backup)
        print(f"   Backup saved -> {backup.name}")

        # Rebuild ZIP with theme injected
        tmp = pbix_path.with_suffix(".pbix.tmp")
        try:
            with zipfile.ZipFile(self.pbix_path, "r") as zin, \
                 zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:

                existing_entries = [i.filename for i in zin.infolist()]
                theme_written    = False

                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename == theme_entry:
                        zout.writestr(item, json.dumps(theme_json, indent=2).encode("utf-8"))
                        theme_written = True
                    else:
                        zout.writestr(item, data)

                # Add theme entry if it did not exist yet
                if not theme_written:
                    zout.writestr(theme_entry, json.dumps(theme_json, indent=2).encode("utf-8"))

            os.replace(tmp, pbix_path)
            self._layout = None  # invalidate cache
            return True

        except Exception as e:
            print(f"   Direct injection failed: {e}")
            print(f"   Use the saved JSON file and import manually via Desktop.")
            if tmp.exists():
                os.remove(tmp)
            return False

    def execute_dax(self, dataset_id: str, dax_query: str) -> dict:
        """DAX execution requires Power BI Service — not available locally."""
        print("   DAX execution requires Power BI Service. Use the Desktop DAX editor instead.")
        return {}

    def refresh_dataset(self, dataset_id: str) -> bool:
        """Dataset refresh requires Power BI Service — not available locally."""
        print("   Dataset refresh requires Power BI Service.")
        return False
