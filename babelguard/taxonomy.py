"""A global scam taxonomy: what the scam pretends to be, and which levers it pulls.

Scam types are defined by the pretext, so the same type covers the same playbook in every country
(a bank "KYC update" in India, a "card blocked" alert in Spain, a "GCash restricted" text in the
Philippines are all `bank_payment`). Lures follow Stajano and Wilson's principles of scams
(Commun. ACM 2011), the scheme the IMC 2025 smishing dataset also uses, so results stay comparable.
"""

SCAM_TYPES = {
    "bank_payment": "Bank, card, wallet or payment app: account blocked, KYC update, suspicious login, "
                    "refund (UPI, M-Pesa, GCash, PIX ...)",
    "government": "Tax refund, fine, subsidy, benefit, customs duty, police or court ('digital arrest')",
    "delivery": "Parcel held, redelivery fee, address check",
    "telecom_utility": "SIM block or re-verification, points expiring, electricity or water disconnection",
    "family_emergency": "'Hi mum/dad, new number', relative in hospital or in trouble",
    "prize_lottery": "Won a lottery, prize, cashback or reward",
    "job_task": "Part-time job, 'like and earn', task scams",
    "investment_crypto": "Trading groups, crypto platforms, pig-butchering",
    "loan_credit": "Pre-approved or instant loan, debt relief",
    "romance_social": "Wrong-number openers, dating, befriending",
    "account_security": "Account compromised, verification code request, tech support",
    "extortion": "Sextortion, threats, blackmail",
}
OTHER_LABELS = {
    "spam": "Unwanted marketing that is not fraud",
    "legit": "Genuine message (hard negatives: real OTPs, bank alerts, government notices)",
}
LURES = ["time/urgency", "authority", "distraction", "need and greed", "kindness", "herd", "dishonesty"]

# IMC 2025 scam_type -> ours. "others" carries no type and needs relabelling.
IMC25_TYPES = {
    "banking": "bank_payment", "government": "government", "delivery": "delivery",
    "telecom": "telecom_utility", "hey mum/dad": "family_emergency", "wrong number": "romance_social",
    "spam": "spam", "others": None,
}

# Language name -> (ISO 639-1/3 code, region). Region follows where the language is mainly used.
LANGUAGES = {
    "english": ("en", "global"), "spanish": ("es", "europe_americas"), "portuguese": ("pt", "europe_americas"),
    "french": ("fr", "europe_africa"), "dutch": ("nl", "europe"), "german": ("de", "europe"),
    "italian": ("it", "europe"), "polish": ("pl", "europe"), "danish": ("da", "europe"),
    "swedish": ("sv", "europe"), "norwegian": ("no", "europe"), "finnish": ("fi", "europe"),
    "czech": ("cs", "europe"), "greek": ("el", "europe"), "romanian": ("ro", "europe"),
    "hungarian": ("hu", "europe"), "catalan": ("ca", "europe"), "slovenian": ("sl", "europe"),
    "estonian": ("et", "europe"), "latvian": ("lv", "europe"), "russian": ("ru", "europe_asia"),
    "ukrainian": ("uk", "europe"), "turkish": ("tr", "middle_east"), "arabic": ("ar", "middle_east_africa"),
    "persian": ("fa", "middle_east"), "hebrew": ("he", "middle_east"), "urdu": ("ur", "south_asia"),
    "hindi": ("hi", "south_asia"), "bengali": ("bn", "south_asia"), "kannada": ("kn", "south_asia"),
    "tamil": ("ta", "south_asia"), "telugu": ("te", "south_asia"), "marathi": ("mr", "south_asia"),
    "gujarati": ("gu", "south_asia"), "malayalam": ("ml", "south_asia"), "odia": ("or", "south_asia"),
    "punjabi": ("pa", "south_asia"), "nepali": ("ne", "south_asia"), "sinhala": ("si", "south_asia"),
    "indonesian": ("id", "southeast_asia"), "malay": ("ms", "southeast_asia"), "tagalog": ("tl", "southeast_asia"),
    "thai": ("th", "southeast_asia"), "vietnamese": ("vi", "southeast_asia"), "khmer": ("km", "southeast_asia"),
    "burmese": ("my", "southeast_asia"), "japanese": ("ja", "east_asia"), "chinese": ("zh", "east_asia"),
    "korean": ("ko", "east_asia"), "swahili": ("sw", "africa"), "igbo": ("ig", "africa"),
    "hausa": ("ha", "africa"), "yoruba": ("yo", "africa"), "amharic": ("am", "africa"),
    "zulu": ("zu", "africa"), "somali": ("so", "africa"), "afrikaans": ("af", "africa"),
    "azerbaijani": ("az", "caucasus_central_asia"), "kazakh": ("kk", "caucasus_central_asia"),
}


def language(name):
    """(code, region) for a language name in any case; ('und', 'unknown') if not known."""
    return LANGUAGES.get((name or "").strip().lower(), ("und", "unknown"))
