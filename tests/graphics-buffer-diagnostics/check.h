// Failure-only buffer state dump for the existing Mesa driver. Testing only.
#include <switch/kernel/svc.h>
#include <switch/result.h>
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>

static int readable_range(const void *pointer, size_t bytes, u32 permission) {
    uintptr_t at = (uintptr_t)pointer;
    if (!bytes || bytes > UINTPTR_MAX - at) return 0;
    uintptr_t end = at + bytes;
    while (at < end) {
        MemoryInfo info; u32 page;
        if (R_FAILED(svcQueryMemory(&info, &page, at)) ||
            (info.perm & permission) != permission || info.addr + info.size <= at) return 0;
        at = info.addr + info.size;
    }
    return 1;
}
static void dump_words(const char *label, const void *pointer, size_t bytes) {
    if (!readable_range(pointer, bytes, Perm_R)) {
        fprintf(stderr, "BUFFER_DIAGNOSTIC %s=%p unreadable\n", label, pointer);
        return;
    }
    const u64 *words = pointer;
    for (size_t i = 0; i < bytes / sizeof(u64); i += 4)
        fprintf(stderr, "BUFFER_DIAGNOSTIC %s+%zu %016lx %016lx %016lx %016lx\n",
            label, i * sizeof(u64), words[i], words[i+1], words[i+2], words[i+3]);
}
static void check_buffer_mapping(struct pipe_context *pipe, struct pipe_resource *resource,
        struct pipe_transfer *transfer, void *map, unsigned offset, unsigned size,
        unsigned usage, const void *data) {
    if (readable_range(map, size, Perm_W)) return;
    struct mallinfo heap = mallinfo();
    fprintf(stderr, "BUFFER_DIAGNOSTIC invalid map=%p size=%u offset=%u usage=%x source=%p pipe=%p resource=%p transfer=%p native_allocated=%zu native_free=%zu\n",
        map, size, offset, usage, data, (void*)pipe, (void*)resource, (void*)transfer,
        (size_t)heap.uordblks, (size_t)heap.fordblks);
    dump_words("resource", resource, 192);
    dump_words("transfer", transfer, 96);
    dump_words("source", data, size < 32 ? 0 : 32);
    fflush(stderr);
    abort();
}
