"""One worker and hard process ceilings, not a machine fingerprint."""
import os
import platform
import sys
import time

_job = None

def _windows_limits():
    import ctypes
    from ctypes import wintypes
    global _job
    size = ctypes.c_size_t
    class Basic(ctypes.Structure):
        _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                    ('flags', wintypes.DWORD), ('min_ws', size), ('max_ws', size),
                    ('active', wintypes.DWORD), ('affinity', size),
                    ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', size),
                    ('job_memory', size), ('peak_process', size), ('peak_job', size)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(size), ctypes.POINTER(size)]
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, size]
    process = kernel.GetCurrentProcess()
    _job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    # Job objects enforce per-process CPU time and committed-memory limits.
    limits.basic.process_time = 300 * 10_000_000
    limits.basic.flags = 0x2 | 0x100
    limits.process_memory = 3 * 1024**3
    if not _job or not kernel.SetInformationJobObject(_job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(_job, process):
        raise ctypes.WinError(ctypes.get_last_error())
    allowed, system = size(), size()
    if not kernel.GetProcessAffinityMask(process, ctypes.byref(allowed), ctypes.byref(system)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.SetProcessAffinityMask(process, allowed.value & -allowed.value):
        raise ctypes.WinError(ctypes.get_last_error())

def peak_rss_kib():
    if os.name != 'nt':
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / 1024 if sys.platform == 'darwin' else value
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('peak_ws', 'ws', 'peak_paged', 'paged',
                                                'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.peak_ws / 1024

def environment():
    cpu = platform.processor()
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    if os.name == 'nt':
        import ctypes
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
        if not kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(), ctypes.byref(allowed), ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        affinity = [i for i in range(allowed.value.bit_length()) if allowed.value & (1 << i)]
    return {'cpu': cpu, 'os': platform.platform(),
            'system': {'name': platform.system(), 'release': platform.release(),
                       'version': platform.version(), 'machine': platform.machine()},
            'python': sys.version, 'implementation': platform.python_implementation(),
            'executable': os.path.basename(sys.executable), 'logical_processor_affinity': affinity,
            'clock': vars(time.get_clock_info('perf_counter')),
            'limits': {'cpu_seconds': 300, 'memory_bytes': 3 * 1024**3,
                       'cpu_scope': 'user-mode CPU time' if os.name == 'nt' else 'user plus system CPU time',
                       'memory_scope': 'committed virtual memory' if os.name == 'nt' else 'virtual address space',
                       'mechanism': 'Windows job object' if os.name == 'nt' else 'POSIX resource limits'},
            'workers': 1}

def constrain():
    if hasattr(os,'sched_getaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[key]='1'
    if os.name == 'nt':
        _windows_limits()
        return
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(290,300))
    cap=3*1024**3
    _,hard=resource.getrlimit(resource.RLIMIT_AS)
    if hard!=resource.RLIM_INFINITY:cap=min(cap,hard)
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
