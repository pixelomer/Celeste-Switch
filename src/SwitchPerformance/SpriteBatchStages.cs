using Microsoft.Xna.Framework.Graphics;

namespace SwitchPerformance;

public sealed partial class PerformanceModule {
    private void InstallSpriteBatchStages() {
        TimedVoid<SpriteBatch>("SpriteBatch.PrepRenderState", "PrepRenderState");
        var upload = NewMeter("SpriteBatch.UpdateVertexBuffer");
        Add(typeof(SpriteBatch).GetMethod("UpdateVertexBuffer", Methods),
            (Func<Func<SpriteBatch, int, int, int>, SpriteBatch, int, int, int>)((orig, self, start, count) => {
                long begin = upload.Start();
                try { return orig(self, start, count); } finally { upload.Stop(begin); }
            }), "SpriteBatch.UpdateVertexBuffer");
        var draw = NewMeter("SpriteBatch.DrawPrimitives");
        Add(typeof(SpriteBatch).GetMethod("DrawPrimitives", Methods),
            (Action<Action<SpriteBatch, Texture, int, int>, SpriteBatch, Texture, int, int>)((orig, self, texture, start, count) => {
                long begin = draw.Start();
                try { orig(self, texture, start, count); } finally { draw.Stop(begin); }
            }), "SpriteBatch.DrawPrimitives");
    }
}
