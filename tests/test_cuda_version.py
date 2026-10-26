import subprocess
import pytest

def test_cuda_version():
    smi_version_details = subprocess.check_output(
        ["nvidia-smi", "--version"], text=True
    ).strip()

    cuda_version = None
    version_lines = ["CUDA UMD version", "CUDA version"]
    for version_line in version_lines:
        for line in smi_version_details.splitlines():
            if version_line in line and "Deprecated" not in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    cuda_version = parts[1].strip()
                break
        if cuda_version:
            break
    if not cuda_version:
        raise RuntimeError("CUDA version could not be determined from `nvidia-smi` output.")

    assert cuda_version=="13.3", "CUDA version could not be determined from `nvidia-smi` output."

if __name__ == "__main__":
    pytest.main([__file__])