// Failure-only diagnostics around the existing public libnx NV interfaces.
#include <switch.h>
#include <malloc.h>
#include <stdio.h>
static unsigned creates, allocations, mappings;
static void failed(const char *stage, Result rc, size_t size) {
    size_t count = 0; uintptr_t at = 0;
    while (count < 100000) {
        MemoryInfo info; u32 page;
        if (R_FAILED(svcQueryMemory(&info, &page, at))) break;
        ++count;
        uintptr_t end = info.addr + info.size;
        if (!info.size || end <= at) break;
        at = end;
    }
    struct mallinfo heap = mallinfo();
    fprintf(stderr, "NV_DIAGNOSTIC stage=%s result=%08x size=%zu creates=%u allocations=%u mappings=%u kernel_records=%zu native_allocated=%zu native_free=%zu\n",
        stage, rc, size, creates, allocations, mappings, count,
        (size_t)heap.uordblks, (size_t)heap.fordblks);
    fflush(stderr);
}
Result __real_nvioctlNvmap_Create(u32, u32, u32 *);
Result __wrap_nvioctlNvmap_Create(u32 fd, u32 size, u32 *handle) {
    __atomic_add_fetch(&creates, 1, __ATOMIC_RELAXED);
    Result rc = __real_nvioctlNvmap_Create(fd, size, handle);
    if (R_FAILED(rc)) failed("NvmapCreate", rc, size);
    return rc;
}
Result __real_nvioctlNvmap_Alloc(u32, u32, u32, u32, u32, u8, void *);
Result __wrap_nvioctlNvmap_Alloc(u32 fd, u32 handle, u32 heapmask, u32 flags, u32 align, u8 kind, void *address) {
    __atomic_add_fetch(&allocations, 1, __ATOMIC_RELAXED);
    Result rc = __real_nvioctlNvmap_Alloc(fd, handle, heapmask, flags, align, kind, address);
    if (R_FAILED(rc)) failed("NvmapAlloc", rc, 0);
    return rc;
}
Result __real_nvAddressSpaceMap(NvAddressSpace *, u32, bool, NvKind, iova_t *);
Result __wrap_nvAddressSpaceMap(NvAddressSpace *space, u32 handle, bool cacheable, NvKind kind, iova_t *out) {
    __atomic_add_fetch(&mappings, 1, __ATOMIC_RELAXED);
    Result rc = __real_nvAddressSpaceMap(space, handle, cacheable, kind, out);
    if (R_FAILED(rc)) failed("AddressSpaceMap", rc, 0);
    return rc;
}
