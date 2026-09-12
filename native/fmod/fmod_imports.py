"""Explicit Android FMOD import surface shared by the probe and port."""
import subprocess, json

def generate_imports(sdk, out, release=True):
    bridge={'open':'open_bridge','__android_log_write':'android_log','__assert2':'assert_bridge','__errno':'errno_bridge','__sF':'fake_stdio','_ZdlPv':'free','pthread_mutex_init':'mutex_init','pthread_mutex_destroy':'mutex_destroy','pthread_mutex_lock':'mutex_lock','pthread_mutex_trylock':'mutex_trylock','pthread_mutex_unlock':'mutex_unlock','pthread_mutexattr_init':'mattr_init','pthread_mutexattr_destroy':'mattr_destroy','pthread_mutexattr_settype':'mattr_type','pthread_once':'once','pthread_create':'create','pthread_attr_init':'attr_init','pthread_attr_destroy':'attr_destroy','pthread_attr_setstacksize':'attr_stack','pthread_attr_setdetachstate':'attr_detach','sem_init':'sem_init_bridge','sem_destroy':'sem_destroy_bridge','sem_post':'sem_post_bridge','sem_wait':'sem_wait_bridge','gettid':'gettid_bridge','clock_gettime':'clock_bridge','setpriority':'priority_bridge','syscall':'syscall_bridge','dlopen':'dlopen_bridge','dlclose':'dlclose_bridge','dlsym':'dlsym_bridge','dlerror':'dlerror_bridge','fprintf':'fprintf_bridge','fwrite':'fwrite_bridge','fflush':'fflush_bridge','fclose':'fclose_bridge'}
    direct=set('cos sprintf gettimeofday pthread_self usleep close read fdopen acosf asinf atan2f atoi calloc cosf exp2f expf fclose feof fmodf fopen fread free fseek ftell ldexp ldexpf log10f log logf malloc memchr memcmp memcpy memmove memset modff nanosleep pow powf qsort realloc sin sincos sincosf sinf sscanf strlen strncmp strncpy strtod strtoul tanf vsnprintf __cxa_atexit __cxa_finalize __cxa_guard_acquire __cxa_guard_release __cxa_pure_virtual'.split())
    syms=set()
    libs=('libfmod.so','libfmodstudio.so') if release else ('libfmodL.so','libfmodstudioL.so')
    for lib in libs:
     text=subprocess.check_output(['readelf','-Ws',str(sdk/'android'/lib)],text=True)
     for line in text.splitlines():
      fields=line.split()
      if len(fields)>=8 and fields[6]=='UND':syms.add(fields[7].split('@')[0])
    syms=sorted(s for s in syms if not s.startswith(('FMOD_','_ZN4FMOD')))
    code=[];table=[];unknown=[]
    for i,name in enumerate(syms):
     target=bridge.get(name,name if name in direct else None)
     if not target:
      target=f'unsupported_{i}';unknown.append(name);code.append(f'static void {target}(void){{unsupported("{name}");}}')
     table.append(f'{{"{name}",(uintptr_t)&{target}}}')
    code.append('static DynLibFunction imports[]={'+',\n'.join(table)+'};')
    (out/'imports.inc').write_text('\n'.join(code));(out/'imports.json').write_text(json.dumps({'adapted':bridge,'direct':sorted(direct),'fail_fast':unknown},indent=2))
    return unknown
