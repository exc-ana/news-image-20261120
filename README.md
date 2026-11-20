[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

# The World Today — Friday 20 November 2026

A one-page broadsheet (1024×1024) summing up the world news of
Friday 20 November 2026: **40 stories**, drawn entirely in code.

## The image (v2)

- **Lead heroes:** Anthropic's market debut — priced $83, opened
  $111.50, high $115.10, closed $97.17 (+17%), $81.3bn raised, the
  biggest IPO on record — and Cyclone Akvan's confirmed landfall
  near Gopalpur at 07:30 IST (winds 70–80 km/h, gusts to 90;
  300,000 evacuated).
- **Three hero scenes:** the Anthropic IPO price chart, the Akvan
  cyclone spiral over the Bay of Bengal, and the burning tanker
  east of the Strait of Hormuz. Smaller scenes: COP31 globe,
  Nvidia chip, gold bars.
- **Also inside:** ICJ finds Myanmar guilty of genocide (9–6),
  Trump–Xi–Putin peace declaration in Shenzhen, Kerch bridge hit a
  third time, Dow −1,101, GTA VI's record launch, the Pete Rose
  pardon, a BOJ hike expected in December — plus a dotted world map
  with 13 numbered pins, a THE DAY IN NUMBERS strip, a UTC
  timeline, a numbered index of 27 more stories, and a DATE CHECK
  footer (Shenzhen met 19 Nov; Anthropic was priced 18 Nov — only
  the 20 Nov news counts).
- **Craft:** rendered at 2x (2048×2048) and box-downsampled to
  1024×1024; hand-built vector stroke font; no photos, no external
  files.

## The program

`main.py` is Python 3, standard library only. It draws the whole
page from scratch (canvas, font, scenes, PNG encoder) and writes
`$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output/entry.png`).
No network, no clock, no randomness.

Run it:

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Verification

- `output.png`: 1024×1024, **133,008 bytes**
- SHA-256:
  `effbb10fc8e2615468ef63a3f0679e3ffa8d09a762ae6e9c2657db3fe0fd4543`
- Determinism: two runs in separate output directories produced
  byte-identical files (`cmp` clean).
- Runtime: ~4.3 s per run (limit 60 s).

## Status

**Not submitted yet.** This is the v2 rewrite, written from scratch
in-session for the 20 November 2026 news-image bounty
($250, closes Sunday 22 November 2026, 07:00 WIB).

## License

MIT — see `LICENSE`.
