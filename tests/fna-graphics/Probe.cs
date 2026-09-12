// Original test content. No game assets or decompiled game code.
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;

static class Probe
{
    internal static int Checks;
    [DllImport("__Internal")] internal static extern uint ProbeGlError();
    [DllImport("__Internal")] internal static extern uint ProbeConfigureLifecycle();
    [DllImport("__Internal")] internal static extern uint ProbeResumeCount();
    internal static void Check(bool value, string name)
    {
        if (!value) throw new Exception("FAIL " + name);
        ++Checks; Console.WriteLine("PASS " + name);
    }
    public static int Main()
    {
        try
        {
            Console.WriteLine("BEGIN original FNA graphics probe " + typeof(Game).Assembly.FullName);
            Check(ProbeConfigureLifecycle()==0,"Horizon suspend and resume notifications configured");
            // Select the OpenGL renderer explicitly, not a headless backend.
            Environment.SetEnvironmentVariable("FNA3D_FORCE_DRIVER", "OpenGL");
            using (var game = new GraphicsProbe()) game.Run();
            Console.WriteLine("END PASS checks=" + Checks);
            return 100;
        }
        catch (Exception e) { Console.WriteLine(e); return 101; }
    }
}
sealed class GraphicsProbe : Game
{
    readonly GraphicsDeviceManager manager;
    SpriteBatch batch;
    Texture2D white, pattern;
    RenderTarget2D target;
    RasterizerState scissor;
    BasicEffect effect;
    readonly Stopwatch clock = new Stopwatch();
    int frames;
    int focusLost, focusResumed;
    uint initialResumes;
    bool connected, button;
    public GraphicsProbe()
    {
        manager = new GraphicsDeviceManager(this) { PreferredBackBufferWidth=1280, PreferredBackBufferHeight=720, SynchronizeWithVerticalRetrace=true };
        IsFixedTimeStep = false;
        Deactivated += (_, _) => { ++focusLost; Console.WriteLine("FOCUS inactive seconds="+clock.Elapsed.TotalSeconds); };
        Activated += (_, _) => { if (focusLost>0) ++focusResumed; Console.WriteLine("FOCUS active seconds="+clock.Elapsed.TotalSeconds); };
    }
    protected override void LoadContent()
    {
        Console.WriteLine("DEVICE " + GraphicsDevice.Adapter.Description + " profile=" + GraphicsDevice.GraphicsProfile);
        Probe.Check(SDL2.SDL.SDL_GetCurrentVideoDriver()=="Switch", "physical Switch SDL video driver");
        batch = new SpriteBatch(GraphicsDevice);
        white = new Texture2D(GraphicsDevice, 1, 1);
        white.SetData(new[] { Color.White });
        pattern = new Texture2D(GraphicsDevice, 2, 2);
        Color[] colors = { Color.Red, Color.Green, Color.Blue, Color.White };
        pattern.SetData(colors);
        Color[] copy = new Color[4]; pattern.GetData(copy);
        for (int i=0;i<4;i++) Probe.Check(copy[i] == colors[i], "texture upload/readback " + i);
        target = new RenderTarget2D(GraphicsDevice, 64, 64, false, SurfaceFormat.Color, DepthFormat.None, 0, RenderTargetUsage.PreserveContents);
        scissor = new RasterizerState { ScissorTestEnable=true, CullMode=CullMode.None };
        effect = new BasicEffect(GraphicsDevice) { VertexColorEnabled=true, World=Matrix.Identity, View=Matrix.Identity, Projection=Matrix.Identity };
        CheckRendering();
        initialResumes = Probe.ProbeResumeCount();
        Console.WriteLine("INITIAL Horizon resume count="+initialResumes);
        clock.Start();
    }
    void Expect(Color[] pixels, int x, int y, Color expected, string name, int tolerance=0)
    {
        Color actual = pixels[y*64+x];
        Probe.Check(Math.Abs(actual.R-expected.R)<=tolerance && Math.Abs(actual.G-expected.G)<=tolerance && Math.Abs(actual.B-expected.B)<=tolerance && Math.Abs(actual.A-expected.A)<=tolerance,
            name + " actual=" + actual + " expected=" + expected);
    }
    void CheckRendering()
    {
        GraphicsDevice.SetRenderTarget(target);
        GraphicsDevice.Clear(Color.Black);
        batch.Begin(SpriteSortMode.Deferred, BlendState.Opaque, SamplerState.PointClamp, DepthStencilState.None, RasterizerState.CullNone);
        batch.Draw(pattern, new Rectangle(0,0,64,64), Color.White);
        batch.End();
        GraphicsDevice.SetRenderTarget(null);
        Color[] pixels = new Color[64*64]; target.GetData(pixels);
        Expect(pixels,8,8,Color.Red,"SpriteBatch top left");
        Expect(pixels,48,8,Color.Green,"SpriteBatch top right");
        Expect(pixels,8,48,Color.Blue,"SpriteBatch bottom left");
        Expect(pixels,48,48,Color.White,"SpriteBatch bottom right");
        GraphicsDevice.SetRenderTarget(target);
        GraphicsDevice.Clear(Color.Red);
        batch.Begin(SpriteSortMode.Deferred, BlendState.AlphaBlend, SamplerState.PointClamp, DepthStencilState.None, RasterizerState.CullNone);
        batch.Draw(white,new Rectangle(0,0,32,64),new Color(0,128,0,128));
        batch.End();
        GraphicsDevice.ScissorRectangle = new Rectangle(32,16,16,16);
        batch.Begin(SpriteSortMode.Deferred, BlendState.Opaque, SamplerState.PointClamp, DepthStencilState.None, scissor);
        batch.Draw(white,new Rectangle(0,0,64,64),Color.Cyan);
        batch.End();
        GraphicsDevice.SetRenderTarget(null); target.GetData(pixels);
        Expect(pixels,8,8,new Color(127,128,0,255),"premultiplied alpha",1);
        Expect(pixels,40,24,Color.Cyan,"scissor interior");
        Expect(pixels,56,24,Color.Red,"scissor exterior");
        GraphicsDevice.SetRenderTarget(target);
        GraphicsDevice.Clear(Color.Black);
        GraphicsDevice.RasterizerState=RasterizerState.CullNone;
        GraphicsDevice.BlendState=BlendState.Opaque;
        GraphicsDevice.DepthStencilState=DepthStencilState.None;
        var vertices = new[] {
            new VertexPositionColor(new Vector3(-1,-1,0),Color.Magenta),
            new VertexPositionColor(new Vector3(0,1,0),Color.Magenta),
            new VertexPositionColor(new Vector3(1,-1,0),Color.Magenta) };
        foreach (var pass in effect.CurrentTechnique.Passes) { pass.Apply(); GraphicsDevice.DrawUserPrimitives(PrimitiveType.TriangleList,vertices,0,1); }
        GraphicsDevice.SetRenderTarget(null); target.GetData(pixels);
        Expect(pixels,32,32,Color.Magenta,"BasicEffect vertex upload and shader");
        Expect(pixels,1,1,Color.Black,"triangle exterior");
        Probe.Check(Probe.ProbeGlError()==0,"OpenGL error state after readbacks");
        Console.WriteLine("RENDER CHECKS COMPLETE; displaying for 75 seconds; press south face button, HOME, then resume");
    }
    protected override void Update(GameTime time)
    {
        var state=GamePad.GetState(PlayerIndex.One);
        if (state.IsConnected && !connected) { connected=true; Console.WriteLine("INPUT controller connected"); }
        if (state.IsButtonDown(Buttons.A) && !button) { button=true; Console.WriteLine("INPUT A received"); }
        if (clock.Elapsed.TotalSeconds >= 75)
        {
            Probe.Check(frames>120,"continuous presentation frames="+frames);
            Probe.Check(connected,"controller discovery");
            Probe.Check(button,"logical A / south face button input");
            Console.WriteLine("INFO focus events lost="+focusLost+" resumed="+focusResumed);
            Probe.Check(Probe.ProbeResumeCount()>initialResumes,"Horizon resume notification count="+Probe.ProbeResumeCount());
            Probe.Check(Probe.ProbeGlError()==0,"OpenGL error state after presentation");
            Exit();
        }
        base.Update(time);
    }
    protected override void Draw(GameTime time)
    {
        GraphicsDevice.Clear(new Color(16,24,40));
        batch.Begin(SpriteSortMode.Deferred,BlendState.Opaque,SamplerState.PointClamp,DepthStencilState.None,RasterizerState.CullNone);
        batch.Draw(pattern,new Rectangle(80,100,480,480),Color.White);
        batch.Draw(target,new Rectangle(680,100,480,480),Color.White);
        batch.Draw(white,new Rectangle(80,620,1080,24),button ? Color.Lime : Color.Gold);
        batch.End();
        ++frames;
        if (frames%120==0) GC.Collect();
        base.Draw(time);
    }
    protected override void UnloadContent()
    {
        effect?.Dispose(); scissor?.Dispose(); target?.Dispose(); pattern?.Dispose(); white?.Dispose(); batch?.Dispose();
        base.UnloadContent();
    }
}
