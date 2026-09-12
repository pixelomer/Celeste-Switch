using System.Security.Cryptography;
using System.Text.Json;
using Celeste.Mod;

var expected = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(args[0]))!;
int assertions = 0;
foreach (var pair in expected) {
    int length = int.Parse(pair.Key);
    byte[] data = Enumerable.Range(0, length).Select(i => (byte)((i * 73 + i / 251) & 255)).ToArray();
    string baseline;
    using (var original = XXHash64.Create()) {
        baseline = Convert.ToHexString(original.ComputeHash(new MemoryStream(data)));
        // Everest's existing implementation merges all accumulators even for
        // inputs shorter than one stripe. Preserve that nonstandard result.
        if (length >= 32 && baseline != pair.Value) throw new Exception("Original hash differs from reference at " + length);
        assertions++;
    }
    foreach (int size in new[] { 4096, 16384, 131072, 262144 }) {
        foreach (int maximumRead in new[] { int.MaxValue, 32, 4096 }) {
            using var input = new ShortReads(data, maximumRead);
            using var hash = XXHash64.Create();
            byte[] buffer = new byte[size];
            int count;
            // Same HashCore/HashFinal sequence as ComputeHash(Stream), with
            // an alternate read-buffer size. This fixture checks chunk-boundary
            // results, not the live IL attachment.
            while ((count = input.Read(buffer, 0, buffer.Length)) > 0)
                hash.TransformBlock(buffer, 0, count, null, 0);
            hash.TransformFinalBlock(Array.Empty<byte>(), 0, 0);
            if (Convert.ToHexString(hash.Hash!) != baseline)
                throw new Exception($"Hash mismatch length={length} buffer={size} readLimit={maximumRead}");
            assertions++;
        }
    }
}
Console.WriteLine(JsonSerializer.Serialize(new { assertions, success = true,
    scope = "upstream XXHash64 across aligned read boundaries; live IL hook tested separately" }));

sealed class ShortReads(byte[] data, int maximumRead) : MemoryStream(data) {
    public override int Read(byte[] buffer, int offset, int count) => base.Read(buffer, offset, Math.Min(count, maximumRead));
}
