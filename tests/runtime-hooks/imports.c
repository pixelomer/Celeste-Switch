// Explicit native host contract; managed mods are not compiled into this table.
#include <string.h>
#include "coreclr-libnx.h"
extern void* monomod_libnx_exception_helper(int index);
// Original regression fixture, not a runtime or mod API.
int ProbeInvokeCallback(int (*callback)(int), int value) { return callback(value); }
void* HostResolvePInvoke(const char* library, const char* entry)
{
    if (!library || !entry || strcmp(library, "__Internal") != 0) return NULL;
#define EXPORT(name) if (strcmp(entry, #name) == 0) return (void*)name
    EXPORT(coreclr_libnx_get_jit);
    EXPORT(coreclr_libnx_jit_get_compile_callback);
    EXPORT(coreclr_libnx_jit_set_compile_callback);
    EXPORT(coreclr_libnx_memory_granularity);
    EXPORT(coreclr_libnx_memory_allocate);
    EXPORT(coreclr_libnx_memory_free);
    EXPORT(coreclr_libnx_memory_readable);
    EXPORT(coreclr_libnx_memory_patch);
    EXPORT(monomod_libnx_exception_helper);
    EXPORT(ProbeInvokeCallback);
#undef EXPORT
    return NULL;
}
