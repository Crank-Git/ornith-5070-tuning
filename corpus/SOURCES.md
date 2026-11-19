# Corpus sources

- `prose.txt`: WikiText-2 raw test split (`wiki.test.raw`), from the ggml-org/ci dataset mirror. CC BY-SA 3.0.
- `code.txt`: 12 KB blocks alternating between
  - Go 1.23.0 stdlib (BSD-3): `net/http/server.go`, `encoding/json/decode.go`, `sort/sort.go`, `strings/strings.go`, `bufio/bufio.go`, `time/format.go`;
  - CPython 3.13.0 stdlib (PSF): `json/decoder.py`, `argparse.py`, `asyncio/tasks.py`, `pathlib/_local.py`, `textwrap.py`.
