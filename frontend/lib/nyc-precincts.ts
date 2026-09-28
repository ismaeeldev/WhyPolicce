/**
 * NYC precinct <-> neighborhood lookup — Scope Revision 1 §4.2
 * (AgentGuide/newscoperev1.md). A deliberately minimal, NYC-only,
 * approximate first version — the client's own wording only asked for "a
 * lightweight location auto-complete or lookup tool" with no stated city
 * scope or accuracy requirement, so this starts as small and reversible
 * as that wording allows: no new paid geocoding API, no external network
 * call, just a real, already-verified precinct/neighborhood map reused
 * from this project's own backend/app/services/ingestion/nyc_precincts.py
 * (NYPD's own published precinct directory, independently re-verified
 * there — see that file's own docstring for the sourcing detail).
 *
 * Nationwide coverage and real GIS/polygon accuracy are both explicitly
 * out of scope for this first pass — see this feature's own entry in
 * AgentGuide/newscoperev1.md §4.2 for the open questions that would need
 * answering before either of those is worth building.
 */

export type PrecinctEntry = {
  precinct: string;
  neighborhoods: string;
};

// Mirrors backend/app/services/ingestion/nyc_precincts.py's
// PRECINCT_NEIGHBORHOODS exactly — kept as a second, frontend-side copy
// rather than a shared package, matching this codebase's own established
// convention of small, per-side static reference lists (see
// frontend/lib/us-states.ts).
const PRECINCT_NEIGHBORHOODS: Record<string, string> = {
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
  "120": "St. George/Stapleton",
  "121": "Westerleigh/Bulls Head",
  "122": "New Dorp/Great Kills",
  "123": "Tottenville/Annadale",
};

export const NYC_PRECINCTS: PrecinctEntry[] = Object.entries(PRECINCT_NEIGHBORHOODS).map(
  ([precinct, neighborhoods]) => ({ precinct, neighborhoods }),
);

/**
 * Approximate, substring-match lookup — typing part of a neighborhood
 * name (e.g. "harlem") returns every precinct whose neighborhood text
 * contains it. Deliberately not exact/exhaustive: several precincts
 * share overlapping neighborhood names (e.g. three separate "Harlem"
 * precincts), so this returns candidates for the citizen to pick from
 * rather than silently guessing a single "correct" one.
 */
export function findPrecinctsByNeighborhood(query: string): PrecinctEntry[] {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];
  return NYC_PRECINCTS.filter((entry) => entry.neighborhoods.toLowerCase().includes(q));
}
