// Standalone FMOD 1.10.14 compatibility probe; no game code or save access.
#include "fmod.h"
#include "fmod_output.h"
#include "fmod_studio.h"
#if FMOD_VERSION != 0x00011014 || FMOD_OUTPUT_PLUGIN_VERSION != 3
#error This probe requires exact FMOD 1.10.14 and output API 3
#endif
#include <errno.h>
#include <math.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef __SWITCH__
#include "so_util.h"
#include <malloc.h>
#include <switch.h>
// Loaded native modules retain code mappings for the process lifetime.
// Exit through Horizon instead of returning a heap with code aliases to hbloader.
u32 __nx_applet_exit_mode = 1;
void android_load(void);
#define ROOT "sdmc:/switch/celeste-fmod-11014"
#define BANKROOT ROOT "/banks"
#else
#include <dlfcn.h>
#define ROOT "/output"
#define BANKROOT "/banks"
#endif
#ifdef __SWITCH__
static FILE *probe_file;
static Mutex probe_log_lock;
#endif
void probe_log(const char *fmt, ...) {
  char msg[1024];
  va_list v;
  va_start(v, fmt);
  vsnprintf(msg, sizeof(msg), fmt, v);
  va_end(v);
#ifdef __SWITCH__
  mutexLock(&probe_log_lock);
  svcOutputDebugString(msg, strlen(msg));
  if (probe_file) {
    fprintf(probe_file, "%s\n", msg);
    fflush(probe_file);
  }
  mutexUnlock(&probe_log_lock);
#endif
  puts(msg);
  fflush(stdout);
}
static void *lookup(const char *name) {
#ifdef __SWITCH__
  void *p = (void *)so_lookup_export_all(name);
#else
  void *p = dlsym(RTLD_DEFAULT, name);
#endif
  if (!p) {
    probe_log("FMOD_PROBE FAIL missing export %s", name);
    exit(2);
  }
  return p;
}
#define APIS(X)                                                                \
  X(FMOD_Studio_System_Create)                                                 \
  X(FMOD_Studio_System_GetLowLevelSystem) X(FMOD_System_GetVersion)                \
      X(FMOD_System_SetOutput) X(FMOD_Studio_System_Initialize) X(             \
          FMOD_Studio_System_Release) X(FMOD_Studio_System_Update)             \
          X(FMOD_System_RegisterOutput) X(FMOD_System_SetOutputByPlugin) X(    \
              FMOD_System_SetSoftwareFormat) X(FMOD_System_SetDSPBufferSize)   \
              X(FMOD_System_CreateDSPByType) X(FMOD_System_PlayDSP) X(         \
                  FMOD_DSP_SetParameterFloat) X(FMOD_DSP_Release)              \
                  X(FMOD_Channel_Stop) X(FMOD_Channel_SetVolume) X(            \
                      FMOD_Studio_Bank_LoadSampleData)                         \
                      X(FMOD_Studio_Bank_GetSampleLoadingState) X(             \
                          FMOD_Studio_System_LoadBankFile)                     \
                          X(FMOD_Studio_Bank_GetEventCount) X(                 \
                              FMOD_Studio_Bank_GetEventList)                   \
                              X(FMOD_Studio_EventDescription_GetPath) X(       \
                                  FMOD_Studio_EventDescription_CreateInstance) \
                                  X(FMOD_Studio_EventInstance_SetCallback) X(  \
                                      FMOD_Studio_EventInstance_Start)         \
                                      X(FMOD_Studio_EventInstance_Stop) X(     \
                                          FMOD_Studio_EventInstance_Release)   \
                                          X(FMOD_Studio_System_FlushCommands)
#define DECL(n) static __typeof__(&n) p_##n;
APIS(DECL)
#define LOAD(n) p_##n = (__typeof__(&n))lookup(#n);
#define CHECK(call)                                                            \
  do {                                                                         \
    FMOD_RESULT r = (call);                                                    \
    if (r != FMOD_OK) {                                                        \
      probe_log("FMOD_PROBE FAIL %s result=%d", #call, r);                     \
      exit(3);                                                                 \
    }                                                                          \
  } while (0)
static FILE *pcm;
static uint64_t sample_count;
static double power;
static float peak;
static int markers, beats;
static int output_live;
static uint64_t next_audio_ns;
static uint64_t now_ns(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return (uint64_t)t.tv_sec * 1000000000ULL + t.tv_nsec;
}
#ifdef __SWITCH__
static AudioOutBuffer ab;
static int16_t *audio_pcm;
static unsigned released_total;
#endif
static FMOD_RESULT F_CALL drivers(FMOD_OUTPUT_STATE *s, int *n) {
  *n = 1;
  return FMOD_OK;
}
static FMOD_RESULT F_CALL driverinfo(FMOD_OUTPUT_STATE *s, int id, char *n,
                                         int len, FMOD_GUID *g, int *r,
                                         FMOD_SPEAKERMODE *m, int *c) {
  snprintf(n, len, "Probe PCM");
  memset(g, 0, sizeof(*g));
  *r = 48000;
  *m = FMOD_SPEAKERMODE_STEREO;
  *c = 2;
  return FMOD_OK;
}
static FMOD_RESULT F_CALL output_init(FMOD_OUTPUT_STATE *s, int d,
                                          FMOD_INITFLAGS fl, int *r,
                                          FMOD_SPEAKERMODE *m, int *c,
                                          FMOD_SOUND_FORMAT *f, int bl, int nb, void *user) {
  *r = 48000;
  *m = FMOD_SPEAKERMODE_STEREO;
  *c = 2;
  *f = FMOD_SOUND_FORMAT_PCMFLOAT;
  probe_log("FMOD_PROBE output init block=%d buffers=%d", bl, nb);
  return FMOD_OK;
}
static FMOD_RESULT F_CALL output_update(FMOD_OUTPUT_STATE *s) {
  float buffer[1024 * 2];
  FMOD_RESULT r = s->readfrommixer(s, buffer, 1024);
  if (r != FMOD_OK)
    return r;
  for (int i = 0; i < 2048; i++) {
    if (!isfinite(buffer[i]))
      return FMOD_ERR_INTERNAL;
    float v = fabsf(buffer[i]);
    if (v > peak)
      peak = v;
    power += (double)v * v;
  }
  sample_count += 2048;
  if (pcm && fwrite(buffer, sizeof(float), 2048, pcm) != 2048)
    return FMOD_ERR_FILE_BAD;
#ifdef __SWITCH__
  if (output_live) {
    for (int i = 0; i < 2048; i++)
      audio_pcm[i] = (int16_t)(fmaxf(-1, fminf(1, buffer[i])) * 32767);
    armDCacheFlush(audio_pcm, 4096);
    AudioOutBuffer *released = NULL;
    Result rc = audoutAppendAudioOutBuffer(&ab);
    if (R_FAILED(rc)) {
      probe_log("FMOD_PROBE FAIL append %x", rc);
      return FMOD_ERR_OUTPUT_DRIVERCALL;
    }
    u32 count = 0;
    rc = audoutWaitPlayFinish(&released, &count, 1000000000ULL);
    if (R_FAILED(rc) || released != &ab || count != 1) {
      probe_log("FMOD_PROBE FAIL audio wait %x count=%u", rc, count);
      return FMOD_ERR_OUTPUT_DRIVERCALL;
    }
    released_total += count;
  }
#endif
  uint64_t now = now_ns();
  if (!next_audio_ns || now > next_audio_ns + 100000000ULL)
    next_audio_ns = now;
  next_audio_ns += 1024ULL * 1000000000ULL / 48000;
  if (now < next_audio_ns) {
    uint64_t wait = next_audio_ns - now;
    struct timespec t = {wait / 1000000000ULL, wait % 1000000000ULL};
    while (nanosleep(&t, &t) && errno == EINTR) {
    }
  }
  return FMOD_OK;
}
static FMOD_RESULT F_CALL output_close(FMOD_OUTPUT_STATE *s) { return FMOD_OK; }
static FMOD_OUTPUT_DESCRIPTION output = {
    .apiversion = FMOD_OUTPUT_PLUGIN_VERSION,
    .name = "Switch probe PCM",
    .version = 1,
    .polling = 0,
    .getnumdrivers = drivers,
    .getdriverinfo = driverinfo,
    .init = output_init,
    .update = output_update,
    .close = output_close};
static FMOD_RESULT F_CALL timeline(FMOD_STUDIO_EVENT_CALLBACK_TYPE t,
                                       FMOD_STUDIO_EVENTINSTANCE *ev,
                                       void *data) {
  if (t == FMOD_STUDIO_EVENT_CALLBACK_TIMELINE_MARKER) {
    FMOD_STUDIO_TIMELINE_MARKER_PROPERTIES *p = data;
    markers++;
    probe_log("FMOD_PROBE marker %d name=%s position=%d", markers, p->name,
              p->position);
  }
  if (t == FMOD_STUDIO_EVENT_CALLBACK_TIMELINE_BEAT) {
    FMOD_STUDIO_TIMELINE_BEAT_PROPERTIES *p = data;
    beats++;
    if (beats <= 4)
      probe_log("FMOD_PROBE beat tempo=%.2f position=%d", p->tempo,
                p->position);
  }
  return FMOD_OK;
}
static void run(FMOD_STUDIO_SYSTEM *s, int frames) {
  for (int i = 0; i < frames; i++)
    CHECK(p_FMOD_Studio_System_Update(s));
}
static void reset_stats(const char *name) {
  if (pcm)
    fclose(pcm);
  char path[512];
  snprintf(path, sizeof(path), ROOT "/%s.f32", name);
  pcm = fopen(path, "wb");
  if (!pcm) {
    probe_log("FMOD_PROBE FAIL capture open %s", path);
    exit(4);
  }
  sample_count = 0;
  power = 0;
  peak = 0;
}
static void stats(const char *name) {
  if (pcm) {
    fclose(pcm);
    pcm = NULL;
  }
  probe_log("FMOD_PROBE PCM %s frames=%llu peak=%.6f rms=%.6f", name,
            (unsigned long long)(sample_count / 2), peak,
            sample_count ? sqrt(power / sample_count) : 0);
  if (peak < 0.00001f) {
    probe_log("FMOD_PROBE FAIL silent %s", name);
    exit(5);
  }
}
int main(void) {
#ifdef __SWITCH__
  probe_file = fopen(ROOT "/probe.log", "w");
  if (!probe_file) return 11;
#endif
  probe_log("FMOD_PROBE BOOT");
#ifdef __SWITCH__
  android_load();
#else
  if (!dlopen("/sdk/linux/libfmod.so.10.14",
              RTLD_NOW | RTLD_GLOBAL) ||
      !dlopen("/sdk/linux/libfmodstudio.so.10.14",
              RTLD_NOW | RTLD_GLOBAL)) {
    probe_log("FMOD_PROBE FAIL dlopen %s", dlerror());
    return 1;
  }
#endif
  APIS(LOAD)
  __typeof__(&FMOD_Debug_Initialize) debug_init =
      lookup("FMOD_Debug_Initialize");
  FMOD_RESULT dr =
      debug_init(FMOD_DEBUG_LEVEL_LOG, FMOD_DEBUG_MODE_TTY, NULL, NULL);
  probe_log("FMOD_PROBE debug init=%d", dr);
  FMOD_STUDIO_SYSTEM *s;
  FMOD_SYSTEM *c;
  unsigned version;
  CHECK(p_FMOD_Studio_System_Create(&s, FMOD_VERSION));
  CHECK(p_FMOD_Studio_System_GetLowLevelSystem(s, &c));
  CHECK(p_FMOD_System_GetVersion(c, &version));
  probe_log("FMOD_PROBE VERSION %x", version);
  if (version != 0x00011014) { probe_log("FMOD_PROBE FAIL wrong runtime version"); return 10; }
  CHECK(p_FMOD_System_SetOutput(c, FMOD_OUTPUTTYPE_NOSOUND_NRT));
  CHECK(p_FMOD_Studio_System_Initialize(
      s, 64, FMOD_STUDIO_INIT_SYNCHRONOUS_UPDATE,
      FMOD_INIT_STREAM_FROM_UPDATE | FMOD_INIT_MIX_FROM_UPDATE, NULL));
  run(s, 4);
  CHECK(p_FMOD_Studio_System_Release(s));
  probe_log("FMOD_PROBE PASS silent initialization and release");
  CHECK(p_FMOD_Studio_System_Create(&s, FMOD_VERSION));
  CHECK(p_FMOD_Studio_System_GetLowLevelSystem(s, &c));
  unsigned handle;
  CHECK(p_FMOD_System_RegisterOutput(c, &output, &handle));
  CHECK(p_FMOD_System_SetOutputByPlugin(c, handle));
  CHECK(p_FMOD_System_SetSoftwareFormat(c, 48000, FMOD_SPEAKERMODE_STEREO, 0));
  CHECK(p_FMOD_System_SetDSPBufferSize(c, 1024, 4));
#ifdef __SWITCH__
  Result rc = audoutInitialize();
  probe_log("FMOD_PROBE audoutInitialize %x", rc);
  if (R_FAILED(rc))
    return 6;
  audio_pcm = memalign(4096, 4096);
  ab = (AudioOutBuffer){
      .buffer = audio_pcm, .buffer_size = 4096, .data_size = 4096};
  rc = audoutStartAudioOut();
  if (R_FAILED(rc)) {
    probe_log("FMOD_PROBE FAIL audoutStart %x", rc);
    return 6;
  }
  output_live = 1;
#endif
  CHECK(p_FMOD_Studio_System_Initialize(
      s, 64, FMOD_STUDIO_INIT_SYNCHRONOUS_UPDATE,
      FMOD_INIT_STREAM_FROM_UPDATE | FMOD_INIT_MIX_FROM_UPDATE, NULL));
  FMOD_DSP *dsp;
  FMOD_CHANNEL *channel;
  CHECK(p_FMOD_System_CreateDSPByType(c, FMOD_DSP_TYPE_OSCILLATOR, &dsp));
  CHECK(p_FMOD_DSP_SetParameterFloat(dsp, FMOD_DSP_OSCILLATOR_RATE, 440));
  CHECK(p_FMOD_System_PlayDSP(c, dsp, NULL, 0, &channel));
  CHECK(p_FMOD_Channel_SetVolume(channel, 0.15f));
  reset_stats("tone");
  run(s, 94);
  stats("tone");
  CHECK(p_FMOD_Channel_Stop(channel));
  CHECK(p_FMOD_DSP_Release(dsp));
#ifdef FMOD_PROBE_EVENT
  const char *banks[] = {FMOD_PROBE_BANK_FILES};
  FMOD_STUDIO_EVENTDESCRIPTION *music = NULL;
  for (unsigned b = 0; b < sizeof(banks) / sizeof(banks[0]); b++) {
    char path[512];
    snprintf(path, sizeof(path), BANKROOT "/%s", banks[b]);
    FMOD_STUDIO_BANK *bank;
    CHECK(p_FMOD_Studio_System_LoadBankFile(
        s, path, FMOD_STUDIO_LOAD_BANK_NORMAL, &bank));
    int count;
    CHECK(p_FMOD_Studio_Bank_GetEventCount(bank, &count));
    if (count > 0) {
      CHECK(p_FMOD_Studio_Bank_LoadSampleData(bank));
      FMOD_STUDIO_LOADING_STATE loading;
      uint64_t deadline = now_ns() + 10000000000ULL;
      do {
        CHECK(p_FMOD_Studio_System_Update(s));
        CHECK(p_FMOD_Studio_Bank_GetSampleLoadingState(bank, &loading));
        if (loading == FMOD_STUDIO_LOADING_STATE_ERROR) {
          probe_log("FMOD_PROBE FAIL sample load");
          return 9;
        }
        if (now_ns() > deadline) {
          probe_log("FMOD_PROBE FAIL sample load timeout");
          return 9;
        }
        struct timespec pause = {0, 1000000};
        nanosleep(&pause, NULL);
      } while (loading != FMOD_STUDIO_LOADING_STATE_LOADED);
    }
    probe_log("FMOD_PROBE BANK %s events=%d", banks[b], count);
    FMOD_STUDIO_EVENTDESCRIPTION **list =
        calloc(count ? count : 1, sizeof(*list));
    int got;
    CHECK(p_FMOD_Studio_Bank_GetEventList(bank, list, count, &got));
    for (int i = 0; i < got; i++) {
      char name[256];
      int len;
      CHECK(p_FMOD_Studio_EventDescription_GetPath(list[i], name, sizeof(name),
                                                   &len));
      if (1) {
        probe_log("FMOD_PROBE event %s", name);
        if (strcmp(name, FMOD_PROBE_EVENT) == 0)
          music = list[i];
      }
    }
    free(list);
  }
  if (!music) {
    probe_log("FMOD_PROBE FAIL no music event");
    return 7;
  }
  char path[256];
  int len;
  CHECK(
      p_FMOD_Studio_EventDescription_GetPath(music, path, sizeof(path), &len));
  probe_log("FMOD_PROBE selected %s", path);
  FMOD_STUDIO_EVENTINSTANCE *event;
  CHECK(p_FMOD_Studio_EventDescription_CreateInstance(music, &event));
  CHECK(p_FMOD_Studio_EventInstance_SetCallback(
      event, timeline,
      FMOD_STUDIO_EVENT_CALLBACK_TIMELINE_MARKER |
          FMOD_STUDIO_EVENT_CALLBACK_TIMELINE_BEAT));
  CHECK(p_FMOD_Studio_EventInstance_Start(event));
  CHECK(p_FMOD_Studio_System_FlushCommands(s));
  reset_stats("music");
  run(s, 750);
  stats("music");
  CHECK(p_FMOD_Studio_EventInstance_Stop(event, FMOD_STUDIO_STOP_IMMEDIATE));
  CHECK(p_FMOD_Studio_EventInstance_Release(event));
#endif
  CHECK(p_FMOD_Studio_System_Release(s));
  if (pcm)
    fclose(pcm);
#ifdef __SWITCH__
  audoutStopAudioOut();
  audoutExit();
  probe_log("FMOD_PROBE audout released=%u", released_total);
#endif
  probe_log("FMOD_PROBE DONE markers=%d beats=%d", markers, beats);
  return 0; // A supplied event need not contain timeline markers.
}
