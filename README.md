[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

# THE WORLD IN ONE DAY — Friday 20 November 2026

Entry for the make.fun bounty **"Sum up 20 November's world news in one image"**
($250, closes Sun 22 Nov 2026 07:00 WIB).
Bounty page: https://make.fun/bounty/news-image-20261120

## The image

A one-page broadsheet of the world's news of Friday 20 November 2026:
navy masthead, giant date headline "FRIDAY 20 NOVEMBER 2026" with a red
NOV 20 box, 3 hero scene illustrations (Anthropic's Nasdaq debut, Cyclone
Akvan bearing down on Odisha, the ICJ genocide ruling on Myanmar), 10 more
numbered story cards, a "THE DAY IN NUMBERS" strip, a dotted world map
"WHERE IT HAPPENED" with 13 numbered pins, a 27-item numbered index, a red
"DATE CHECK" footer, and a sources line. **40 stories in total.**

Lead stories: Anthropic's record $81.3bn IPO debut ($83 priced, $111.50
open, $97.17 close); the Dow's 1,101-point slide; the ICJ's first-ever
finding that a state committed genocide (Myanmar, 9–6); Cyclone Akvan's
noon landfall near Gopalpur with 100,000+ evacuated; the Trump–Xi–Putin
"peace declaration" from Shenzhen; GTA VI's launch-day records.

## How it is built

`main.py` is written from scratch (pure Python standard library only — no
PIL, no network). Text uses a hand-built vector stroke font rendered at
2048×2048 and box-downscaled to 1024×1024 (Lanczos-style crispness via
2x supersampling). All illustrations are drawn from shapes; no photos.

Run it with:

```
python3 main.py            # writes $MAKEFUN_OUTPUT_DIR/entry.png
                           # (default /output/entry.png)
```

## Output

- File: `output.png` (copy of the program's `entry.png`)
- Size: **1024 × 1024 px, 115,592 bytes** (limit: 1 MiB)
- SHA-256: `dd48dbd8c553da173d9b16a78862ad39e928389f8305cbab67e003c7397733ec`
- Runtime: ~3.7 s per run (limit: 2 min)

## Determinism

Two runs from different output directories produce byte-identical output
(same SHA-256, verified 20 Nov 2026, runs at ~01:58 WIB). No randomness,
no clock, no network, fixed zlib level.

## Top 3 sources

1. **Reuters** (via WSJ/Investopedia/Reuters wires) — Anthropic debut
   ($83 / $111.50 / $97.17, $81.3bn), Dow −1,101.11 to 49,097.06,
   BOJ December-hike Reuters poll (86% expect +25bp to 1.50%).
2. **ICJ / UN / Le Monde** — Myanmar genocide ruling, 19 Nov: 9–6 vote,
   first state found guilty of genocide, ~10,000 killed, 700,000 fled,
   reparations ordered.
3. **India Meteorological Department / Indian press (PTI, Deccan Herald)**
   — Cyclone Akvan: landfall ~noon IST 20 Nov near Gopalpur, winds
   90–100 km/h gusting 110, 100,000+ evacuated, 69 trains cancelled.

Full story-by-story verification notes: see `BUILD-NOTES.md`.

## Status

Local build only. **Not submitted, no GitHub repo, no wallet linked, no
transcript bundle.** Built early on 20 Nov (01:35–02:00 WIB) from news
reported up to that hour; a refresh with later 20 Nov news is possible
before the Sun 22 Nov 07:00 WIB deadline.
