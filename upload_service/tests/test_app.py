from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from upload_service.app import Settings, create_app


ORIGIN = "https://gabbys-cookbook.perezdev.com"


def image_bytes(color: str = "tomato") -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), color=color).save(output, format="JPEG")
    return output.getvalue()


def authenticated_client(tmp_path) -> TestClient:
    settings = Settings(
        upload_root=tmp_path,
        allowed_origin=ORIGIN,
    )
    return TestClient(create_app(settings), base_url=ORIGIN)


def test_session_uses_trusted_proxy_identity(tmp_path) -> None:
    client = authenticated_client(tmp_path)

    response = client.get(
        "/api/admin/session",
        headers={"Cf-Access-Authenticated-User-Email": "gabby@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "email": "gabby@example.com"}


def test_batch_upload_review_and_delete(tmp_path) -> None:
    client = authenticated_client(tmp_path)
    response = client.post(
        "/api/submissions",
        data={"title": "Test recipe", "notes": "Handwritten card, front and back"},
        files=[
            ("images", ("front.jpg", image_bytes("tomato"), "image/jpeg")),
            ("images", ("back.jpg", image_bytes("gold"), "image/jpeg")),
        ],
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 201, response.text
    submission = response.json()
    assert len(submission["images"]) == 2

    queue = client.get("/api/submissions")
    assert queue.status_code == 200
    assert queue.json()["submissions"][0]["title"] == "Test recipe"

    image = client.get(submission["images"][0]["url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"

    removed_image = client.delete(
        submission["images"][0]["url"], headers={"Origin": ORIGIN}
    )
    assert removed_image.status_code == 200
    assert len(removed_image.json()["images"]) == 1

    removed_submission = client.delete(
        f"/api/submissions/{submission['id']}", headers={"Origin": ORIGIN}
    )
    assert removed_submission.status_code == 204
    assert client.get("/api/submissions").json()["submissions"] == []


def test_non_image_upload_is_rejected_and_removed(tmp_path) -> None:
    client = authenticated_client(tmp_path)
    response = client.post(
        "/api/submissions",
        data={"title": "Not an image"},
        files=[("images", ("fake.jpg", b"not actually an image", "image/jpeg"))],
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []
