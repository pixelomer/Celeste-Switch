// Native FMOD ABI integration for embedded CoreCLR and other homebrew hosts.
#include "fmod.h"
#include "fmod_studio.h"
#include "so_util.h"
#include <switch.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static Mutex load_lock,log_lock;
static int loaded;
void android_load(void);
FMOD_RESULT CelesteFmodConfigure(FMOD_SYSTEM*);
uint64_t CelesteAudioMixed(void),CelesteAudioNonzero(void),CelesteAudioReleased(void),CelesteAudioTimeouts(void);
int CelesteAudioError(void);
void probe_log(const char *fmt,...) {
    va_list args;va_start(args,fmt);mutexLock(&log_lock);
    vprintf(fmt,args);putchar('\n');fflush(stdout);
    mutexUnlock(&log_lock);va_end(args);
}
static FMOD_RESULT F_CALL create_studio(FMOD_STUDIO_SYSTEM **out,unsigned version) {
    __typeof__(&FMOD_Studio_System_Create) create=(void*)so_lookup_export_all("FMOD_Studio_System_Create");
    __typeof__(&FMOD_Studio_System_GetLowLevelSystem) low=(void*)so_lookup_export_all("FMOD_Studio_System_GetLowLevelSystem");
    __typeof__(&FMOD_Studio_System_Release) release=(void*)so_lookup_export_all("FMOD_Studio_System_Release");
    FMOD_RESULT r=create(out,version);if(r!=FMOD_OK)return r;
    FMOD_SYSTEM *system=NULL;r=low(*out,&system);
    if(r==FMOD_OK)r=CelesteFmodConfigure(system);
    if(r!=FMOD_OK){release(*out);*out=NULL;}
    return r;
}
static FMOD_RESULT F_CALL create_low(FMOD_SYSTEM **out) {
    __typeof__(&FMOD_System_Create) create=(void*)so_lookup_export_all("FMOD_System_Create");
    __typeof__(&FMOD_System_Release) release=(void*)so_lookup_export_all("FMOD_System_Release");
    FMOD_RESULT r=create(out);if(r!=FMOD_OK)return r;
    r=CelesteFmodConfigure(*out);
    if(r!=FMOD_OK){release(*out);*out=NULL;}
    return r;
}
void *CelesteFmodResolve(const char *library,const char *entry) {
    if(!library||!entry)return NULL;
    if(!strcmp(library,"CelestePlatform")) {
#define EXPORT(name) if(!strcmp(entry,#name))return (void*)name
        EXPORT(CelesteAudioMixed);EXPORT(CelesteAudioNonzero);EXPORT(CelesteAudioReleased);EXPORT(CelesteAudioTimeouts);EXPORT(CelesteAudioError);
#undef EXPORT
        return NULL;
    }
    if(strcmp(library,"fmod")&&strcmp(library,"fmodstudio")&&strcmp(library,"libfmod.so")&&strcmp(library,"libfmodstudio.so"))return NULL;
    mutexLock(&load_lock);
    if(!loaded){android_load();loaded=1;}
    mutexUnlock(&load_lock);
    if(!strcmp(entry,"FMOD_Studio_System_Create"))return (void*)create_studio;
    if(!strcmp(entry,"FMOD_System_Create"))return (void*)create_low;
    void *symbol=(void*)so_lookup_export_all(entry);
    if(!symbol)probe_log("FMOD_IMPORT missing %s:%s",library,entry);
    return symbol;
}
