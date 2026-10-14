"""Indicator extraction, checksums and redaction."""
import os

from babelguard.indicators import (Indicator, b58encode_check, bech32_encode, bech32_ok, extract,
                                   link_key, luhn_ok, redact, verhoeff_digit, verhoeff_ok)


def kinds(msg):
    return {(i.kind, i.value) for i in extract(msg)}


def test_defanged_and_disguised_links():
    assert ("domain", "sbi-kyc.com") in kinds("visit hxxps://sbi-kyc[.]com/login now")
    assert ("domain", "sbi-kyc.com") in kinds("visit sbi-kyc dot com")
    assert ("domain", "paytm-kyc.in") in kinds("pаytm-kyc.in")           # Cyrillic а
    assert ("domain", "refund.co") in kinds("re​fund.co")


def test_shorteners_and_messaging_links_keep_their_path():
    assert ("url", "bit.ly/abc123") in kinds("click https://bit.ly/abc123.")
    assert ("url", "t.me/refunddesk") in kinds("join t.me/refunddesk")


def test_file_names_are_not_domains():
    assert not {k for k in kinds("open invoice.pdf or setup.apk") if k[0] == "domain"}


def test_phones_in_any_digits_and_any_country():
    india = ("phone", "+919876543210")
    assert india in kinds("+91-98765-43210")
    assert india in kinds("0091 98765 43210")
    assert ("phone", "9876543210") in kinds("call 98765 43210")              # no country assumed
    assert india in {(i.kind, i.value) for i in extract("कॉल करें ९८७६५ ४३२१०", country="IN")}
    assert india in {(i.kind, i.value) for i in extract("ଫୋନ୍ କରନ୍ତୁ ୯୮୭୬୫୪୩୨୧୦", country="IN")}
    assert ("phone", "+447700900123") in kinds("ring +44 7700 900123")
    mz = {(i.kind, i.value) for i in extract("Neste Nr. M-Pesa:857296999", country="MZ")}
    assert ("phone", "+258857296999") in mz
    ke = {(i.kind, i.value) for i in extract("Tuma pesa 0712 345 678", country="KE")}
    assert ("phone", "+254712345678") in ke
    assert ("phone", "+639171234567") in kinds("GCash support +63 917 123 4567")


def test_same_number_with_and_without_country_code_links():
    a = extract("call +91 98765 43210")
    b = extract("call 98765 43210")
    assert {link_key(x) for x in a} == {link_key(x) for x in b}


def test_upi_is_not_email_and_email_is_not_upi():
    k = kinds("pay refund.help@ybl or mail help@refund-desk.com")
    assert ("upi", "refund.help@ybl") in k
    assert ("email", "help@refund-desk.com") in k
    assert ("upi", "help@refund-desk") not in k


def test_btc_checksums():
    genesis = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert ("btc", genesis) in kinds(f"send to {genesis}")
    broken = genesis[:-1] + "b"
    assert not any(k[0] == "btc" for k in kinds(f"send to {broken}"))
    seg = bech32_encode("bc", [0] + [ord(c) % 32 for c in "w508d6qejxtdg4c0yrygtnc2fpsr8t"])
    assert bech32_ok(seg) and ("btc", seg) in kinds(f"wallet {seg}")
    assert not bech32_ok(seg[:-1] + ("q" if seg[-1] != "q" else "p"))


def test_tron_and_eth():
    tron = b58encode_check(b"\x41" + os.urandom(20))
    assert tron.startswith("T") and ("tron", tron) in kinds(f"USDT TRC20: {tron}")
    eth = "0x" + "ab" * 20
    assert ("eth", eth) in kinds(f"ERC20 {eth.upper().replace('0X', '0x')}")


def test_cards_and_aadhaar_are_not_phones():
    assert not any(k[0] == "phone" for k in kinds("card 4111 1111 1111 1111"))
    base = "23456789012"
    aadhaar = base + verhoeff_digit(base)
    assert verhoeff_ok(aadhaar)
    assert not any(k[0] == "phone" for k in kinds(f"aadhaar {aadhaar}"))


def test_checksum_helpers():
    assert luhn_ok("4111111111111111") and not luhn_ok("4111111111111112")
    base = "98765432101"
    good = base + verhoeff_digit(base)
    assert verhoeff_ok(good)
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert not verhoeff_ok(bad)


def test_redaction_keeps_scammer_details_and_hides_victims():
    base = "23456789012"
    aadhaar = base + verhoeff_digit(base)
    msg = (f"OTP 482913 for card 4111-1111-1111-1111, Aadhaar {aadhaar}, PAN ABCDE1234F. "
           "Pay refund.help@ybl or call 98765 43210")
    r = redact(msg)
    for secret in ("482913", "4111", aadhaar, "ABCDE1234F"):
        assert secret not in r
    assert "refund.help@ybl" in r and "98765 43210" in r
    assert redact("ओटीपी ५५५१२३ है") == "ओटीपी [OTP] है"


def test_indicator_is_hashable_value():
    assert Indicator("upi", "a@ybl") == Indicator("upi", "a@ybl")
