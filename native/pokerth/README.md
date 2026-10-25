# PokerTH opponent core

Pinned upstream: [PokerTH v2.1.10](https://github.com/pokerth/pokerth/tree/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba).
The eleven files in `vendor/` are unmodified. `upstream.json` records their Git
blob IDs and SHA-256 checksums, verified against the upstream recursive tree.
Original copyright headers and `vendor/COPYING` are retained. PokerTH is licensed
under AGPL version 3 or later, including the additional permission in its source
headers. The WTR bridge is also AGPL-3.0-or-later. Preserve the license and provide
Corresponding Source, including this bridge and build script, when distributing
covered binaries or offering a modified covered program for remote interaction.

Build from the repository root with Python 3 and a C++20 compiler (Clang or GCC):

```sh
python3 scripts/build_pokerth.py
native/pokerth/build/pokerth-opponent --version
```

This is an offline build. No Qt, OpenSSL, downloads or research temporary files
are required. `CXX` can select a compiler. Generated binaries are ignored by Git.
The build verifies the vendored checksums and records compiler provenance in
`build/build.json`. The macOS compiler warns about intentional adjacent string
literals in the unmodified upstream preflop chart.

The wrapper accepts one bounded numeric request on stdin and returns three
integers: action enum, bet, raise increment. It validates cards, chip bounds,
player counts, streets, personality ranges and input length. Errors never echo
inputs. Python supplies a fresh seed from the acting seat's private policy RNG,
uses a two-second process timeout and validates the bounded result before mapping
it to the observed legal menu. Every invocation exits, including its Monte Carlo
RNG; there is no persistent native process or cross-table native memory.

The application replaces upstream `Tools::GetRand` with seeded standard C++
randomness and portable rejection sampling. Upstream decision/equity logic is
unchanged. This makes runs reproducible with matching versions, seeds and public
action sequences. It does not claim bit-identical play to the desktop application.
