"""National NIBRS offense-code lookup table — plan.md Step 9 Phase 5.

Real fix, not a guess: Milwaukee's dataset only exposes raw NIBRS codes
(`Offense_All`, e.g. "90Z;13B") with no description field of its own —
confirmed directly against its full schema (`datastore_search_sql` on the
resource returns exactly 8 real columns, none of them a description).
A real end-to-end verification query ("Any crime reported in Milwaukee?")
correctly retrieved genuine Milwaukee records but the answer surfaced raw
codes like "290" and "90J" instead of readable offense names — honest,
not fabricated, but a real quality gap since every other city's summary
uses a human-readable offense name.

This table was pulled from a DIFFERENT city's own live dataset (Memphis's
MPD_Public_Safety_Incidents, which DOES publish both `UCR_Incident_Code`
and `UCR_Description` side by side) via a real grouped query, not
hand-typed from memory or an external reference — NIBRS codes are a
national FBI standard, so a mapping confirmed against one real city's
live data is valid for any other city using the same code set.
"""

NIBRS_CODE_DESCRIPTIONS = {
    "13A": "Aggravated Assault",
    "23H": "All Other Larceny",
    "90Z": "All Other Offenses",
    "720": "Animal Cruelty",
    "200": "Arson",
    "40B": "Assisting/Promoting Prostitution",
    "90A": "Bad Checks",
    "39A": "Betting/Wagering",
    "510": "Bribery",
    "220": "Burglary/Breaking & Entering",
    "26G": "Computer Hacking/Invasion",
    "250": "Counterfeiting/Forgery",
    "26B": "Credit Card/ATM Fraud",
    "90B": "Curfew/Loitering/Vagrancy Violations",
    "290": "Destruction/Damage/Vandalism of Property",
    "90C": "Disorderly Conduct",
    "90D": "Driving Under the Influence",
    "35B": "Drug/Narcotic Equipment Violations",
    "35A": "Drug/Narcotic Violations",
    "90E": "Drunkenness",
    "270": "Embezzlement",
    "210": "Extortion/Blackmail",
    "26A": "False Pretenses/Swindle/Confidence Game",
    "90F": "Family Offenses, Nonviolent",
    "39C": "Gambling Equipment Violations",
    "26F": "Identity Theft",
    "26C": "Impersonation",
    "13C": "Intimidation",
    "09C": "Justifiable Homicide",
    "100": "Kidnapping/Abduction",
    "90G": "Liquor Law Violations",
    "240": "Motor Vehicle Theft",
    "09A": "Murder/Non-Negligent Manslaughter",
    "09D": "Negligent Vehicular Manslaughter",
    "09B": "Negligent Manslaughter",
    "39B": "Operating/Promoting/Assisting Gambling",
    "90H": "Peeping Tom",
    "23A": "Pocket-Picking",
    "370": "Pornography/Obscene Material",
    "40A": "Prostitution",
    "40C": "Purchasing Prostitution",
    "23B": "Purse-Snatching",
    "120": "Robbery",
    "23C": "Shoplifting",
    "13B": "Simple Assault",
    "13D": "Stalking",
    "280": "Stolen Property Offenses",
    "23D": "Theft From a Building",
    "23F": "Theft From a Motor Vehicle",
    "23E": "Theft From Coin-Operated Machine or Device",
    "23G": "Theft of Motor Vehicle Parts/Accessories",
    "90J": "Trespass of Real Property",
    "520": "Weapon Law Violations",
    "26D": "Welfare Fraud",
    "26E": "Wire Fraud",
}


def describe_nibrs_code(code: str) -> str:
    """Returns a real, human-readable offense name for a known NIBRS code,
    or the raw code itself if unrecognized — never fabricates a
    description for a code not in the verified table above."""
    return NIBRS_CODE_DESCRIPTIONS.get(code.strip().upper(), code.strip())
