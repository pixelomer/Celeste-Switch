#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <SDL2/SDL.h>
#include <string.h>
#include "coreclr-libnx.h"
#include "nxvm.h"
#ifdef CELESTE_NXLINK_STDIO
#include <switch.h>
#endif
extern void* monomod_libnx_exception_helper(int);
extern void* PAL_LoadLibraryDirect(const char*);
extern void* PAL_GetProcAddressDirect(void*,const char*);
extern int PAL_FreeLibraryDirect(void*);
extern void* CelesteFmodResolve(const char*,const char*);
extern unsigned __nx_nv_transfermem_size;
extern char *fake_heap_start, *fake_heap_end;
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
#ifdef CELESTE_NXLINK_STDIO
    // Optional test transport already provided by libnx and the nxlink launcher.
    // Keep BSD/socket lifetime through process exit, including runtime workers.
    Result network = socketInitializeDefault();
    if (R_FAILED(network)) {
        fprintf(stderr, "HOST nxlink socket initialization failed result=%08x\n", network);
        return 1;
    }
    if (nxlinkStdio() < 0) {
        perror("HOST nxlink stdout/stderr connection");
        return 1;
    }
    printf("HOST live nxlink stdout/stderr enabled\n");
#endif
    // Set libnx's supported NV service budget before the graphics driver starts.
#if CELESTE_NV_TRANSFER_MIB
    __nx_nv_transfermem_size = (unsigned)CELESTE_NV_TRANSFER_MIB << 20;
#endif
    printf("HOST NV transfer memory=%u\n", __nx_nv_transfermem_size);
    // libnx reserves the native heap up front; mallinfo's current arena is not
    // the whole available heap. Report the actual loader/libnx-provided extent.
    printf("HOST native heap extent=%zu\n", (size_t)(fake_heap_end - fake_heap_start));
    // Configure the existing shared allocator before CoreCLR/BCL initialize it.
    // This is physical data backing, separate from native graphics, audio and
    // executable-code allocations. The runtime's GC reads this actual capacity.
    const size_t managed_pool = (size_t)CELESTE_MANAGED_POOL_MIB << 20;
    bool pool_ready;
#if CELESTE_PROTECTED_MANAGED_POOL
    pool_ready = nxvm_init_protected(managed_pool);
#else
    pool_ready = nxvm_ensure_initialized(managed_pool);
#endif
    if (!pool_ready || nxvm_stats().capacity != managed_pool) {
        fprintf(stderr, "HOST managed pool initialization failed requested=%zu actual=%zu\n",
                managed_pool, nxvm_stats().capacity);
        return 1;
    }
    printf("HOST managed pool=%zu virtual arena=%zu\n", managed_pool, nxvm_virtual_capacity());
    printf("HOST protected managed pool=%d\n", CELESTE_PROTECTED_MANAGED_POOL);
#if CELESTE_GC_REGION_MIB
    // Use the upstream GC tuning option, without changing reservation semantics.
    // Keep room in the shared arena for GC bookkeeping and other PAL/BCL users.
    const size_t gc_region = (size_t)CELESTE_GC_REGION_MIB << 20;
    if (gc_region + ((size_t)64 << 20) > nxvm_virtual_capacity()) {
        fprintf(stderr, "HOST GC region leaves insufficient shared virtual space\n");
        return 1;
    }
    char region_config[32];
    snprintf(region_config, sizeof(region_config), "%zx", gc_region);
    if (setenv("DOTNET_GCRegionRange", region_config, 1) != 0) return 1;
    printf("HOST configured GC region=%zu\n", gc_region);
#endif
    if (chdir("sdmc:/switch/celeste-pc") != 0) { perror("Celeste working directory"); return 1; }
    if (mkdir("sdmc:/switch/celeste-pc/tmp", 0777) != 0 && errno != EEXIST) {
        perror("Celeste temporary directory"); return 1;
    }
    struct stat temp;
    if (stat("sdmc:/switch/celeste-pc/tmp", &temp) != 0 || !S_ISDIR(temp.st_mode)) return 1;
    setenv("TMPDIR", "/switch/celeste-pc/tmp", 1);
    // Existing Everest option: preserve the error log without launching a viewer.
    setenv("EVEREST_NO_ERRORLOG_ON_CRASH", "1", 1);
    setenv("FNA3D_FORCE_DRIVER", "OpenGL", 1);
    setenv("FNA_AUDIO_DISABLE_SOUND", "1", 1);
    setenv("FNA3D_OPENGL_DISABLE_LATESWAPTEAR", "1", 1);
    char *prefs = SDL_GetPrefPath(NULL, "Celeste");
    printf("HOST SDL=%s preferences=%s\n", SDL_GetPlatform(), prefs ? prefs : "(null)");
    int failed = !prefs || strcmp(prefs, "/switch/celeste-pc/");
    SDL_free(prefs);
    return failed != 0;
}
