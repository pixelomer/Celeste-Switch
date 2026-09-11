using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using Mono.Cecil;

// Calls source-built Everest NETCoreifier on a separate output. It never invokes
// the inspected game's entry point or replaces its native audio libraries.
internal static class Program
{
    private static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

    private static object Metadata(ModuleDefinition module) => new {
        name = module.Assembly.Name.FullName,
        flags = (int)module.Attributes,
        framework = module.Assembly.CustomAttributes.FirstOrDefault(a => a.AttributeType.FullName == "System.Runtime.Versioning.TargetFrameworkAttribute")?.ConstructorArguments[0].Value,
        references = module.AssemblyReferences.Select(a => a.FullName).ToArray(),
    };

    public static int Main(string[] args)
    {
        if (args.Length != 2) { Console.Error.WriteLine("Usage: CelesteSwitch.Coreify INPUT OUTPUT (new file)"); return 2; }
        string input = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[1]);
        if (StringComparer.OrdinalIgnoreCase.Equals(input, output) || File.Exists(output))
            throw new IOException("Output must be a new file distinct from the input");
        string originalHash = Hash(input);
        object before;
        using (var module = ModuleDefinition.ReadModule(input)) before = Metadata(module);
        NETCoreifier.Coreifier.ConvertToNetCore(input, output);
        if (Hash(input) != originalHash) throw new IOException("Source input changed during conversion");
        using var converted = ModuleDefinition.ReadModule(output);
        if ((converted.Attributes & (ModuleAttributes.Required32Bit | ModuleAttributes.Preferred32Bit)) != 0)
            throw new InvalidDataException("Coreifier retained 32-bit flags");
        var result = new { input_sha256 = originalHash, output_sha256 = Hash(output), before, after = Metadata(converted) };
        Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
        return 0;
    }
}
