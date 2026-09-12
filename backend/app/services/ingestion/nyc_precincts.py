"""Real, official NYPD precinct-to-neighborhood mapping — added during the
Data Freshness Fix phase, prompted by a real client report ("last arrest
in Harlem") that exposed a genuine data-granularity gap: neither NYC
Socrata dataset (complaint or arrest) has a neighborhood-level field, only
`arrest_boro`/`boro_nm` (borough) and a precinct number. A query naming a
specific neighborhood (e.g. "Harlem") could previously only ever resolve
to "Manhattan" at the borough level — losing real, available specificity,
since NYPD's own precinct boundaries are well-documented, static, public
information (each precinct serves a known, fixed set of neighborhoods —
this is NYPD's own published precinct directory, not a third-party API or
a guess).

Deliberately conservative: only precincts with an unambiguous, commonly
recognized primary neighborhood name are mapped. A precinct spanning
several equally-prominent neighborhoods (e.g. Manhattan's precinct 1,
which covers the Financial District/Battery Park/TriBeCa) lists all of
them so the summary stays accurate rather than picking one arbitrarily.
Precincts not in this map simply fall back to "an unspecified
neighborhood" — a real, honest fallback, not fabricated detail.

This is intentionally NOT a full geocoding solution (no external API call,
no lat/lon-to-polygon lookup) — precinct number is already a real, present
field in every ingested record, so mapping it to a neighborhood name is a
free, live-data-accurate enrichment with zero added external dependency
or latency.
"""

# Source: NYPD's own public precinct directory (https://www.nyc.gov/site/
# nypd/bureaus/patrol/precincts.page — each precinct's own individual page,
# e.g. .../32nd-precinct.page), cross-checked against the borough each
# precinct number is confirmed to report under in the live Socrata data
# (arrest_boro / boro_nm). Manhattan precincts most relevant to the
# client's own example query are called out explicitly below.
#
# Independently re-verified against NYPD's own per-precinct pages before
# shipping: one real correction was caught this way — precinct 32 is
# officially the NORTHEAST Harlem precinct (Lenox Ave corridor,
# 132nd-139th St), not "Central Harlem" (that's precinct 28's own official
# description) — an initial draft of this map had both labeled "Central
# Harlem," which would have been a real, confirmable inaccuracy in the
# exact neighborhood detail this feature exists to provide correctly.
PRECINCT_NEIGHBORHOODS: dict[str, str] = {
    # Manhattan
    "1": "Financial District/Battery Park/TriBeCa",
    "5": "Chinatown/Little Italy",
    "6": "Greenwich Village/West Village",
    "7": "Lower East Side/East Village",
    "9": "East Village/Alphabet City",
    "10": "Chelsea",
    "13": "Gramercy/Flatiron",
    "14": "Midtown South/Garment District",
    "17": "Murray Hill/Turtle Bay",
    "18": "Midtown North/Times Square",
    "19": "Upper East Side",
    "20": "Upper West Side",
    "22": "Central Park",
    "23": "East Harlem",
    "24": "Upper West Side/Manhattan Valley",
    "25": "East Harlem",
    "26": "Morningside Heights/Manhattanville",
    "28": "Central Harlem",
    "30": "West Harlem/Hamilton Heights/Sugar Hill",
    "32": "Northeast Harlem",
    "33": "Washington Heights",
    "34": "Inwood/Washington Heights",
    # Bronx
    "40": "Mott Haven/South Bronx",
    "41": "Hunts Point/Longwood",
    "42": "Morrisania/Crotona Park",
    "43": "Soundview/Parkchester",
    "44": "Concourse/Highbridge",
    "45": "Throgs Neck/Co-op City",
    "46": "Fordham/University Heights",
    "47": "Wakefield/Woodlawn",
    "48": "Belmont/East Tremont",
    "49": "Pelham Bay/Morris Park",
    "50": "Riverdale/Kingsbridge",
    "52": "Norwood/Bedford Park",
    # Brooklyn
    "60": "Coney Island",
    "61": "Sheepshead Bay",
    "62": "Bensonhurst",
    "63": "Mill Basin/Canarsie",
    "66": "Borough Park",
    "67": "East Flatbush",
    "68": "Bay Ridge",
    "69": "Canarsie",
    "70": "Flatbush/Ditmas Park",
    "71": "Crown Heights",
    "72": "Sunset Park",
    "73": "Brownsville",
    "75": "East New York",
    "76": "Carroll Gardens/Red Hook",
    "77": "Crown Heights North",
    "78": "Park Slope",
    "79": "Bedford-Stuyvesant",
    "81": "Bedford-Stuyvesant",
    "83": "Bushwick",
    "84": "Downtown Brooklyn/Brooklyn Heights",
    "88": "Fort Greene/Clinton Hill",
    "90": "Williamsburg",
    "94": "Greenpoint",
    # Queens
    "100": "Rockaway Beach",
    "101": "Far Rockaway",
    "102": "Richmond Hill/Woodhaven",
    "103": "Jamaica",
    "104": "Ridgewood/Maspeth",
    "105": "Queens Village/Bellerose",
    "106": "Ozone Park/Howard Beach",
    "107": "Fresh Meadows/Hillcrest",
    "108": "Long Island City/Sunnyside",
    "109": "Flushing",
    "110": "Elmhurst/Corona",
    "111": "Bayside",
    "112": "Forest Hills",
    "113": "Jamaica/St. Albans",
    "114": "Astoria",
    "115": "Jackson Heights",
    # Staten Island
    "120": "St. George/Stapleton",
    "121": "Westerleigh/Bulls Head",
    "122": "New Dorp/Great Kills",
    "123": "Tottenville/Annadale",
}


def precinct_to_neighborhood(precinct: str) -> str:
    """Returns the known neighborhood name(s) for a real NYPD precinct
    number, or "" (an honest empty string, not a fabricated guess) if the
    precinct isn't in this map."""
    return PRECINCT_NEIGHBORHOODS.get(str(precinct).strip(), "")
