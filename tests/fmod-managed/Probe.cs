// Original integration control; calls the actual FMOD bindings in the user's
// coreified Celeste assembly without invoking the game's entry point.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
static class Probe {
    [DllImport("CelestePlatform")] internal static extern ulong CelesteAudioMixed();
    [DllImport("CelestePlatform")] internal static extern ulong CelesteAudioNonzero();
    [DllImport("CelestePlatform")] internal static extern ulong CelesteAudioReleased();
    [DllImport("CelestePlatform")] internal static extern int CelesteAudioError();
    static int checks;
    internal static void Check(bool test,string message){if(!test)throw new Exception("FAIL "+message);checks++;Console.WriteLine("PASS "+message);}
    internal static void Fmod(FMOD.RESULT result){if(result!=FMOD.RESULT.OK)throw new Exception("FMOD "+result);}
    public static int Main(){try{
        Console.WriteLine("BEGIN FNA and asynchronous FMOD / actual Celeste bindings "+typeof(FMOD.Studio.System).Assembly.FullName);
        Environment.SetEnvironmentVariable("FNA3D_FORCE_DRIVER","OpenGL");
        using(var game=new AudioGame())game.Run();
        Check(CelesteAudioError()==0,"native output error state");
        ulong stopped=CelesteAudioMixed();Thread.Sleep(150);
        Check(CelesteAudioMixed()==stopped,"mixer stopped after System.release");
        // Reinitialize through ordinary bindings to verify output ownership cleanup.
        FMOD.Studio.System again;Fmod(FMOD.Studio.System.create(out again));
        Fmod(again.initialize(128,FMOD.Studio.INITFLAGS.NORMAL,FMOD.INITFLAGS.NORMAL,IntPtr.Zero));
        Thread.Sleep(100);Fmod(again.update());Fmod(again.release());
        Check(CelesteAudioMixed()>stopped,"output reinitialization");
        Check(CelesteAudioError()==0,"native output error state after reinitialization");
        Console.WriteLine("END PASS checks="+checks);return 100;
    }catch(Exception e){Console.WriteLine(e);return 101;}}
}
sealed class AudioGame:Game {
    readonly GraphicsDeviceManager graphics;
    readonly Stopwatch clock=new Stopwatch();
    FMOD.Studio.System studio;
    FMOD.Studio.EventDescription description;
    readonly List<FMOD.Studio.EventInstance> events=new List<FMOD.Studio.EventInstance>();
    readonly FMOD.Studio.EVENT_CALLBACK callback;
    SpriteBatch batch;Texture2D texture;
    int frames,plays,callbacks,workerCallbacks,callbackFailures;
    readonly int mainThread=Environment.CurrentManagedThreadId;
    double nextPlay;bool finished;
    long maxUpdateTicks;
    public AudioGame(){graphics=new GraphicsDeviceManager(this){PreferredBackBufferWidth=1280,PreferredBackBufferHeight=720,SynchronizeWithVerticalRetrace=true};IsFixedTimeStep=false;callback=OnEvent;}
    FMOD.RESULT OnEvent(FMOD.Studio.EVENT_CALLBACK_TYPE type,IntPtr instance,IntPtr parameters){
        try{int count=Interlocked.Increment(ref callbacks);if(Environment.CurrentManagedThreadId!=mainThread)Interlocked.Increment(ref workerCallbacks);
            if(count%13==0)GC.Collect(2,GCCollectionMode.Forced,true,true);
            return FMOD.RESULT.OK;
        }catch{Interlocked.Increment(ref callbackFailures);return FMOD.RESULT.ERR_INTERNAL;}
    }
    protected override void LoadContent(){
        batch=new SpriteBatch(GraphicsDevice);texture=new Texture2D(GraphicsDevice,1,1);texture.SetData(new[]{Color.White});
        Probe.Fmod(FMOD.Studio.System.create(out studio));FMOD.System low;
        Probe.Fmod(studio.getLowLevelSystem(out low));uint version;Probe.Fmod(low.getVersion(out version));Probe.Check(version==0x11014,"exact FMOD runtime version");
        Probe.Fmod(studio.initialize(1024,FMOD.Studio.INITFLAGS.NORMAL,FMOD.INITFLAGS.NORMAL,IntPtr.Zero));
        foreach(string name in new[]{"Master Bank.strings.bank","Master Bank.bank","ui.bank"}){FMOD.Studio.Bank bank;Probe.Fmod(studio.loadBankFile("/switch/celeste-fmod-11014/banks/"+name,FMOD.Studio.LOAD_BANK_FLAGS.NORMAL,out bank));}
        Probe.Fmod(studio.getEvent("event:/ui/main/button_select",out description));
        Probe.Fmod(description.loadSampleData());Probe.Fmod(studio.flushSampleLoading());
        Console.WriteLine("READY asynchronous audio and graphics for 20 seconds");clock.Start();
    }
    protected override void Update(GameTime time){
        long start=Stopwatch.GetTimestamp();Probe.Fmod(studio.update());long ticks=Stopwatch.GetTimestamp()-start;if(ticks>maxUpdateTicks)maxUpdateTicks=ticks;
        if(clock.Elapsed.TotalSeconds>=nextPlay && plays<60){
            FMOD.Studio.EventInstance instance;Probe.Fmod(description.createInstance(out instance));
            Probe.Fmod(instance.setCallback(callback,FMOD.Studio.EVENT_CALLBACK_TYPE.ALL));Probe.Fmod(instance.start());events.Add(instance);plays++;nextPlay+=0.25;
        }
        if(frames%90==0)GC.Collect(2,GCCollectionMode.Forced,true,true);
        if(clock.Elapsed.TotalSeconds>=20 && !finished){finished=true;
            Probe.Check(frames>600,"concurrent FNA presentation frames="+frames);
            Probe.Check(Probe.CelesteAudioMixed()>1000,"asynchronous mixer blocks="+Probe.CelesteAudioMixed());
            Probe.Check(Probe.CelesteAudioNonzero()>20,"decoded nonzero audio blocks="+Probe.CelesteAudioNonzero());
            Probe.Check(Probe.CelesteAudioReleased()>500,"completed Horizon audio buffers="+Probe.CelesteAudioReleased());
            Probe.Check(callbacks>60 && workerCallbacks>0,"managed callbacks total="+callbacks+" worker="+workerCallbacks);
            Probe.Check(callbackFailures==0,"managed callback/GC failures");
            Console.WriteLine("FMOD update max_ms="+(maxUpdateTicks*1000.0/Stopwatch.Frequency));
            foreach(var instance in events){Probe.Fmod(instance.stop(FMOD.Studio.STOP_MODE.IMMEDIATE));Probe.Fmod(instance.release());}
            Probe.Fmod(studio.flushCommands());Probe.Fmod(studio.release());studio=null;
            GC.KeepAlive(callback);Exit();
        }
        base.Update(time);
    }
    protected override void Draw(GameTime time){GraphicsDevice.Clear(new Color(16,25,40));batch.Begin();batch.Draw(texture,new Rectangle(80,80,1100,480),new Color((byte)(frames%255),(byte)120,(byte)190));batch.End();frames++;base.Draw(time);}
    protected override void Dispose(bool disposing){if(disposing){if(studio!=null){studio.release();studio=null;}texture?.Dispose();batch?.Dispose();}base.Dispose(disposing);}
}
