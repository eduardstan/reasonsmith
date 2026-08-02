"""Pins the README's social card to the copy the website serves.

What this module is for:
  The first figure of the README, `docs/assets/og.png`, must stay byte-identical to the card the
  website serves as its OpenGraph and Twitter image (`assets/og.png` in the separate
  `eduardstan/reasonsmith-site` repository, generated from `brand/og.html` there). The site clone is
  not available in CI, so the SHA-256 below is the only side of the pair CI can check.

What a reader must not break:
  - The digest is a blunt instrument on purpose: any edit to `docs/assets/og.png` that does not
    first regenerate the authoritative card in the site repository and copy it here fails the build.
  - Updating the card means touching three places in one change: `brand/og.html` in the site
    repository, `docs/assets/og.png` here, and the digest below.
"""

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OG_IMAGE = REPO_ROOT / "docs" / "assets" / "og.png"

# SHA-256 of the card as served by eduardstan/reasonsmith-site at `assets/og.png`, generated from
# `brand/og.html` there. Changing this file means regenerating it there first and copying the
# result here — never editing the PNG directly.
AUTHORITATIVE_SHA256 = "74f2ce568cffd0f1d0a07674089b5c36cbd47c459b6165d577a6349097fe3edc"


def test_social_card_matches_the_site_served_copy():
    digest = hashlib.sha256(OG_IMAGE.read_bytes()).hexdigest()
    assert digest == AUTHORITATIVE_SHA256, (
        "docs/assets/og.png no longer matches the social card the website serves "
        "(expected sha256 "
        + AUTHORITATIVE_SHA256
        + ", got "
        + digest
        + "). The authoritative copy lives in eduardstan/reasonsmith-site at assets/og.png, "
        "generated from brand/og.html there: regenerate the card in that repository first, copy "
        "the result over docs/assets/og.png, and update the pinned digest in this test in the "
        "same change."
    )
