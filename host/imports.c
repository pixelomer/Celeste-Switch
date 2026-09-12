#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <SDL2/SDL.h>
#include <string.h>
#include "coreclr-libnx.h"
extern void* monomod_libnx_exception_helper(int);
extern void* PAL_LoadLibraryDirect(const char*);
extern void* PAL_GetProcAddressDirect(void*,const char*);
extern int PAL_FreeLibraryDirect(void*);
extern void* CelesteFmodResolve(const char*,const char*);
void* HostResolvePInvoke(const char *library,const char *entry){
    if(library && entry && !strcmp(library,"__Internal")) {
#define EXPORT(name) if(!strcmp(entry,#name))return (void*)name
        EXPORT(coreclr_libnx_get_jit);EXPORT(coreclr_libnx_jit_get_compile_callback);EXPORT(coreclr_libnx_jit_set_compile_callback);
        EXPORT(coreclr_libnx_memory_granularity);EXPORT(coreclr_libnx_memory_allocate);EXPORT(coreclr_libnx_memory_free);
        EXPORT(coreclr_libnx_memory_readable);EXPORT(coreclr_libnx_memory_patch);EXPORT(monomod_libnx_exception_helper);
#undef EXPORT
    }
    void *audio=CelesteFmodResolve(library,entry);if(audio)return audio;
    if(!library||!entry||(strcmp(library,"SDL2")&&strcmp(library,"FNA3D")&&strcmp(library,"lua54")))return 0;
    void *module=PAL_LoadLibraryDirect(0);if(!module)return 0;
    void *result=PAL_GetProcAddressDirect(module,entry);PAL_FreeLibraryDirect(module);return result;
}

// SDL's homebrew preference policy uses cwd. Keep saves private to this port.
int HostConfigureApplication(void) {
    if (chdir("sdmc:/switch/celeste-pc") != 0) { perror("Celeste working directory"); return 1; }
    setenv("FNA3D_FORCE_DRIVER", "OpenGL", 1);
    setenv("FNA_AUDIO_DISABLE_SOUND", "1", 1);
    setenv("FNA3D_OPENGL_DISABLE_LATESWAPTEAR", "1", 1);
    char *prefs = SDL_GetPrefPath(NULL, "Celeste");
    printf("HOST SDL=%s preferences=%s\n", SDL_GetPlatform(), prefs ? prefs : "(null)");
    int failed = !prefs || strcmp(prefs, "/switch/celeste-pc/");
    SDL_free(prefs);
    return failed != 0;
}
