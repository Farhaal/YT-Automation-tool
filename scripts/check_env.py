import subprocess
import sys


def print_status(name, status, details=""):
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    mark = "[OK]" if status else "[FAIL]"
    print(f"{color}{mark} {name}{reset} {details}")

def main():
    print("--- OpenReel Environment Check ---")

    # Python version
    py_version = sys.version_info
    py_ok = py_version.major == 3 and py_version.minor >= 11
    print_status("Python 3.11+", py_ok, f"(Found {sys.version.split()[0]})")

    # Virtual Environment
    in_venv = sys.prefix != sys.base_prefix
    print_status("Virtual Environment", in_venv, "(Running in .venv)" if in_venv else "(Not in venv)")

    # CUDA
    cuda_ok = False
    cuda_details = "(Not found)"
    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            cuda_ok = True
            cuda_details = f"(Found {cuda_count} CUDA device(s) via CTranslate2)"
        else:
            cuda_details = "(CUDA not available in CTranslate2)"
    except ImportError:
         cuda_details = "(CTranslate2 not installed yet)"
    
    print_status("CUDA / GPU", cuda_ok, cuda_details)

    # FFmpeg
    ffmpeg_ok = False
    ffmpeg_details = "(Not found)"
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            ffmpeg_ok = True
            # Check for nvenc
            nvenc_check = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=False)
            if "nvenc" in nvenc_check.stdout:
                ffmpeg_details = "(Found NVENC support)"
    except Exception:
        pass
        
    if not ffmpeg_ok:
        try:
            import imageio_ffmpeg
            _ = imageio_ffmpeg.get_ffmpeg_exe()
            ffmpeg_ok = True
            ffmpeg_details = "(Found bundled imageio-ffmpeg)"
        except (ImportError, Exception):
            pass
            
    print_status("FFmpeg", ffmpeg_ok, ffmpeg_details)

if __name__ == "__main__":
    main()
