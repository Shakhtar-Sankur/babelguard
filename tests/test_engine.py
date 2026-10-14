"""Streaming engine: links on arrival, matches batch linking, and scales its indexes."""
from babelguard.dataset import Record
from babelguard.engine import CampaignEngine
from babelguard.loadgen import bcubed, stream


def test_links_across_languages_by_indicator_and_by_text():
    e = CampaignEngine()
    a = e.ingest("Your SBI KYC expires today. Update at hxxps://sbi-kyc-update[.]com or call 98765 43210", "en")
    b = e.ingest("आपका SBI KYC आज समाप्त। अपडेट करें: sbi-kyc-update.com या कॉल करें ९८७६५ ४३२१०", "hi")
    c = e.ingest("Congratulations! You won 25 lakh in the KBC lottery. Call our manager to claim.", "en")
    d = e.ingest("Congratulations!! You won 25 lakh in KBC lottery. Call our manager now to claim.", "en")
    assert a.new and not b.new and b.campaign == a.campaign
    assert {"domain:sbi-kyc-update.com", "phone:876543210"} & set(b.reasons)
    assert c.new and d.campaign == c.campaign and "text" in d.reasons
    e.ingest("Final notice: hxxps://sbi-kyc-update[.]com", "en")
    assert e.find(3) == c.campaign == 2 and e.find(1) == 0            # ids never change once given
    camp = e.campaign_of(b.message)
    assert camp.size == 3 and camp.languages == {"en", "hi"}


def test_legitimate_and_overused_indicators_do_not_link():
    e = CampaignEngine(max_indicator_campaigns=3)
    a = e.ingest("Official notice: visit www.sbi.co.in for KYC rules", "en")
    b = e.ingest("Reminder from the branch: www.sbi.co.in has the new timings", "en")
    assert a.campaign != b.campaign
    ids = [e.ingest(f"message {k} {'x' * k} call 98765 43210", "en") for k in range(1, 9)]
    assert len({e.find(x.message) for x in ids}) >= 1
    assert e.stats["indicators_blocked"] in (0, 1)


def test_bcubed():
    assert bcubed([1, 1, 2, 2], ["a", "a", "b", "b"]) == (1.0, 1.0, 1.0)
    p, r, f = bcubed([1, 1, 1, 1], ["a", "a", "b", "b"])
    assert p == 0.5 and r == 1.0


def test_engine_recovers_synthetic_campaigns():
    recs = []
    texts = ["Your parcel is held at customs, pay the fee at <URL> today",
             "Your bank account is blocked, verify now at <URL> or call <PHONE_NUMBER>",
             "You won a prize of 50000, claim it by calling <PHONE_NUMBER> now",
             "Dear <NAMED_ENTITY>, your electricity will be cut tonight, pay at <URL>"]
    for k, t in enumerate(texts):
        recs.append(Record(id=str(k), text=t, lang="en", region="global", label="scam", group=k))
    msgs = list(stream(recs, n_messages=400, n_campaigns=4, seed=3))
    e = CampaignEngine()
    pred = [e.ingest(text, lang, t).message for text, lang, _, t in msgs]
    pred = [e.find(i) for i in pred]
    p, r, f = bcubed(pred, [c for _, _, c, _ in msgs])
    assert p > 0.99 and r > 0.95
