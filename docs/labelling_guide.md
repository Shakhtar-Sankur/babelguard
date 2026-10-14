# Labelling guide (v0)

Each annotator should be a native speaker of the message's language. Read the message as someone
who received it would.

## 1. Label (choose one)

| Label | When |
|---|---|
| `scam` | It tries to get money, credentials, codes or personal data by deception, or to make the reader call, click, install or pay on a false pretext |
| `spam` | Unwanted marketing that is honest about what it is |
| `legit` | A genuine message from who it claims to be (OTPs, real bank alerts, real delivery notices, real government messages) |
| `unsure` | You cannot tell from the text. Say why in the notes |

If a message could be genuine, ask: *does it ask for something a genuine sender never asks for in
a text?* Examples are a PIN or OTP, payment to a personal UPI ID or wallet, installing an app from
a link, or calling an ordinary mobile number for "bank support".

## 2. Scam type

Choose one, by **pretext** (what it pretends to be), not by country. The full list is in
`babelguard/taxonomy.py`: `bank_payment`, `government`, `delivery`, `telecom_utility`,
`family_emergency`, `prize_lottery`, `job_task`, `investment_crypto`, `loan_credit`,
`romance_social`, `account_security`, `extortion`.

## 3. Lures (choose all that apply; Stajano and Wilson)

`time/urgency`, `authority`, `distraction`, `need and greed`, `kindness`, `herd`, `dishonesty`.

## 4. Disguises (tick any you see)

- Words written in another script, or the language typed in Latin letters (Hinglish, Greeklish …)
- Look-alike letters (Cyrillic а for Latin a, 0 for O)
- Odd spacing or hidden characters inside brand names or links
- Deliberate misspellings of brand names

## 5. Privacy (always)

Set `privacy_flag` if the message still contains a real person's name, a victim's own number or
account details, an address, or anything else that identifies a person. A flagged record is fixed
or removed before release, and is never published as it is.
