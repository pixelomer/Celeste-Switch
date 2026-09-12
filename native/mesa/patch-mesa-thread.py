#!/usr/bin/env python3
"""Experimental Mesa 20.1 Switch GL worker wiring; apply to a generated source copy."""
import sys
from pathlib import Path
root = Path(sys.argv[1])

def edit(relative, old, new):
    p = root / relative
    s = p.read_text()
    assert s.count(old) == 1, (relative, old, s.count(old))
    p.write_text(s.replace(old, new))
edit('src/mesa/state_tracker/st_manager.c', '#ifndef __SWITCH__\n   st->iface.start_thread = st_start_thread;\n   st->iface.thread_finish = st_thread_finish;\n#endif', '   st->iface.start_thread = st_start_thread;\n   st->iface.thread_finish = st_thread_finish;')
edit('src/mesa/state_tracker/st_context.c', '#ifndef __SWITCH__\n   /* This must be called first so that glthread has a chance to finish */\n   _mesa_glthread_destroy(ctx);\n#endif', '   /* This must be called first so that glthread has a chance to finish */\n   _mesa_glthread_destroy(ctx);')
f = 'src/egl/drivers/switch/egl_switch.c'
edit(f, 'static int\nswitch_st_get_param', "Result switch_worker_affinity;\nint switch_worker_core = -1;\nstatic void\nswitch_st_set_background_context(struct st_context_iface *stctx,\n                                 struct util_queue_monitoring *stats)\n{\n    /* EGL framebuffer callbacks use explicit stctx/surface pointers, not EGL TLS.\n       Mesa initializes the worker's GL TLS immediately after this callback. */\n    switch_worker_affinity = svcSetThreadCoreMask(CUR_THREAD_HANDLE, 1, 1ULL << 1);\n    switch_worker_core = svcGetCurrentProcessorNumber();\n}\n\nstatic int\nswitch_st_get_param")
edit(f, 'stmgr->get_param = switch_st_get_param;', 'stmgr->get_param = switch_st_get_param;\n    stmgr->set_background_context = switch_st_set_background_context;')
edit(f, '    return &context->base;', '    if (debug_get_bool_option("CELESTE64_MESA_THREAD", false))\n        context->stctx->start_thread(context->stctx);\n    return &context->base;')
edit(f, '    EGLBoolean ret = disp->stapi->make_current', '    /* Finish old work before replacing drawables or releasing their references. */\n    if (old_ctx) {\n        struct switch_egl_context *old = switch_egl_context(old_ctx);\n        old->stctx->thread_finish(old->stctx);\n    }\n    EGLBoolean ret = disp->stapi->make_current')
edit(f, '    if (surface->cur_slot < 0) {', '    /* Drain BEFORE reading cur_slot: the worker can dequeue the first buffer. */\n    context->stctx->thread_finish(context->stctx);\n    if (surface->cur_slot < 0) {')
p = root / 'src/mesa/state_tracker/st_manager.c'
edit('include/c11/threads.h', '#ifndef HAVE_TIMESPEC_GET', '#if !defined(HAVE_TIMESPEC_GET) && !defined(__SWITCH__)')
edit('src/util/u_thread.h', '   if (ret)\n      return 0;', '   if (ret != thrd_success)\n      return 0;')
p = root / 'src/mesa/state_tracker/st_manager.c'
edit('src/egl/drivers/switch/egl_switch.c', '        context->stctx->destroy(context->stctx);', '        context->stctx->thread_finish(context->stctx);\n        context->stctx->destroy(context->stctx);')
