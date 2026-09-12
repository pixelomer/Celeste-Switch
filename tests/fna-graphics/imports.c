// Native dependency resolution for this original graphics probe.
#include <stdio.h>
#include <string.h>
#include <SDL.h>
#include <switch.h>
extern void* PAL_LoadLibraryDirect(const char*);
extern void* PAL_GetProcAddressDirect(void*, const char*);
extern int PAL_FreeLibraryDirect(void*);
static AppletHookCookie lifecycleCookie;
static unsigned resumeCount;
static void OnAppletLifecycle(AppletHookType type, void* unused)
{
    (void)unused;
    if (type == AppletHookType_OnResume) ++resumeCount;
}
unsigned ProbeConfigureLifecycle(void)
{
    Result result = appletSetFocusHandlingMode(AppletFocusHandlingMode_SuspendHomeSleepNotify);
    if (R_SUCCEEDED(result)) result = appletSetRestartMessageEnabled(true);
    if (R_SUCCEEDED(result)) appletHook(&lifecycleCookie, OnAppletLifecycle, NULL);
    return result;
}
unsigned ProbeResumeCount(void) { return resumeCount; }
unsigned ProbeGlError(void)
{
    typedef unsigned (*GetError)(void);
    GetError getError = (GetError)SDL_GL_GetProcAddress("glGetError");
    return getError ? getError() : ~0u;
}
void* HostResolvePInvoke(const char* library, const char* entry)
{
    if (!library || !entry) return NULL;
    if (!strcmp(library, "__Internal") && !strcmp(entry, "ProbeResumeCount")) return (void*)ProbeResumeCount;
    if (!strcmp(library, "__Internal") && !strcmp(entry, "ProbeConfigureLifecycle")) return (void*)ProbeConfigureLifecycle;
    if (!strcmp(library, "__Internal") && !strcmp(entry, "ProbeGlError")) return (void*)ProbeGlError;
    if (strcmp(library, "SDL2") && strcmp(library, "FNA3D")) return NULL;
    void* module = PAL_LoadLibraryDirect(NULL);
    if (!module) return NULL;
    void* address = PAL_GetProcAddressDirect(module, entry);
    PAL_FreeLibraryDirect(module);
    if (!address) fprintf(stderr, "Missing graphics import %s:%s\n", library, entry);
    return address;
}
