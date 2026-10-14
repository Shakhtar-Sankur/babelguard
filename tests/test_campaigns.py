"""One campaign across languages; legitimate domains never join campaigns."""
import numpy as np

from babelguard.campaigns import link

MSGS = [
    "Your SBI KYC expires today. Update at hxxps://sbi-kyc-update[.]com or call 98765 43210",  # en
    "आपका SBI KYC आज समाप्त। अपडेट करें: sbi-kyc-update.com या कॉल करें ९८७६५ ४३२१०",             # hi
    "ଆପଣଙ୍କ ପାର୍ସଲ ଅଟକି ଯାଇଛି। ଶୁଳ୍କ ପଠାନ୍ତୁ: refund.help@ybl",                                   # or
    "Your parcel is held at customs. Pay the fee to refund.help@ybl",                            # en
    "Official notice: visit www.sbi.co.in for KYC rules",                                        # legit
    "Reminder: visit www.sbi.co.in, never share your OTP",                                       # legit
]


def groups(cs):
    return sorted(sorted(c.members) for c in cs)


def test_indicators_link_across_languages_and_legit_domains_do_not():
    cs = link(MSGS)
    assert groups(cs) == [[0, 1], [2, 3], [4], [5]]
    reasons = {r for c in cs for _, _, r in c.links}
    assert "upi:refund.help@ybl" in reasons


def test_near_copies_link_by_text():
    a = "Congratulations! You won 25 lakh in the KBC lottery. Call our manager to claim."
    b = "Congratulations!! You won 25 lakh in KBC lottery. Call our manager now to claim."
    c = "Your electricity will be cut tonight. Pay the bill now."
    assert groups(link([a, b, c])) == [[0, 1], [2]]


def test_very_common_indicators_are_ignored():
    msgs = [f"msg {i} call 98765 43210" for i in range(10)] + ["other"]
    cs = link(msgs, max_df=0.2, text_threshold=1.01)
    assert max(len(c.members) for c in cs) == 1


def test_meaning_links_through_an_embedder():
    def embed(texts):                     # stand-in for a multilingual encoder
        v = np.array([[1.0, 0.0] if "lottery" in t or "लॉटरी" in t else [0.0, 1.0] for t in texts])
        return v / np.linalg.norm(v, axis=1, keepdims=True)
    msgs = ["You won the lottery, pay tax to claim", "आपने लॉटरी जीती, दावा करने के लिए टैक्स भरें", "power cut tonight"]
    cs = link(msgs, embed=embed)
    assert groups(cs) == [[0, 1], [2]]
    assert any(r == "meaning" for c in cs for _, _, r in c.links)
