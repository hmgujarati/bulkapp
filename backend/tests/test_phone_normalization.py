"""Mixed-country phone normalization (no forced +91).

Run: python tests/test_phone_normalization.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import normalize_phone_number  # noqa: E402

CASES = [
    # (raw, selected dial code, expected)
    ("9876543210", "91", "+919876543210"),        # local Indian
    ("09876543210", "91", "+919876543210"),       # local with trunk 0
    ("919876543210", "91", "+919876543210"),      # Indian with country code
    ("+919876543210", "91", "+919876543210"),
    ("971501234567", "91", "+971501234567"),      # UAE inside an India-selected list
    ("00971501234567", "91", "+971501234567"),    # 00 international prefix
    ("+971 50 123 4567", "91", "+971501234567"),
    ("15551234567", "91", "+15551234567"),        # US inside an India-selected list
    ("447911123456", "91", "+447911123456"),      # UK inside an India-selected list
    ("501234567", "971", "+971501234567"),        # local UAE
    ("13812345678", "86", "+8613812345678"),      # local Chinese 11-digit mobile
    ("", "91", ""),
    ("abcd", "91", ""),
]


def main():
    failures = []
    for raw, cc, expected in CASES:
        got = normalize_phone_number(raw, cc)
        if got != expected:
            failures.append(f"{raw!r} (+{cc}) -> {got!r}, expected {expected!r}")
        else:
            print(f"✓ {raw!r} (+{cc}) -> {got}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nALL PASSED")


if __name__ == "__main__":
    main()
