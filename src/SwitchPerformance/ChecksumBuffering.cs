using System.Security.Cryptography;
using Celeste.Mod;
using Mono.Cecil;
using Mono.Cecil.Cil;
using MonoMod.Cil;
using MonoMod.RuntimeDetour;

namespace SwitchPerformance;

public sealed class PerformanceSettings : EverestModuleSettings {
    public bool Diagnostics { get; set; }
    public bool DetailedEntities { get; set; } = true;
    public bool BufferChecksums { get; set; } = true;
}

public sealed partial class PerformanceModule {
    public override Type SettingsType => typeof(PerformanceSettings);
    private PerformanceSettings Settings => (PerformanceSettings)_Settings;
    [ThreadStatic] private static int checksumDepth;
    private ILHook? checksumBufferHook;

    private void InstallChecksumBuffering() {
        try {
            var method = typeof(HashAlgorithm).GetMethod(nameof(HashAlgorithm.ComputeHash), new[] { typeof(Stream) })!;
            checksumBufferHook = new ILHook(method, il => {
                var cursor = new ILCursor(il);
                bool Match(Instruction i) => i.MatchLdcI4(4096) &&
                    i.Next?.Operand is MethodReference target && target.Name == "Rent" &&
                    target.DeclaringType.FullName.StartsWith("System.Buffers.ArrayPool`1<");
                if (il.Body.Instructions.Count(Match) != 1)
                    throw new InvalidOperationException("Expected one 4096-byte ArrayPool.Rent; leaving hashing unchanged");
                cursor.GotoNext(MoveType.After, Match);
                cursor.Emit(OpCodes.Ldarg_0);
                cursor.Emit(OpCodes.Ldarg_1);
                cursor.EmitDelegate<Func<int, HashAlgorithm, Stream, int>>((original, hasher, stream) => {
                    if (checksumDepth <= 0 || hasher is not XXHash64 || stream.GetType() != typeof(FileStream)) return original;
                    return Settings.BufferChecksums ? 128 * 1024 : original;
                });
            });
            Emit(new { kind = "hook", label = "scoped checksum read buffer", success = true,
                enabled = Settings.BufferChecksums });
            Logger.Log("SwitchPerformance", "Scoped checksum buffer hook installed; BufferChecksums=" + Settings.BufferChecksums);
        } catch (Exception e) {
            Emit(new { kind = "hook", label = "scoped checksum read buffer", success = false, error = e.ToString() });
            Logger.Log("SwitchPerformance", "Checksum buffer hook unavailable; original hashing retained: " + e);
        }
    }
}
