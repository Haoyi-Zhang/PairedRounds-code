"""One worker and hard process ceilings, not a machine fingerprint."""
import os
import resource

def constrain():
    if hasattr(os,'sched_getaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_CPU,(290,300))
    cap=3*1024**3
    _,hard=resource.getrlimit(resource.RLIMIT_AS)
    if hard!=resource.RLIM_INFINITY:cap=min(cap,hard)
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
