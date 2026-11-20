"""Local FLUX.1-schnell image generation through stable-diffusion.cpp."""

import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


MODEL_CARD_URL = "https://huggingface.co/black-forest-labs/FLUX.1-schnell"
RELEASES_API = "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest"
MODEL_FILES = (
    (
        "flux1-schnell-q2_k.gguf",
        "https://huggingface.co/leejet/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-q2_k.gguf",
        4110959520,
        "e23c3c58b5475937419dd34ec0ccac301d8348ceadd7838eb367e6ce9329c836",
    ),
    (
        "clip_l.safetensors",
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors",
        246144152,
        "660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd",
    ),
    (
        "t5xxl_fp8_e4m3fn.safetensors",
        "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors",
        4893934904,
        "7d330da4816157540d6bb7838bf63a0f02f573fc48ca4d8de34bb0cbfd514f09",
    ),
    (
        "ae.safetensors",
        "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors",
        335304388,
        None,
    ),
)
ENGINE_DIRNAME = "stable-diffusion.cpp-win-vulkan"


def data_dir():
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return root / "Calisto" / "image_generation"


def model_dir():
    return data_dir() / "models"


def engine_dir():
    return data_dir() / ENGINE_DIRNAME


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        redirected = super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            new_url,
        )
        if redirected and request.host.casefold() != urllib.parse.urlparse(new_url).netloc.casefold():
            redirected.remove_header("Authorization")
        return redirected


def _download(url, destination, expected_size=None, expected_sha256=None, token=None, progress=None):
    destination = Path(destination)
    if destination.exists() and destination.stat().st_size == expected_size:
        if expected_sha256 is None or _sha256(destination) == expected_sha256:
            return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(destination.name + ".part")
    headers = {"User-Agent": "Calisto/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    try:
        opener = urllib.request.build_opener(_SafeRedirectHandler())
        with opener.open(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or expected_size or 0)
            received = 0
            last_report = 0.0
            digest = hashlib.sha256()
            with temporary_path.open("wb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if progress and (now - last_report >= 0.5 or (total and received >= total)):
                        progress(received, total)
                        last_report = now
        if expected_size is not None and received != expected_size:
            raise IOError(
                "Taille inattendue pour {} : {} octets reçus au lieu de {}.".format(
                    destination.name, received, expected_size
                )
            )
        if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
            raise IOError("La vérification SHA-256 a échoué pour {}.".format(destination.name))
        os.replace(str(temporary_path), str(destination))
    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise


def _latest_windows_runtime(progress=None):
    request = urllib.request.Request(
        RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Calisto"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.loads(response.read().decode("utf-8"))
    asset = next(
        (
            item
            for item in release.get("assets", [])
            if item.get("name", "").endswith("win-vulkan-x64.zip")
        ),
        None,
    )
    if not asset:
        raise RuntimeError("Aucun binaire Vulkan Windows n'est disponible dans la dernière version.")
    digest = str(asset.get("digest") or "")
    expected_hash = digest.split(":", 1)[1] if digest.startswith("sha256:") else None
    archive_path = data_dir() / "downloads" / asset["name"]
    _download(
        asset["browser_download_url"],
        archive_path,
        expected_size=asset.get("size"),
        expected_sha256=expected_hash,
        progress=progress,
    )
    return archive_path


def _install_runtime(archive_path):
    target_dir = engine_dir()
    staging_dir = target_dir.with_name(target_dir.name + ".installing")
    if staging_dir.exists():
        shutil.rmtree(str(staging_dir))
    staging_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(str(archive_path)) as archive:
            root = staging_dir.resolve()
            members = archive.infolist()
            for member in members:
                resolved = (staging_dir / member.filename).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError as error:
                    raise ValueError("L'archive du moteur contient un chemin invalide.") from error
            archive.extractall(str(staging_dir))
        executable = next(staging_dir.rglob("sd-cli.exe"), None)
        if executable is None:
            raise RuntimeError("Le binaire sd-cli.exe est absent de l'archive téléchargée.")
        if target_dir.exists():
            shutil.rmtree(str(target_dir))
        os.replace(str(staging_dir), str(target_dir))
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(str(staging_dir))
        raise


def install(on_progress=None, token=None):
    data_dir().mkdir(parents=True, exist_ok=True)
    model_dir().mkdir(parents=True, exist_ok=True)
    if os.name == "nt" and not any(engine_dir().rglob("sd-cli.exe")):
        archive = _latest_windows_runtime(
            lambda received, total: on_progress("Moteur C++", received, total)
            if on_progress
            else None
        )
        _install_runtime(archive)
        archive.unlink()
    elif os.name != "nt":
        raise RuntimeError("L'installation automatique du moteur est actuellement disponible sous Windows.")

    for name, url, size, digest in MODEL_FILES:
        _download(
            url,
            model_dir() / name,
            expected_size=size,
            expected_sha256=digest,
            token=token if name == "ae.safetensors" else None,
            progress=lambda received, total, filename=name: on_progress(filename, received, total)
            if on_progress
            else None,
        )
    return True


def is_ready():
    if os.name != "nt":
        return False
    required = [model_dir() / item[0] for item in MODEL_FILES]
    return any(engine_dir().rglob("sd-cli.exe")) and all(
        path.is_file() and path.stat().st_size == size
        for path, (_, _, size, _) in zip(required, MODEL_FILES)
    )


def _executable():
    executable = next(engine_dir().rglob("sd-cli.exe"), None)
    if executable is None:
        raise FileNotFoundError("Le moteur d'images n'est pas installé. Ouvrez les réglages pour le configurer.")
    return executable


def generate(prompt, output_path, on_output=None, init_image=None, strength=0.6):
    if not is_ready():
        raise RuntimeError("Le moteur FLUX n'est pas installé ou ses modèles sont incomplets.")
    models = {name: model_dir() / name for name, _, _, _ in MODEL_FILES}
    command = [
        str(_executable()),
        "--diffusion-model",
        str(models["flux1-schnell-q2_k.gguf"]),
        "--vae",
        str(models["ae.safetensors"]),
        "--clip_l",
        str(models["clip_l.safetensors"]),
        "--t5xxl",
        str(models["t5xxl_fp8_e4m3fn.safetensors"]),
        "-p",
        str(prompt),
        "-o",
        str(output_path),
        "--cfg-scale",
        "1.0",
        "--sampling-method",
        "euler",
        "--steps",
        "12",
        "--clip-on-cpu",
        "--auto-fit",
        "on",
        "--width",
        "1024",
        "--height",
        "1024",
        "--offload-to-cpu",
    ]
    if init_image:
        command += ["-i", str(init_image), "--strength", str(strength)]
    process = subprocess.Popen(
        command,
        cwd=str(_executable().parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = []
    try:
        for line in process.stdout:
            line = line.rstrip()
            if line:
                output.append(line)
                if on_output:
                    on_output(line)
        return_code = process.wait()
    except Exception:
        process.kill()
        process.wait()
        raise
    if return_code != 0:
        detail = "\n".join(output[-20:])
        raise RuntimeError(
            "stable-diffusion.cpp a échoué (code {}).\n{}".format(
                return_code, detail or "Aucun détail fourni par le moteur."
            )
        )
    output_path = Path(output_path)
    if not output_path.is_file() or output_path.stat().st_size < 64:
        raise RuntimeError("Le moteur s'est terminé sans produire une image valide.")
    with output_path.open("rb") as image_file:
        if image_file.read(8) != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Le moteur n'a pas produit une image PNG valide.")
    return output_path
