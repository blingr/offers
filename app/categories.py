"""Roll marktguru's ~150 fine-grained leaf categories up into a small set of
broad, tickable groups (Fleisch, Milchprodukte, Obst, Gemüse, ...).

marktguru's own category tree references parent ids it doesn't expose, so a
data-driven roll-up isn't reliable. Instead we classify each offer's leaf
category name with an ordered keyword match — first group whose keyword is a
substring of the (lowercased) category name wins.
"""

# Canonical group order (also the order shown in the UI). Emoji live in the
# frontend; here we keep plain labels so they're easy to store and query.
GROUP_ORDER = [
    "Obst",
    "Gemüse",
    "Fleisch & Wurst",
    "Fisch & Meeresfrüchte",
    "Milchprodukte & Eier",
    "Brot & Gebäck",
    "Süßes & Snacks",
    "Tiefkühl & Fertig",
    "Getränke",
    "Alkohol",
    "Grundnahrung & Vorrat",
    "Drogerie & Haushalt",
    "Haustier",
    "Sonstiges",
]

# A few short/ambiguous category names matched exactly (checked first) so their
# letters don't collide with substrings (e.g. "eis" inside "reis"/"fleisch").
_EXACT = {
    "eis": "Süßes & Snacks",
    "reis": "Grundnahrung & Vorrat",
    "reisen": "Sonstiges",
    "wein": "Alkohol",
    "tee": "Getränke",
    "veganes": "Sonstiges",
    "gin": "Alkohol",
    "mais": "Gemüse",
    "bohnen": "Gemüse",
}

# Ordered (label, keywords). First keyword hit wins — order resolves overlaps,
# e.g. Tiefkühl before Brot so "Tiefkühlbackwaren" doesn't land in Brot.
_GROUPS = [
    ("Tiefkühl & Fertig", ["tiefkühl", "fertiggericht", "pizza", "pommes"]),
    ("Süßes & Snacks", [
        "schokolade", "praline", "keks", "bonbon", "gummi", "riegel", "chips",
        "salzgebäck", "popcorn", "cracker", "nüsse", "knabber", "süßwaren",
        "süßigkeit", "eiscreme", "speiseeis", "snacks", "imbiss",
    ]),
    ("Obst", [
        "obst", "frucht", "frücht", "beeren", "apfel", "äpfel", "banane",
        "trauben", "zitrus", "melone", "mango", "kirsch", "pflaum",
    ]),
    ("Gemüse", [
        "gemüse", "tomate", "salat", "kartoffel", "erdäpfel", "zwiebel",
        "paprika", "karotte", "gurke", "pilz", "champignon", "avocado",
        "kraut", "kräuter", "brokkoli", "spinat", "zucchini",
    ]),
    ("Fleisch & Wurst", [
        "fleisch", "geflügel", "hähnch", "huhn", "pute", "schinken", "würst",
        "wurst", "salami", "faschiert", "speck", "leberkäse", "steak",
        "schnitzel", "gulasch", "bacon",
    ]),
    ("Fisch & Meeresfrüchte", [
        "fisch", "meeresfrüchte", "lachs", "thunfisch", "garnele", "scampi",
        "muschel",
    ]),
    ("Milchprodukte & Eier", [
        "käse", "joghurt", "milch", "butter", "topfen", "obers", "sahne",
        "rahm", "eier", "molkerei", "quark", "pudding", "dessert",
    ]),
    ("Brot & Gebäck", [
        "brot", "brötchen", "semmel", "toast", "kuchen", "feinback",
        "backwaren", "gebäck", "croissant", "strudel",
    ]),
    ("Alkohol", [
        "bier", "wein", "sekt", "likör", "spirituos", "wodka", "cocktail",
        "whisky", "whiskey", "schnaps", "aperitif", "prosecco", "rum", "brand",
        "champagner", "grappa", "cognac", "tequila",
    ]),
    ("Getränke", [
        "softdrink", "wasser", "kaffee", "kakao", "saft", "säfte", "limonade",
        "energy", "sirup", "smoothie", "eistee",
    ]),
    ("Grundnahrung & Vorrat", [
        "nudel", "pasta", "öl", "fett", "zucker", "mehl", "konserv", "sauce",
        "soße", "aufstrich", "dip", "müsli", "cornflakes", "honig",
        "marmelade", "essig", "gewürz", "salz", "suppe", "brühe", "getreide",
        "antipasti", "fonds",
    ]),
    ("Drogerie & Haushalt", [
        "waschmittel", "spülmittel", "reinig", "duschgel", "haarpflege",
        "shampoo", "deo", "windel", "zahn", "seife", "körperpflege", "hygiene",
        "kosmetik", "papier", "tücher", "pflege", "putz", "küchenrolle",
        "creme", "lotion", "düfte", "maniküre", "sonnenschutz",
    ]),
    ("Haustier", ["futter", "tierbedarf", "katze", "hund", "tier"]),
]


def classify(category):
    """Return the broad group label for a leaf category name."""
    if not category:
        return "Sonstiges"
    c = category.strip().lower()
    if c in _EXACT:
        return _EXACT[c]
    for label, keywords in _GROUPS:
        if any(k in c for k in keywords):
            return label
    return "Sonstiges"
