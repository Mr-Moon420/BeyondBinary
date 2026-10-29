"""Shared device selection and bounded inference for the laptop's GPU."""
import os
import threading
from contextlib import nullcontext

import torch

_GPU_LOCK = threading.RLock()


def uses_cuda():
    return os.getenv("BEYONDBINARY_DEVICE", "auto").lower() != "cpu" and torch.cuda.is_available()


def pipeline_options():
    # FP16 fits the existing classifiers on a 4 GB GPU. Preserve CPU precision.
    return {
        "device": 0 if uses_cuda() else -1,
        "dtype": torch.float16 if uses_cuda() else torch.bfloat16,
        "low_cpu_mem_usage": True,
    }


def inference_slot():
    # Concurrent requests share the models; do not overlap GPU activation peaks.
    return _GPU_LOCK if uses_cuda() else nullcontext()
