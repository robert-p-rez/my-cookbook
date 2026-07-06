from __future__ import annotations

import json
import os
import re
import shutil
import uuid
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import jwt
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from jwt import InvalidTokenError, PyJWKClient
from PIL import Image, UnidentifiedImageError


ACCESS_JWT_HEADER = "cf-access-jwt-assertion"
MAX_IMAGES = 20
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_TOTAL_BYTES = 90 * 1024 * 1024
SUBMISSION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ALLOWED_IMAGE_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}

Image.MAX_IMAGE_PIXELS = 50_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_team_domain(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("https://", "http://")):
        value = f"https://{value}"
    return value


def _email_set(value: str | None) -> frozenset[str]:
    return frozenset(
        email.strip().lower() for email in (value or "").split(",") if email.strip()
    )


@dataclass(frozen=True)
class Settings:
    upload_root: Path
    allowed_origin: str
    access_team_domain: str
    access_aud: str
    access_allowed_emails: frozenset[str]
    access_auth_bypass: bool = False

    @classmethod
    def from_environment(cls) -> "Settings":
        access_auth_bypass = _truthy(os.environ.get("ACCESS_AUTH_BYPASS"))
        access_team_domain = _normalize_team_domain(
            os.environ.get("CLOUDFLARE_ACCESS_TEAM_DOMAIN", "")
        )
        access_aud = os.environ.get("CLOUDFLARE_ACCESS_AUD", "").strip()

        if not access_auth_bypass:
            if not access_team_domain:
                raise RuntimeError("CLOUDFLARE_ACCESS_TEAM_DOMAIN must be set")
            if not access_aud:
                raise RuntimeError("CLOUDFLARE_ACCESS_AUD must be set")

        return cls(
            upload_root=Path(os.environ.get("UPLOAD_ROOT", "/data/uploads")).resolve(),
            allowed_origin=os.environ.get(
                "ALLOWED_ORIGIN", "https://gabbys-cookbook.perezdev.com"
            ).rstrip("/"),
            access_team_domain=access_team_domain,
            access_aud=access_aud,
            access_allowed_emails=_email_set(os.environ.get("ACCESS_ALLOWED_EMAILS")),
            access_auth_bypass=access_auth_bypass,
        )


@dataclass(frozen=True)
class AccessIdentity:
    email: str
    subject: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    settings.upload_root.mkdir(parents=True, exist_ok=True)
    jwk_client = (
        None
        if settings.access_auth_bypass
        else PyJWKClient(f"{settings.access_team_domain}/cdn-cgi/access/certs")
    )

    app = FastAPI(
        title="Cookbook upload service",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def secure_api_responses(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def verify_origin(request: Request) -> None:
        if request.headers.get("origin", "").rstrip("/") != settings.allowed_origin:
            raise HTTPException(status_code=403, detail="Request origin is not allowed")

    def require_authenticated(request: Request) -> AccessIdentity:
        if settings.access_auth_bypass:
            return AccessIdentity(email="local-dev", subject="local-dev")

        access_jwt = request.headers.get(ACCESS_JWT_HEADER)
        if not access_jwt:
            raise HTTPException(
                status_code=401, detail="Cloudflare Access authentication required"
            )

        try:
            if jwk_client is None:
                raise RuntimeError("Cloudflare Access validator was not configured")
            signing_key = jwk_client.get_signing_key_from_jwt(access_jwt)
            payload = jwt.decode(
                access_jwt,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.access_aud,
                issuer=settings.access_team_domain,
            )
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=401, detail="Cloudflare Access token is invalid"
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Cloudflare Access token validation is unavailable",
            ) from exc

        email = str(payload.get("email") or "").strip().lower()
        subject = str(payload.get("sub") or "")
        if (
            settings.access_allowed_emails
            and email not in settings.access_allowed_emails
        ):
            raise HTTPException(
                status_code=403, detail="This Cloudflare Access user is not allowed"
            )
        return AccessIdentity(email=email, subject=subject)

    def submission_directory(submission_id: str) -> Path:
        if not SUBMISSION_ID_PATTERN.fullmatch(submission_id):
            raise HTTPException(status_code=404, detail="Submission not found")
        return settings.upload_root / submission_id

    def load_manifest(submission_id: str) -> dict[str, Any]:
        manifest_path = submission_directory(submission_id) / "manifest.json"
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raise HTTPException(status_code=404, detail="Submission not found") from None

    def save_manifest(manifest: dict[str, Any]) -> None:
        target = submission_directory(manifest["id"])
        temporary_path = target / ".manifest.json.tmp"
        temporary_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary_path.replace(target / "manifest.json")

    def public_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
        submission_id = manifest["id"]
        copy = dict(manifest)
        copy["images"] = [
            {
                **image,
                "url": f"/api/submissions/{submission_id}/images/{image['filename']}",
            }
            for image in manifest.get("images", [])
        ]
        return copy

    async def persist_image(
        upload: UploadFile,
        target: Path,
        position: int,
        total_bytes: int,
    ) -> tuple[dict[str, Any], int]:
        original_name = Path(upload.filename or "image").name[:180]
        temporary_path = target / f".{position:02d}.upload"
        image_bytes = 0

        with temporary_path.open("wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                image_bytes += len(chunk)
                total_bytes += len(chunk)
                if image_bytes > MAX_IMAGE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"{original_name} exceeds the 15 MB image limit",
                    )
                if total_bytes > MAX_TOTAL_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="The upload exceeds the 90 MB batch limit",
                    )
                destination.write(chunk)

        if image_bytes == 0:
            raise HTTPException(status_code=400, detail=f"{original_name} is empty")

        try:
            with Image.open(temporary_path) as image:
                image.verify()
                image_format = image.format
            with Image.open(temporary_path) as image:
                width, height = image.size
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise HTTPException(
                status_code=400, detail=f"{original_name} is not a valid image"
            ) from exc

        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=415,
                detail=f"{original_name} must be a JPEG, PNG, or WebP image",
            )

        extension, media_type = ALLOWED_IMAGE_FORMATS[image_format]
        stored_name = f"{position:02d}-{uuid.uuid4().hex[:12]}.{extension}"
        temporary_path.replace(target / stored_name)

        return (
            {
                "filename": stored_name,
                "original_name": original_name,
                "content_type": media_type,
                "size": image_bytes,
                "width": width,
                "height": height,
            },
            total_bytes,
        )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/admin/session")
    async def session_status(
        identity: AccessIdentity = Depends(require_authenticated),
    ) -> dict[str, str | bool]:
        return {"authenticated": True, "email": identity.email}

    @app.post("/api/submissions", status_code=201)
    async def create_submission(
        request: Request,
        title: Annotated[str, Form()],
        images: Annotated[list[UploadFile], File()],
        notes: Annotated[str, Form()] = "",
        _: AccessIdentity = Depends(require_authenticated),
    ) -> dict[str, Any]:
        verify_origin(request)
        title = title.strip()
        notes = notes.strip()
        if not 2 <= len(title) <= 120:
            raise HTTPException(
                status_code=422, detail="Recipe title must be 2–120 characters"
            )
        if len(notes) > 5_000:
            raise HTTPException(
                status_code=422, detail="Notes are limited to 5,000 characters"
            )
        if not 1 <= len(images) <= MAX_IMAGES:
            raise HTTPException(
                status_code=422, detail=f"Select between 1 and {MAX_IMAGES} images"
            )

        submission_id = uuid.uuid4().hex
        target = submission_directory(submission_id)
        target.mkdir(mode=0o700)
        stored_images: list[dict[str, Any]] = []
        total_bytes = 0

        try:
            for position, upload in enumerate(images, start=1):
                stored_image, total_bytes = await persist_image(
                    upload, target, position, total_bytes
                )
                stored_images.append(stored_image)

            manifest = {
                "id": submission_id,
                "title": title,
                "notes": notes,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "images": stored_images,
            }
            save_manifest(manifest)
            return public_manifest(manifest)
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
        finally:
            for upload in images:
                await upload.close()

    @app.get("/api/submissions")
    async def list_submissions(
        _: AccessIdentity = Depends(require_authenticated),
    ) -> dict[str, list[dict[str, Any]]]:
        submissions: list[dict[str, Any]] = []
        for directory in settings.upload_root.iterdir():
            if not directory.is_dir() or not SUBMISSION_ID_PATTERN.fullmatch(
                directory.name
            ):
                continue
            try:
                submissions.append(public_manifest(load_manifest(directory.name)))
            except HTTPException:
                continue
        submissions.sort(key=lambda item: item["uploaded_at"], reverse=True)
        return {"submissions": submissions}

    @app.get("/api/submissions/{submission_id}/images/{filename}")
    async def get_image(
        submission_id: str,
        filename: str,
        _: AccessIdentity = Depends(require_authenticated),
    ) -> FileResponse:
        manifest = load_manifest(submission_id)
        image = next(
            (item for item in manifest["images"] if item["filename"] == filename), None
        )
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        image_path = submission_directory(submission_id) / image["filename"]
        if not image_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(image_path, media_type=image["content_type"])

    @app.delete("/api/submissions/{submission_id}/images/{filename}")
    async def delete_image(
        submission_id: str,
        filename: str,
        request: Request,
        _: AccessIdentity = Depends(require_authenticated),
    ) -> dict[str, Any]:
        verify_origin(request)
        manifest = load_manifest(submission_id)
        image = next(
            (item for item in manifest["images"] if item["filename"] == filename), None
        )
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        (submission_directory(submission_id) / image["filename"]).unlink(missing_ok=True)
        manifest["images"] = [
            item for item in manifest["images"] if item["filename"] != filename
        ]
        save_manifest(manifest)
        return public_manifest(manifest)

    @app.delete("/api/submissions/{submission_id}", status_code=204)
    async def delete_submission(
        submission_id: str,
        request: Request,
        _: AccessIdentity = Depends(require_authenticated),
    ) -> Response:
        verify_origin(request)
        target = submission_directory(submission_id)
        if not (target / "manifest.json").is_file():
            raise HTTPException(status_code=404, detail="Submission not found")
        shutil.rmtree(target)
        return Response(status_code=204)

    return app
