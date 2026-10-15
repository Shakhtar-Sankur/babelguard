import random

from babelguard.engine import CampaignEngine
from babelguard.parallel import ingest_parallel

LURES = [
    "Your parcel is held at customs. Pay the {fee} fee at https://{d}.example/track within 24 hours.",
    "Dear customer, your account is blocked. Update KYC at http://{d}.example/kyc or call +91 98{n}.",
    "आपका खाता बंद कर दिया गया है। तुरंत {d}.example/verify पर सत्यापित करें, शुल्क {fee}।",
    "Su paquete está retenido. Pague {fee} en https://{d}.example/pago hoy.",
    "ସୂଚନା: ଆପଣଙ୍କ ପାର୍ସଲ ରଖାଯାଇଛି, {d}.example ରେ {fee} ଦିଅନ୍ତୁ।",
    "You won a prize! Claim via WhatsApp +44 7{n} before midnight.",
]


def messages(n, seed=0):
    rng = random.Random(seed)
    for k in range(n):
        lure = rng.choice(LURES)
        text = lure.format(fee=rng.choice(["$1.99", "₹49", "€2"]), d=f"site{rng.randrange(40)}",
                           n=f"{rng.randrange(10**8):08d}")
        if rng.random() < 0.3:
            text += " " + rng.choice(["Reply STOP", "ref " + str(rng.randrange(1000)), "!!"])
        yield text, rng.choice(["en", "hi", "es", "or"]), float(k), None


def partition(engine):
    return [engine.find(i) for i in range(len(engine.parent))]


def test_parallel_ingest_matches_serial():
    serial = CampaignEngine()
    for text, lang, t, country in messages(3000):
        serial.ingest(text, lang, t, country)
    par = CampaignEngine()
    out = list(ingest_parallel(par, messages(3000), workers=2, chunksize=64))
    assert [a.message for a in out] == list(range(3000))
    assert partition(par) == partition(serial)
    assert {k: (c.size, sorted(c.languages), sorted(c.indicators)) for k, c in par.campaigns.items()} == \
           {k: (c.size, sorted(c.languages), sorted(c.indicators)) for k, c in serial.campaigns.items()}
