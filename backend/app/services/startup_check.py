import subprocess

from backend.app.core.logger import logger


def run_startup_checks():
    logger.info("Starting OpenReel environment checks...")

    # GPU Check
    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            logger.info(f"GPU: [bold green]Found {cuda_count} CUDA device(s) via CTranslate2[/bold green]")
        else:
            logger.info("GPU: [bold yellow]CUDA not available in CTranslate2, falling back to CPU[/bold yellow]")
    except ImportError:
        logger.info("GPU: [bold yellow]CTranslate2 not installed, cannot verify GPU[/bold yellow]")

    # FFmpeg check
    ffmpeg_ok = False
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            ffmpeg_ok = True
            nvenc_check = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=False)
            has_nvenc = "nvenc" in nvenc_check.stdout.lower()
            nvenc_str = "[bold green]Yes[/bold green]" if has_nvenc else "[bold yellow]No[/bold yellow]"
            logger.info(f"FFmpeg: [bold green]Found system ffmpeg[/bold green]. NVENC support: {nvenc_str}")
    except FileNotFoundError:
        # Check bundled imageio_ffmpeg
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            ffmpeg_ok = True
            logger.info(f"FFmpeg: [bold green]Found bundled ffmpeg[/bold green] at {exe}")
        except Exception:
            pass

    if not ffmpeg_ok:
        logger.error("FFmpeg: [bold red]Not found![/bold red] Rendering will fail.")
