// Narrow, fail-fast Android ABI adapter for the FMOD feasibility probe.
#include "so_util.h"
#include <errno.h>
#include <fcntl.h>
#include <malloc.h>
#include <math.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <switch.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>
void probe_log(const char *, ...);
int debugPrintf(const char *fmt, ...) {
  char b[1024];
  va_list v;
  va_start(v, fmt);
  vsnprintf(b, sizeof(b), fmt, v);
  va_end(v);
  probe_log("LOADER %s", b);
  return 0;
}
__attribute__((noreturn)) void fatal_error(const char *fmt, ...) {
  char b[1024];
  va_list v;
  va_start(v, fmt);
  vsnprintf(b, sizeof(b), fmt, v);
  va_end(v);
  probe_log("FMOD_PROBE FAIL %s", b);
  exit(20);
}
__attribute__((noreturn)) static void unsupported(const char *n) {
  fatal_error("unsupported Android call %s", n);
}
static uint64_t main_tls[128];
static void set_tls(void *p) { __asm__ volatile("msr tpidr_el0, %0" ::"r"(p)); }
static pthread_mutex_t adapter_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t *get_mutex(uintptr_t *slot) {
  pthread_mutex_lock(&adapter_lock);
  if (*slot <= 0xffff) {
    unsigned type = *slot;
    pthread_mutex_t *m = malloc(sizeof(*m));
    if (!m)
      fatal_error("mutex allocation");
    pthread_mutexattr_t at;
    pthread_mutexattr_init(&at);
    if (type & 0x4000)
      pthread_mutexattr_settype(&at, PTHREAD_MUTEX_RECURSIVE);
    else if (type & 0x8000)
      pthread_mutexattr_settype(&at, PTHREAD_MUTEX_ERRORCHECK);
    int rc = pthread_mutex_init(m, &at);
    pthread_mutexattr_destroy(&at);
    if (rc)
      fatal_error("mutex init %d", rc);
    *slot = (uintptr_t)m;
  }
  pthread_mutex_t *m = (void *)*slot;
  pthread_mutex_unlock(&adapter_lock);
  return m;
}
static int mutex_init(uintptr_t *p, const int *a) {
  *p = a && *a == 1 ? 0x4000 : a && *a == 2 ? 0x8000 : 0;
  get_mutex(p);
  return 0;
}
static int mutex_destroy(uintptr_t *p) {
  pthread_mutex_t *m = get_mutex(p);
  int r = pthread_mutex_destroy(m);
  if (!r) {
    free(m);
    *p = 0;
  }
  return r;
}
static int mutex_lock(uintptr_t *p) { return pthread_mutex_lock(get_mutex(p)); }
static int mutex_trylock(uintptr_t *p) {
  int r = pthread_mutex_trylock(get_mutex(p));
  return r == EBUSY ? 16 : r;
}
static int mutex_unlock(uintptr_t *p) {
  return pthread_mutex_unlock(get_mutex(p));
}
static int mattr_init(int *p) {
  *p = 0;
  return 0;
}
static int mattr_type(int *p, int t) {
  if (t > 2 || t < 0)
    return 22;
  *p = t;
  return 0;
}
static int mattr_destroy(int *p) { return 0; }
static int once(int *p, void (*fn)(void)) {
  int expected = 0;
  if (__atomic_compare_exchange_n(p, &expected, 1, 0, __ATOMIC_ACQ_REL,
                                  __ATOMIC_ACQUIRE)) {
    fn();
    __atomic_store_n(p, 2, __ATOMIC_RELEASE);
  } else
    while (__atomic_load_n(p, __ATOMIC_ACQUIRE) != 2)
      svcSleepThread(100000);
  return 0;
}
typedef struct {
  size_t stack;
  int detached;
} Attr;
static int attr_init(Attr *a) {
  a->stack = 256 * 1024;
  a->detached = 0;
  return 0;
}
static int attr_destroy(Attr *a) { return 0; }
static int attr_stack(Attr *a, size_t n) {
  a->stack = n;
  return 0;
}
static int attr_detach(Attr *a, int n) {
  if (n < 0 || n > 1)
    return 22;
  a->detached = n;
  return 0;
}
typedef struct {
  void *(*fn)(void *);
  void *arg;
} Start;
static void *thread_start(void *p) {
  Start start = *(Start *)p;
  free(p);
  uint64_t tls[128] = {0};
  set_tls(tls);
  return start.fn(start.arg);
}
static int create(uint64_t *out, const Attr *a, void *(*fn)(void *),
                  void *arg) {
  Start *s = malloc(sizeof(*s));
  if (!s)
    return 12;
  *s = (Start){fn, arg};
  pthread_attr_t at;
  pthread_attr_init(&at);
  pthread_attr_setstacksize(&at,
                            a && a->stack > 256 * 1024 ? a->stack : 256 * 1024);
  if (a && a->detached)
    pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
  pthread_t t;
  int r = pthread_create(&t, &at, thread_start, s);
  pthread_attr_destroy(&at);
  if (r)
    free(s);
  else {
    *out = (uint64_t)t;
    probe_log("FMOD_PROBE thread created");
  }
  return r;
}
_Static_assert(sizeof(Semaphore) <= 16, "Bionic semaphore storage");
static int sem_init_bridge(Semaphore *s, int shared, unsigned n) {
  if (shared)
    unsupported("process shared semaphore");
  semaphoreInit(s, n);
  return 0;
}
static int sem_destroy_bridge(Semaphore *s) { return 0; }
static int sem_post_bridge(Semaphore *s) {
  semaphoreSignal(s);
  return 0;
}
static int sem_wait_bridge(Semaphore *s) {
  semaphoreWait(s);
  return 0;
}
static int android_log(int level, const char *tag, const char *message) {
  probe_log("ANDROID %s: %s", tag, message);
  return 0;
}
static int *errno_bridge(void) { return &errno; }
static int gettid_bridge(void) {
  u64 id = 0;
  svcGetThreadId(&id, CUR_THREAD_HANDLE);
  return (int)id;
}
static int clock_bridge(int c, struct timespec *t) {
  if (c == 0)
    return clock_gettime(CLOCK_REALTIME, t);
  if (c == 1) {
    uint64_t n = armTicksToNs(armGetSystemTick());
    t->tv_sec = n / 1000000000;
    t->tv_nsec = n % 1000000000;
    return 0;
  }
  unsupported("clock id");
  return -1;
}
// Linux nice 0 maps to the normal homebrew thread priority; preserve its order.
// Only current-thread requests are supported. Unsupported requests fail visibly.
static int priority_bridge(int which, unsigned who, int priority) {
  if (which != 0 || (who && who != (unsigned)gettid_bridge()) || priority < -20 || priority > 19) {
    errno = 22;
    return -1;
  }
  Result rc = svcSetThreadPriority(CUR_THREAD_HANDLE, 0x2c + priority);
  probe_log("FMOD_PROBE priority nice=%d native=%d result=%x", priority, 0x2c + priority, rc);
  if (R_FAILED(rc)) { errno = 1; return -1; }
  return 0;
}
static long syscall_bridge(long n, ...) {
  if (n == 178) return gettid_bridge();
  if (n == 122) { // AArch64 Linux sched_setaffinity for the current thread.
    va_list args; va_start(args, n);
    int tid = va_arg(args, int); size_t bytes = va_arg(args, size_t);
    const void *mask = va_arg(args, const void *); va_end(args);
    if (tid && tid != gettid_bridge()) { errno = 3; return -1; }
    if (!bytes) { errno = 22; return -1; }
    if (!mask) { errno = 14; return -1; }
    uint64_t requested = 0, allowed = 0;
    memcpy(&requested, mask, bytes < sizeof(requested) ? bytes : sizeof(requested));
    Result rc = svcGetInfo(&allowed, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0);
    if (R_FAILED(rc)) { errno = 1; return -1; }
    uint64_t effective = requested & allowed;
    if (!effective) { errno = 22; return -1; }
    rc = svcSetThreadCoreMask(CUR_THREAD_HANDLE, -1, (u32)effective);
    probe_log("FMOD_PROBE sched_setaffinity tid=%d requested=%lx effective=%lx result=%x", tid, (unsigned long)requested, (unsigned long)effective, rc);
    if (R_FAILED(rc)) { errno = 22; return -1; }
    return 0;
  }
  if (n == 123) { // AArch64 Linux sched_getaffinity; raw syscall returns byte count.
    va_list args; va_start(args, n);
    int tid = va_arg(args, int);
    size_t bytes = va_arg(args, size_t);
    void *mask = va_arg(args, void *);
    va_end(args);
    if (tid && tid != gettid_bridge()) { errno = 3; return -1; }
    if (bytes < sizeof(uint64_t)) { errno = 22; return -1; }
    if (!mask) { errno = 14; return -1; }
    s32 preferred; u64 affinity;
    Result rc = svcGetThreadCoreMask(&preferred, &affinity, CUR_THREAD_HANDLE);
    if (R_FAILED(rc)) { errno = 1; return -1; }
    memcpy(mask, &affinity, sizeof(affinity));
    probe_log("FMOD_PROBE sched_getaffinity tid=%d size=%lu mask=%lx", tid, (unsigned long)bytes, (unsigned long)affinity);
    return sizeof(affinity);
  }
  probe_log("FMOD_PROBE syscall %ld", n);
  unsupported("syscall");
}
static void *dlopen_bridge(const char *n, int flags) {
  probe_log("FMOD_PROBE dlopen %s", n ? n : "NULL");
  if (!n)
    return so_first();
  const char *b = strrchr(n, '/');
  return so_find_module(b ? b + 1 : n);
}
static void *dlsym_bridge(void *h, const char *n) {
  return (void *)(so_is_module(h) ? so_lookup_export(h, n)
                                  : so_lookup_export_all(n));
}
static int dlclose_bridge(void *h) { return 0; }
static char *dlerror_bridge(void) {
  return "library unavailable in FMOD probe";
}
static void assert_bridge(const char *f, int l, const char *fn, const char *e) {
  fatal_error("Android assert %s:%d %s %s", f, l, fn, e);
}
extern int __cxa_atexit(void (*)(void *), void *, void *);
extern void __cxa_finalize(void *);
extern int __cxa_guard_acquire(void *);
extern void __cxa_guard_release(void *);
extern void __cxa_pure_virtual(void);
static unsigned char fake_stdio[3][152];
static FILE *stdio_map(FILE *f) {
  uintptr_t offset = (uintptr_t)f - (uintptr_t)fake_stdio;
  if (offset < sizeof(fake_stdio)) {
    if (offset % 152)
      unsupported("stdio interior access");
    return offset == 0 ? stdin : offset == 152 ? stdout : stderr;
  }
  return f;
}
static int fprintf_bridge(FILE *f, const char *fmt, ...) {
  va_list v;
  va_start(v, fmt);
  int n = vfprintf(stdio_map(f), fmt, v);
  va_end(v);
  return n;
}
static size_t fwrite_bridge(const void *p, size_t a, size_t b, FILE *f) {
  return fwrite(p, a, b, stdio_map(f));
}
static int fflush_bridge(FILE *f) { return fflush(f ? stdio_map(f) : NULL); }
static int fclose_bridge(FILE *f) { return fclose(stdio_map(f)); }
static int open_bridge(const char *path, int flags, ...) {
  probe_log("FMOD_PROBE open %s flags=%x", path, flags);
  int f = flags & 3;
  if (flags & 0100)
    f |= O_CREAT;
  if (flags & 0200)
    f |= O_EXCL;
  if (flags & 01000)
    f |= O_TRUNC;
  if (flags & 02000)
    f |= O_APPEND;
  if (flags & 04000)
    f |= O_NONBLOCK;
  if (flags & ~(3 | 0100 | 0200 | 01000 | 02000 | 04000 | 02000000))
    unsupported("open flags");
  int mode = 0;
  if (flags & 0100) {
    va_list v;
    va_start(v, flags);
    mode = va_arg(v, int);
    va_end(v);
  }
  int fd = open(path, f, mode);
  probe_log("FMOD_PROBE open result=%d errno=%d", fd, fd < 0 ? errno : 0);
  return fd;
}
#include "imports.inc"
static Handle probe_process;
Handle probeProcessHandle(void) { return probe_process; }
static void send_handle(void *arg) {
  Handle client = *(Handle *)arg;
  HipcRequest req =
      hipcMakeRequestInline(armGetTls(), .type = 4, .num_copy_handles = 1);
  req.copy_handles[0] = CUR_PROCESS_HANDLE;
  Result rc = svcSendSyncRequest(client);
  probe_log("FMOD_PROBE handle sender result=%x", rc);
}
static void acquire_process(void) {
  probe_process = envGetOwnProcessHandle();
  if (probe_process)
    return;
  Handle server, client;
  Result rc = svcCreateSession(&server, &client, false, 0);
  if (R_FAILED(rc))
    fatal_error("create local session %x", rc);
  Thread sender;
  rc = threadCreate(&sender, send_handle, &client, NULL, 0x10000, 0x2c, -2);
  if (R_FAILED(rc))
    fatal_error("create handle thread %x", rc);
  threadStart(&sender);
  s32 index;
  rc = svcReplyAndReceive(&index, &server, 1, INVALID_HANDLE, 1000000000LL);
  if (R_FAILED(rc))
    fatal_error("receive process handle %x", rc);
  HipcParsedRequest req = hipcParseRequest(armGetTls());
  if (req.meta.num_copy_handles != 1)
    fatal_error("no copied process handle");
  probe_process = req.data.copy_handles[0];
  svcCloseHandle(server);
  threadWaitForExit(&sender);
  threadClose(&sender);
  svcCloseHandle(client);
  probe_log("FMOD_PROBE acquired process handle=%x", probe_process);
}
void android_load(void) {
  set_tls(main_tls);
  acquire_process();
  probe_log("FMOD_PROBE process handle=%x mapcode=%d", probe_process,
            envIsSyscallHinted(0x77));
  static so_module modules[2];
#ifdef FMOD_PROBE_RELEASE
  const char *names[] = {"libfmod.so", "libfmodstudio.so"};
#else
  const char *names[] = {"libfmodL.so", "libfmodstudioL.so"};
#endif

  for (int i = 0; i < 2; i++) {
    char p[256];
    snprintf(p, sizeof(p), "sdmc:/switch/celeste-fmod-11014/lib/%s", names[i]);
    void *base = memalign(4096, 8 * 1024 * 1024);
    if (!base)
      fatal_error("load allocation");
    int r = so_load(&modules[i], p, base, 8 * 1024 * 1024);
    if (r)
      fatal_error("load %s %d", p, r);
    so_relocate(&modules[i]);
  }
  for (int i = 0; i < 2; i++)
    if (so_resolve(&modules[i], imports, sizeof(imports) / sizeof(imports[0]),
                   0))
      fatal_error("unresolved imports");
  for (int i = 0; i < 2; i++) {
    so_finalize(&modules[i]);
    so_flush_caches(&modules[i]);
  }
  for (int i = 0; i < 2; i++) {
    probe_log("FMOD_PROBE constructors %s", names[i]);
    so_execute_init_array(&modules[i]);
  }
  probe_log("FMOD_PROBE libraries loaded");
  extern void probe_jni_init(void);
  probe_jni_init();
}
