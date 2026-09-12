#include <string.h>
extern void* PAL_LoadLibraryDirect(const char*);
extern void* PAL_GetProcAddressDirect(void*,const char*);
extern int PAL_FreeLibraryDirect(void*);
extern void* CelesteFmodResolve(const char*,const char*);
void* HostResolvePInvoke(const char *library,const char *entry){
    void *audio=CelesteFmodResolve(library,entry);if(audio)return audio;
    if(!library||!entry||(strcmp(library,"SDL2")&&strcmp(library,"FNA3D")))return 0;
    void *module=PAL_LoadLibraryDirect(0);if(!module)return 0;
    void *result=PAL_GetProcAddressDirect(module,entry);PAL_FreeLibraryDirect(module);return result;
}
