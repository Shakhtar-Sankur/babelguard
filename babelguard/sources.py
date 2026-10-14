"""Every open dataset Babelguard builds on: where it is, its licence, whether its text may be
redistributed, and the checksum of the exact file used. `python -m babelguard.sources fetch`
downloads them into data/private/ (git-ignored) and verifies each checksum."""
import os
import sys
import urllib.request

from .dataset import sha256

HF = "https://huggingface.co/datasets"
SOURCES = {
    "imc25": {
        "files": {"imc25.csv": ("https://raw.githubusercontent.com/reportsmishing/Smishing-Dataset-IMC25/main/"
                                "dataset/final_dataset_output.csv",
                                "1bbd1e9e82c3ea023112207b80da268a5c4a07d2353c2b0898360ab037fa9a64")},
        "license": "CC-BY-4.0", "redistribute": True,
        "citation": "Agarwal, Papasavva, Suarez-Tangil, Vasek. Fishing for Smishing. ACM IMC 2025. "
                    "doi:10.1145/3730567.3764431",
        "regions": "49 languages; mostly Europe and the Americas",
    },
    "bengali_smishing": {
        "files": {f"bengali/{s}.parquet": (f"{HF}/shariul-islam/bengali-sms-smishing-dataset/resolve/main/"
                                           f"data/{s}-00000-of-00001.parquet", h)
                  for s, h in [("train", "9fb92ea7e185297f4dd66442a7ed5f11ffc82d501c1ca2ea38385f430b9fe18e"),
                               ("validation", "a6a652087bbc328618cc39720a3ec66be53e106d9184dcf83791bc4da705a1fc"),
                               ("test", "2719d61aaf82b4b38e256e7e0d5ecee4a19588a7f522b863c713a435d0dffa31")]},
        "license": "MIT", "redistribute": True,
        "citation": "Bengali SMS Smishing Dataset (SmishDetect-LLM), huggingface.co/datasets/"
                    "shariul-islam/bengali-sms-smishing-dataset",
        "regions": "South Asia: Bengali script, Banglish (Latin script), code-mixed, English",
    },
    "moz_smishing": {
        "files": {"moz/test.csv": (f"{HF}/MOZNLP/MOZ-Smishing/resolve/main/test.csv",
                                   "814a11d9b05741c4b47eb0d0784b1fd12a2a076f83a714a9908bdda594986ab8")},
        "license": "creativeml-openrail-m", "redistribute": False,     # use-restricted; raw text has names
        "citation": "Ali et al. MOZ-Smishing: A Benchmark Dataset for Detecting Mobile Money Frauds. "
                    "AfricaNLP 2025. doi:10.18653/v1/2025.africanlp-1.23",
        "regions": "Africa: Mozambican Portuguese, mobile money",
    },
    "singlish_sms": {
        "files": {"singlish/Translations.xlsx": ("https://zenodo.org/records/22657729/files/Translations.xlsx?download=1",
                                                 "c7b3588777b1b255fce0814c92704b36d035229b6899b3bd2b83c5e59f33fbd9")},
        "license": "CC-BY-4.0", "redistribute": True,
        "citation": "Ng and Chan. A Translated Singlish SMS Dataset. Data 11(9):235, 2026. "
                    "doi:10.5281/zenodo.22657729",
        "regions": "Southeast Asia: Singlish everyday messages (hard negatives)",
    },
}


def fetch(root="data/private", names=None):
    for name, src in SOURCES.items():
        if names and name not in names:
            continue
        for rel, (url, digest) in src["files"].items():
            path = os.path.join(root, rel)
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                urllib.request.urlretrieve(url, path)
            got = sha256(path)
            status = "ok" if got == digest else f"CHECKSUM MISMATCH ({got})"
            print(f"{name:18s} {rel:32s} {status}")


if __name__ == "__main__" and sys.argv[1:2] == ["fetch"]:
    fetch(names=sys.argv[2:] or None)
