[![make.fun](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/exc-ana/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120)

# The World Today — Friday 20 November 2026

A one-page newspaper broadsheet summing up the world's news of Friday
20 November 2026, drawn entirely in code. This is my entry for the
[make.fun news-image-20261120 bounty](https://make.fun/bounty/news-image-20261120)
($250, closes Sunday 22 November 2026, 07:00 WIB).

## The image

40 stories on one page: a navy masthead, a giant date headline, a red
NOV 20 date box, and numbered cards with hand-drawn scenes.

- **Lead stories:** Anthropic slides on day two of trading (record
  $81.3bn debut, then −6% pre-market to $91) and Russia's overnight
  missile-and-drone strikes on Kyiv's bridges.
- **Also covered:** the ICJ's 9–6 genocide verdict against Myanmar,
  COP31 ending with no deal, Cyclone Akvan fizzling on landfall, the
  Shenzhen three-way peace declaration, two more tankers hit in the
  Strait of Hormuz, the Dow sinking 2.19%, GTA VI's $2.36bn launch day,
  gold's worst week since March, Bitcoin below $62K, and Nicholls'
  175* lifting New Zealand.
- **Plus:** a dotted world map with numbered pins, a "THE DAY IN
  NUMBERS" strip, a timeline, a 28-item index, and a red DATE CHECK
  footer. Every story above happened or was first reported on Friday
  20 November 2026.

## How it is made

`main.py` (Python 3.13, standard library only) draws the whole page
from scratch: a 2x supersampled RGB canvas, a hand-made vector stroke
font, eight drawn scenes (IPO chart, Kyiv bridges at night, the Peace
Palace, a COP31 globe, a cyclone spiral, the Shenzhen summit, burning
tankers, a cricket pitch), a dotted world map, then a box-average
downsample to 1024×1024 and a hand-rolled PNG encoder. No photos, no
network, no randomness — two runs write byte-identical output.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
```

## Verification

- `output.png`: 1024×1024 RGB PNG, **104,684 bytes** (limit 1 MiB)
- SHA-256: `80c34bb67f3f49dfa30e9f8b94c3d388418a87e3fb44ce41eb535821f8846b17`
- Determinism: two independent runs to different output directories
  produced byte-identical files (`cmp` clean)
- Runtime: ~1.6 s per run (limit 60 s)

## Sources

Figures were checked against Reuters, AP, CNN, WSJ, the Financial
Times, Cricbuzz and exchange/market data on 20 November 2026 up to
~17:30 WIB. "Reported 20 Nov" means first reported or published on
20 November in world press, even where the event itself was 19 November
US time. The US regular session had not opened at build time, so only
pre-market and futures prices are used.

## License

MIT — see [LICENSE](LICENSE).
