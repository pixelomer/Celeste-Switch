// Compile the real Mesa allocator with fault-injected BO creation. No GPU use.
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "nouveau_mm.c"

unsigned __nx_applet_exit_mode = 1;
static bool fail_bo = true;
static struct nouveau_bo test_bo;
static unsigned invalid_references;
int nouveau_bo_new(struct nouveau_device *dev, uint32_t flags, uint32_t align,
        uint64_t size, union nouveau_bo_config *config, struct nouveau_bo **out) {
    if (fail_bo) return -ENOMEM;
    memset(&test_bo, 0, sizeof(test_bo));
    test_bo.device = dev; test_bo.flags = flags; test_bo.size = size;
    test_bo.offset = 0x10000000;
    *out = &test_bo;
    return 0;
}
void nouveau_bo_ref(struct nouveau_bo *bo, struct nouveau_bo **out) {
    if (bo && bo != &test_bo) ++invalid_references;
    *out = bo;
}
static FILE *logfile;
static unsigned checks;
static void check(bool ok, const char *name) {
    ++checks;
    if (!ok) { fprintf(logfile, "FAIL %s checks=%u\n", name, checks); abort(); }
}
int main(void) {
    logfile = fopen(TEST_FIXED ? "sdmc:/switch/mesa-allocator-fixed.txt" :
                                "sdmc:/switch/mesa-allocator-original.txt", "w");
    if (!logfile) return 1;
    setvbuf(logfile, NULL, _IONBF, 0);
    union nouveau_bo_config config = {0};
    struct nouveau_mman *cache = nouveau_mm_create(NULL, NOUVEAU_BO_GART, &config);
    check(cache != NULL, "create cache");
    struct nouveau_bo *bo = NULL;
    uint32_t offset = 999;
    struct nouveau_mm_allocation *allocation = nouveau_mm_allocate(cache, 256, &bo, &offset);
    fprintf(logfile, "RESULT fixed=%d allocation=%p bo=%p offset=%u invalid_refs=%u\n",
        TEST_FIXED, (void*)allocation, (void*)bo, offset, invalid_references);
    if (!TEST_FIXED) {
        check(allocation && bo && invalid_references, "reproduce invalid slab after failed BO creation");
        // The original corrupted its list; process teardown reclaims this test.
        fprintf(logfile, "CONTROL reproduced invalid allocation checks=%u\n", checks);
        fclose(logfile); return 0;
    }
    check(!allocation && !bo && !offset && !invalid_references, "failed BO allocation propagates");
    struct mm_bucket *bucket = mm_bucket_by_size(cache, 256);
    check(list_is_empty(&bucket->free) && list_is_empty(&bucket->used) && list_is_empty(&bucket->full), "failure preserves empty lists");
    fail_bo = false;
    for (unsigned i = 0; i < 256; ++i) {
        allocation = nouveau_mm_allocate(cache, 256, &bo, &offset);
        check(allocation && bo == &test_bo && !(offset & 255), "retry returns aligned allocation");
        nouveau_mm_free(allocation);
        nouveau_bo_ref(NULL, &bo);
    }
    check(!invalid_references, "all subsequent BO references valid");
    nouveau_mm_destroy(cache);
    fprintf(logfile, "PASS checks=%u lifetimes=256\n", checks);
    fclose(logfile); return 0;
}
