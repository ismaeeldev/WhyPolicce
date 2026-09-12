import re
from pathlib import Path

# Real folder-organization fix: this whole scratch_* set (Bellevue/Fed
# Way/Greeley/Kirkland/Lakewood raw ArcGIS response dumps from an earlier
# city-research phase) used to live loose at the backend/ root, discovered
# and cleaned up during a real project-structure audit. Moved here rather
# than deleted outright — these are throwaway exploration artifacts, not
# meant to be committed or relied on long-term, but retain real research
# value if a future phase revisits Washington-state cities. Path updated
# to be relative to this file's own new location, not the old hardcoded
# absolute backend-root path.
txt = (Path(__file__).parent / "scratch_kirkland.json").read_text(encoding="utf-8", errors="ignore")
pattern = r'https://services[0-9]*\.arcgis\.com/[A-Za-z0-9]+/arcgis/rest/services/[A-Za-z0-9_/%\.\-]+'
urls=set(re.findall(pattern, txt))
for u in sorted(urls):
    print(u)
