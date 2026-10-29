import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ModelRuntimeTests(unittest.TestCase):
    def load_runtime(self, cuda_available):
        fake_torch = SimpleNamespace(
            float16="fp16", bfloat16="bf16",
            cuda=SimpleNamespace(is_available=lambda: cuda_available),
        )
        path = Path(__file__).resolve().parents[1] / "backend" / "model_runtime.py"
        spec = importlib.util.spec_from_file_location("runtime_under_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"torch": fake_torch}):
            spec.loader.exec_module(module)
        return module

    def test_gpu_uses_fp16_and_shared_memory_guard(self):
        runtime = self.load_runtime(True)
        with patch.dict(os.environ, {"BEYONDBINARY_DEVICE": "auto"}):
            self.assertEqual(runtime.pipeline_options()["device"], 0)
            self.assertEqual(runtime.pipeline_options()["dtype"], "fp16")
            self.assertIs(runtime.inference_slot(), runtime.inference_slot())

    def test_cpu_environment_and_override_keep_cpu_precision(self):
        for cuda_available, override in [(False, "auto"), (True, "cpu")]:
            runtime = self.load_runtime(cuda_available)
            with patch.dict(os.environ, {"BEYONDBINARY_DEVICE": override}):
                self.assertEqual(runtime.pipeline_options()["device"], -1)
                self.assertEqual(runtime.pipeline_options()["dtype"], "bf16")


if __name__ == "__main__":
    unittest.main()
