// FMOD 1.10.14 asynchronous output using Horizon audout.
#include "fmod.h"
#include "fmod_output.h"
#include "so_util.h"
#include <switch.h>
#include <malloc.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#if FMOD_VERSION != 0x00011014 || FMOD_OUTPUT_PLUGIN_VERSION != 3
#error Exact FMOD 1.10.14 / output API3 required
#endif
#define BUFFERS 4
#define BLOCK 512
void probe_log(const char*,...);
typedef struct {
    AudioOutBuffer buffers[BUFFERS];
    int pending[BUFFERS];
    float mix[BLOCK*2];
    unsigned next;
    uint64_t deadline;
} Output;
static int device_owned;
static uint64_t mixed, nonzero, released, timeouts;
static int output_error;
uint64_t CelesteAudioMixed(void) { return __atomic_load_n(&mixed,__ATOMIC_RELAXED); }
uint64_t CelesteAudioNonzero(void) { return __atomic_load_n(&nonzero,__ATOMIC_RELAXED); }
uint64_t CelesteAudioReleased(void) { return __atomic_load_n(&released,__ATOMIC_RELAXED); }
uint64_t CelesteAudioTimeouts(void) { return __atomic_load_n(&timeouts,__ATOMIC_RELAXED); }
int CelesteAudioError(void) { return __atomic_load_n(&output_error,__ATOMIC_RELAXED); }
static FMOD_RESULT fail(int code) {
    __atomic_store_n(&output_error,code,__ATOMIC_RELAXED);
    probe_log("FMOD_OUTPUT error=%x",code);
    return FMOD_ERR_OUTPUT_DRIVERCALL;
}
static FMOD_RESULT F_CALL drivers(FMOD_OUTPUT_STATE *s,int *n) { *n=1;return FMOD_OK; }
static FMOD_RESULT F_CALL info(FMOD_OUTPUT_STATE *s,int id,char *name,int len,FMOD_GUID *guid,int *rate,FMOD_SPEAKERMODE *mode,int *channels) {
    if(id!=0)return FMOD_ERR_INVALID_PARAM;
    if(len>0)snprintf(name,len,"Horizon audout");
    memset(guid,0,sizeof(*guid));*rate=48000;*mode=FMOD_SPEAKERMODE_STEREO;*channels=2;return FMOD_OK;
}
static FMOD_RESULT F_CALL close_output(FMOD_OUTPUT_STATE *s) {
    Output *o=s->plugindata;
    if(!o)return FMOD_OK;
    audoutExit();
    for(unsigned i=0;i<BUFFERS;i++)free(o->buffers[i].buffer);
    free(o);s->plugindata=NULL;
    __atomic_store_n(&device_owned,0,__ATOMIC_RELEASE);
    return FMOD_OK;
}
static FMOD_RESULT F_CALL init(FMOD_OUTPUT_STATE *s,int driver,FMOD_INITFLAGS flags,int *rate,FMOD_SPEAKERMODE *mode,int *channels,FMOD_SOUND_FORMAT *format,int block,int count,void *user) {
    if(driver!=0 || block!=BLOCK)return FMOD_ERR_OUTPUT_FORMAT;
    int expected=0;
    if(!__atomic_compare_exchange_n(&device_owned,&expected,1,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return FMOD_ERR_OUTPUT_ALLOCATED;
    Output *o=calloc(1,sizeof(*o));
    if(!o){__atomic_store_n(&device_owned,0,__ATOMIC_RELEASE);return FMOD_ERR_MEMORY;}
    Result rc=audoutInitialize();
    if(R_FAILED(rc)){free(o);__atomic_store_n(&device_owned,0,__ATOMIC_RELEASE);return fail(rc);}
    s->plugindata=o;
    if(audoutGetSampleRate()!=48000 || audoutGetChannelCount()!=2){close_output(s);return FMOD_ERR_OUTPUT_FORMAT;}
    for(unsigned i=0;i<BUFFERS;i++){
        void *data=memalign(4096,4096);
        if(!data){close_output(s);return FMOD_ERR_MEMORY;}
        o->buffers[i]=(AudioOutBuffer){.buffer=data,.buffer_size=4096,.data_size=BLOCK*2*sizeof(int16_t)};
    }
    *rate=48000;*mode=FMOD_SPEAKERMODE_STEREO;*channels=2;*format=FMOD_SOUND_FORMAT_PCMFLOAT;
    probe_log("FMOD_OUTPUT ready rate=48000 block=%d buffers=%d",BLOCK,BUFFERS);
    return FMOD_OK;
}
static FMOD_RESULT F_CALL start(FMOD_OUTPUT_STATE *s) {Result r=audoutStartAudioOut();return R_SUCCEEDED(r)?FMOD_OK:fail(r);}
static FMOD_RESULT F_CALL stop(FMOD_OUTPUT_STATE *s) {Result r=audoutStopAudioOut();return R_SUCCEEDED(r)?FMOD_OK:fail(r);}
static FMOD_RESULT F_CALL mix(FMOD_OUTPUT_STATE *s) {
    Output *o=s->plugindata;
    uint64_t now=armTicksToNs(armGetSystemTick());
    const uint64_t duration=BLOCK*1000000000ULL/48000;
    if(!o->deadline || now>o->deadline+100000000ULL)o->deadline=now-(BUFFERS-1)*duration;
    if(now<o->deadline)svcSleepThread(o->deadline-now);
    o->deadline+=duration;
    unsigned slot=o->next%BUFFERS;
    while(o->pending[slot]){
        AudioOutBuffer *done=NULL;u32 count=0;
        Result rc=audoutWaitPlayFinish(&done,&count,200000000ULL);
        // Return on every timeout so FMOD can stop/join its own mixer thread.
        // Retain ownership of the pending buffer for the next invocation.
        if(R_VALUE(rc)==KERNELRESULT(TimedOut)){__atomic_fetch_add(&timeouts,1,__ATOMIC_RELAXED);return FMOD_OK;}
        if(R_FAILED(rc))return fail(rc);
        if(!count)return FMOD_OK;
        int found=0;
        for(unsigned i=0;i<BUFFERS;i++)if(done==&o->buffers[i] && o->pending[i]){o->pending[i]=0;found=1;}
        if(!found || count!=1)return fail(-2);
        __atomic_fetch_add(&released,1,__ATOMIC_RELAXED);
    }
    FMOD_RESULT r=s->readfrommixer(s,o->mix,BLOCK);
    if(r!=FMOD_OK)return fail(r);
    int any=0;int16_t *pcm=o->buffers[slot].buffer;
    for(unsigned i=0;i<BLOCK*2;i++){
        float v=o->mix[i];if(!isfinite(v))return fail(-3);
        if(fabsf(v)>0.00001f)any=1;
        pcm[i]=(int16_t)(fmaxf(-1,fminf(1,v))*32767);
    }
    armDCacheFlush(pcm,BLOCK*2*sizeof(int16_t));
    Result rc=audoutAppendAudioOutBuffer(&o->buffers[slot]);
    if(R_FAILED(rc))return fail(rc);
    o->pending[slot]=1;o->next++;
    __atomic_fetch_add(&mixed,1,__ATOMIC_RELAXED);
    if(any)__atomic_fetch_add(&nonzero,1,__ATOMIC_RELAXED);
    return FMOD_OK;
}
static FMOD_OUTPUT_DESCRIPTION output={.apiversion=FMOD_OUTPUT_PLUGIN_VERSION,.name="Horizon audout",.version=1,.polling=0,.getnumdrivers=drivers,.getdriverinfo=info,.init=init,.start=start,.stop=stop,.close=close_output,.mixer=mix};
FMOD_RESULT CelesteFmodConfigure(FMOD_SYSTEM *system) {
    __typeof__(&FMOD_System_RegisterOutput) reg=(void*)so_lookup_export_all("FMOD_System_RegisterOutput");
    __typeof__(&FMOD_System_SetOutputByPlugin) select=(void*)so_lookup_export_all("FMOD_System_SetOutputByPlugin");
    __typeof__(&FMOD_System_SetSoftwareFormat) format=(void*)so_lookup_export_all("FMOD_System_SetSoftwareFormat");
    __typeof__(&FMOD_System_SetDSPBufferSize) buffer=(void*)so_lookup_export_all("FMOD_System_SetDSPBufferSize");
    __typeof__(&FMOD_System_GetVersion) version=(void*)so_lookup_export_all("FMOD_System_GetVersion");
    unsigned actual=0,handle;FMOD_RESULT r;
    if(!version)return FMOD_ERR_UNSUPPORTED;
    if((r=version(system,&actual))!=FMOD_OK)return r;
    if(actual!=0x00011014){probe_log("FMOD_OUTPUT version mismatch=%x",actual);return FMOD_ERR_VERSION;}
    if(!reg||!select||!format||!buffer)return FMOD_ERR_UNSUPPORTED;
    if((r=reg(system,&output,&handle))!=FMOD_OK)return r;
    if((r=select(system,handle))!=FMOD_OK)return r;
    if((r=format(system,48000,FMOD_SPEAKERMODE_STEREO,0))!=FMOD_OK)return r;
    return buffer(system,BLOCK,BUFFERS);
}
