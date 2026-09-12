// Deliberately limited JNI facade. Unsupported Java operations abort the probe.
#include "so_util.h"
#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void probe_log(const char *, ...);
void fatal_error(const char *, ...) __attribute__((noreturn));
static struct JNINativeInterface_ native;
static JNIEnv env = &native;
static struct JNIInvokeInterface_ invoke;
static JavaVM vm = &invoke;
static void unimplemented(void) { fatal_error("unsupported JNI operation"); }
static jint getenv_bridge(JavaVM *v, void **e, jint version) {
  *e = &env;
  return JNI_OK;
}
static jint attach_bridge(JavaVM *v, void **e, void *a) {
  *e = &env;
  return JNI_OK;
}
static jint detach_bridge(JavaVM *v) { return JNI_OK; }
static jclass find_class(JNIEnv *e, const char *n) {
  probe_log("FMOD_PROBE JNI FindClass %s", n);
  if (strcmp(n, "org/fmod/AudioDevice") && strcmp(n, "org/fmod/MediaCodec") &&
      strcmp(n, "org/fmod/FMOD"))
    fatal_error("unsupported JNI class %s", n);
  return (jclass)n;
}
static jobject global_ref(JNIEnv *e, jobject o) { return o; }
static void delete_ref(JNIEnv *e, jobject o) {}
static jboolean exception_check(JNIEnv *e) { return JNI_FALSE; }
static jthrowable exception_occurred(JNIEnv *e) { return NULL; }
static void exception_clear(JNIEnv *e) {}
static jmethodID static_method(JNIEnv *e, jclass c, const char *n,
                               const char *sig) {
  probe_log("FMOD_PROBE JNI static method %s %s", n, sig);
  return (jmethodID)strdup(n);
}
static jint static_int(JNIEnv *e, jclass c, jmethodID m, va_list args) {
  fatal_error("unsupported JNI int method %s", (char *)m);
}
static jboolean static_bool(JNIEnv *e, jclass c, jmethodID m, va_list args) {
  if (!strcmp((char *)m, "checkInit"))
    return JNI_FALSE;
  fatal_error("unsupported JNI bool method %s", (char *)m);
}
static jint getvm(JNIEnv *e, JavaVM **v) {
  *v = &vm;
  return JNI_OK;
}
void probe_jni_init(void) {
  for (size_t i = 0; i < sizeof(native) / sizeof(void *); i++) {
    void *p = (void *)unimplemented;
    memcpy((char *)&native + i * sizeof(void *), &p, sizeof(p));
  }
  native.FindClass = find_class;
  native.NewGlobalRef = global_ref;
  native.DeleteGlobalRef = delete_ref;
  native.DeleteLocalRef = delete_ref;
  native.ExceptionCheck = exception_check;
  native.ExceptionOccurred = exception_occurred;
  native.ExceptionClear = exception_clear;
  native.GetStaticMethodID = static_method;
  native.CallStaticIntMethodV = static_int;
  native.CallStaticBooleanMethodV = static_bool;
  native.GetJavaVM = getvm;
  invoke.GetEnv = getenv_bridge;
  invoke.AttachCurrentThread = attach_bridge;
  invoke.AttachCurrentThreadAsDaemon = attach_bridge;
  invoke.DetachCurrentThread = detach_bridge;
  jint (*onload)(JavaVM *, void *) = (void *)so_lookup_export_all("JNI_OnLoad");
  if (!onload)
    fatal_error("JNI_OnLoad missing");
  jint v = onload(&vm, NULL);
  probe_log("FMOD_PROBE JNI_OnLoad=%x", v);
  if (v != JNI_VERSION_1_6)
    fatal_error("JNI_OnLoad failed");
}
