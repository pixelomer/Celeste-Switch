# Checksum read-size fixture

This source-only fixture compiles Everest's MIT-licensed XXHash64 helper with
framework classes. It does not load proprietary game assemblies or install the
live MonoMod IL hook. Preserve the source license when redistributing its code.

## Source input and build

Use .NET SDK 10.0.111. From this repository root, obtain a new source checkout:

```sh
git clone https://github.com/pixelomer/Everest.git third_party/checksum-everest
git -C third_party/checksum-everest checkout --detach cc8aaba288009879dc12482ceb43b4f536281e6e
dotnet build tests/performance-checksum/ChecksumFixture.csproj -c Release \
  -p:EverestSource="$(pwd)/third_party/checksum-everest" \
  --artifacts-path artifacts/checksum-fixture-build \
  --output artifacts/checksum-fixture
```

The project includes Celeste.Mod.mm/Mod/Helpers/XXHash.cs directly; recursive
submodules and game preparation are not required. Keep generated outputs outside
Git and preserve previous outputs before rebuilding.

## Input contract and separate execution

The sole argument is a JSON object mapping decimal byte lengths to uppercase
big-endian standard XXH64 hex, with seed zero. Input byte i is
(i*73 + i/251) & 255. The committed
[expected.json](expected.json) provides thirteen standard XXH64 vectors for
that byte rule, including stripe and buffer boundaries. They are deterministic
fixture inputs, not captured game/build identities. Execute separately:

```sh
dotnet artifacts/checksum-fixture/ChecksumFixture.dll tests/performance-checksum/expected.json
```

Thirteen lengths times thirteen checks give 169 assertions when every check
completes. The short-input oracle entries remain reference data even though
their direct comparison is intentionally skipped.

For each input, the fixture compares the baseline ComputeHash(Stream) digest
with the reference for lengths at least 32. It then compares twelve alternate
combinations against that baseline: four buffers (4096, 16384, 131072, 262144)
and three maximum reads (unlimited, 32, 4096). Exceptions signal disagreement;
completion prints a JSON assertion count. Those are prospective checks, not a
recorded pass.

The original helper always merges the accumulators, including inputs shorter
than one 32-byte stripe. For those inputs, retain its existing result instead
of substituting standard xxHash; the oracle comparison is intentionally skipped.
This fixture covers aligned read boundaries and does not prove arbitrary
unaligned short reads, live IL attachment, actual file stability, throughput
or mod compatibility. The optional mod benchmark separately exercises a full
archive through existing checksum hooks. Do not change the algorithm as part
of read-buffer tuning.
