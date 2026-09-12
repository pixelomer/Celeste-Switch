# FMOD 1.10.14 Horizon integration

The shared Android/Bionic/JNI adapters serve both the synchronous native
fixture and managed hosts. Loader source is derived from the pinned public
MIT hl2-nx implementation with its notices intact. Obtain its source and
the exact user-supplied Android/Linux SDK archives through the
[native build recipe](../../tests/fmod-11014/README.md). Licensed SDK
headers/libraries, banks and generated outputs must remain outside Git.
FMOD 1.10.20 and FMOD 2 are not substitutes.

runtime.c resolves ordinary fmod/fmodstudio P/Invokes. System creation calls
the FMOD implementation, then configures Horizon output before initialization.
Other exports resolve to the loaded libraries, preserving the game's embedded
bindings and ordinary bank/event APIs. Missing exports are reported; unsupported
Android imports terminate by name. Network/live-update support is not provided.

output.c implements output API 3 using FMOD's mixer thread and four 512-frame
Horizon audout buffers. It requests stereo 48 kHz float samples, checks that
they are finite, clamps/converts to signed 16-bit PCM and submits them to audout.
Each pending buffer remains owned until release. A 200 ms wait timeout returns
to FMOD so its worker can stop/join without releasing the pending buffer early.
Partial initialization is cleaned up. Only one independent system can own
the device; a second fails explicitly. Releasing the system permits subsequent
initialization. Counters expose submitted, nonzero and released blocks,
timeouts and errors; they are diagnostics, not captured measurements.

Compile native code with the soft libnx TLS ABI. Adapter-created threads give
loaded Android code its Bionic TLS. FMOD_ADAPTER_MIN_STACK defaults to 256 KiB
for the standalone native fixture; the CoreCLR integration builder sets
1572864 bytes for managed callback threads. This is a bounded adapter, not
general Android thread or Java VM support.

Native libraries and mappings remain alive until process exit. Hosts must
use libnx's application process-exit policy instead of returning mapped-away
heap pages to hbloader. Dynamic unloading and arbitrary native mod libraries
are not implemented.

The [managed integration fixture](../../tests/fmod-managed/README.md)
exercises FNA rendering and asynchronous FMOD callbacks through the user's
converted game assembly without invoking its entry point. The synchronous
native fixture and managed fixture cover different contracts; neither alone
establishes full game, mod, docking or extended audio-lifecycle compatibility.
