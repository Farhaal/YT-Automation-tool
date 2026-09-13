import subprocess
from backend.app.core.logger import logger

def run_startup_checks():
    logger.info("Starting OpenReel environment checks...")

    # GPU Check
    cuda_available = False
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            logger.info(f"GPU: [bold green]Found {torch.cuda.get_device_name(0)}[/bold green]")
        else:
            logger.info("GPU: [bold yellow]CUDA not available in PyTorch, falling back to CPU[/bold yellow]")
    except ImportError:
        logger.info("GPU: [bold yellow]PyTorch not installed, checking without PyTorch...[/bold yellow]")
        # Note: faster-whisper doesn't strictly need PyTorch, but for logging we usually check via torch.

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
