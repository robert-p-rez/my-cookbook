(() => {
  "use strict";

  const root = document.querySelector("[data-upload-app]");
  if (!root) return;

  const authPanel = root.querySelector("[data-auth-panel]");
  const privatePanel = root.querySelector("[data-private-panel]");
  const authStatus = root.querySelector("[data-auth-status]");
  const accessIdentity = root.querySelector("[data-access-identity]");
  const mode = root.dataset.mode;

  const setStatus = (element, message, kind = "") => {
    if (!element) return;
    element.textContent = message;
    element.dataset.kind = kind;
  };

  const errorMessage = async (response) => {
    try {
      const body = await response.json();
      return typeof body.detail === "string" ? body.detail : "The request could not be completed.";
    } catch {
      return "The request could not be completed.";
    }
  };

  const request = async (url, options = {}) => {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    if (response.status === 401 || response.status === 403) showAccessRequired();
    return response;
  };

  const showAccessRequired = (message = "Cloudflare Access authentication is required.") => {
    authPanel.hidden = false;
    privatePanel.hidden = true;
    setStatus(authStatus, message, "error");
  };

  const showPrivatePanel = (email = "") => {
    authPanel.hidden = true;
    privatePanel.hidden = false;
    if (accessIdentity) {
      accessIdentity.textContent = email ? `Signed in with Cloudflare Access as ${email}` : "Signed in with Cloudflare Access";
    }
    if (mode === "admin") loadQueue();
  };

  root.querySelectorAll("[data-retry-auth]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.reload();
    });
  });

  const uploadForm = root.querySelector("[data-upload-form]");
  if (uploadForm) {
    const fileInput = root.querySelector("[data-file-input]");
    const selectedFiles = root.querySelector("[data-selected-files]");
    const uploadStatus = root.querySelector("[data-upload-status]");
    const submitButton = root.querySelector("[data-submit-button]");

    fileInput.addEventListener("change", () => {
      selectedFiles.replaceChildren();
      if (!fileInput.files.length) return;
      const summary = document.createElement("p");
      summary.textContent = `${fileInput.files.length} image${fileInput.files.length === 1 ? "" : "s"} selected`;
      selectedFiles.append(summary);
      const list = document.createElement("ul");
      Array.from(fileInput.files).forEach((file) => {
        const item = document.createElement("li");
        item.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
        list.append(item);
      });
      selectedFiles.append(list);
    });

    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!fileInput.files.length) {
        setStatus(uploadStatus, "Select at least one image.", "error");
        return;
      }
      const files = Array.from(fileInput.files);
      if (files.length > 20) {
        setStatus(uploadStatus, "Select no more than 20 images.", "error");
        return;
      }
      if (files.some((file) => file.size > 15 * 1024 * 1024)) {
        setStatus(uploadStatus, "Each image must be 15 MB or smaller.", "error");
        return;
      }
      if (files.reduce((total, file) => total + file.size, 0) > 90 * 1024 * 1024) {
        setStatus(uploadStatus, "The selected images must total 90 MB or less.", "error");
        return;
      }
      submitButton.disabled = true;
      setStatus(uploadStatus, "Uploading and validating images…");
      try {
        const response = await request("/api/submissions", {
          method: "POST",
          body: new FormData(uploadForm),
        });
        if (!response.ok) {
          setStatus(uploadStatus, await errorMessage(response), "error");
          return;
        }
        const submission = await response.json();
        uploadForm.reset();
        selectedFiles.replaceChildren();
        setStatus(
          uploadStatus,
          `${submission.images.length} image${submission.images.length === 1 ? "" : "s"} sent for review.`,
          "success",
        );
      } catch {
        setStatus(uploadStatus, "The upload failed. Check your connection and try again.", "error");
      } finally {
        submitButton.disabled = false;
      }
    });
  }

  const makeElement = (tag, className, text = "") => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  };

  const formatBytes = (bytes) => {
    if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const reviewQueue = root.querySelector("[data-review-queue]");
  const queueStatus = root.querySelector("[data-queue-status]");

  const renderQueue = (submissions) => {
    reviewQueue.replaceChildren();
    if (!submissions.length) {
      const empty = makeElement("div", "cb-empty-state");
      empty.append(
        makeElement("strong", "", "No submissions waiting"),
        makeElement("p", "", "New recipe images will appear here after upload."),
      );
      reviewQueue.append(empty);
      return;
    }

    submissions.forEach((submission) => {
      const card = makeElement("article", "cb-submission-card");
      const heading = makeElement("header", "cb-submission-card__heading");
      const titleGroup = document.createElement("div");
      titleGroup.append(
        makeElement("span", "cb-submission-card__date", new Date(submission.uploaded_at).toLocaleString()),
        makeElement("h3", "", submission.title),
      );
      const deleteSubmission = makeElement("button", "cb-danger-button", "Delete submission");
      deleteSubmission.type = "button";
      deleteSubmission.addEventListener("click", async () => {
        if (!window.confirm(`Delete “${submission.title}” and all of its images?`)) return;
        deleteSubmission.disabled = true;
        const response = await request(`/api/submissions/${encodeURIComponent(submission.id)}`, {
          method: "DELETE",
        });
        if (response.ok) loadQueue();
        else {
          setStatus(queueStatus, await errorMessage(response), "error");
          deleteSubmission.disabled = false;
        }
      });
      heading.append(titleGroup, deleteSubmission);
      card.append(heading);

      if (submission.notes) {
        card.append(makeElement("p", "cb-submission-card__notes", submission.notes));
      }

      const imageGrid = makeElement("div", "cb-upload-image-grid");
      submission.images.forEach((image) => {
        const figure = document.createElement("figure");
        const link = document.createElement("a");
        link.href = image.url;
        link.target = "_blank";
        link.rel = "noopener";
        link.title = "Open original image";
        const preview = document.createElement("img");
        preview.src = image.url;
        preview.alt = image.original_name;
        preview.loading = "lazy";
        link.append(preview);

        const caption = document.createElement("figcaption");
        const details = document.createElement("div");
        details.append(
          makeElement("strong", "", image.original_name),
          makeElement("span", "", `${image.width}×${image.height} · ${formatBytes(image.size)}`),
        );
        const deleteImage = makeElement("button", "cb-image-delete", "Delete");
        deleteImage.type = "button";
        deleteImage.addEventListener("click", async () => {
          if (!window.confirm(`Delete ${image.original_name}?`)) return;
          deleteImage.disabled = true;
          const response = await request(image.url, { method: "DELETE" });
          if (response.ok) loadQueue();
          else {
            setStatus(queueStatus, await errorMessage(response), "error");
            deleteImage.disabled = false;
          }
        });
        caption.append(details, deleteImage);
        figure.append(link, caption);
        imageGrid.append(figure);
      });
      card.append(imageGrid);
      reviewQueue.append(card);
    });
  };

  async function loadQueue() {
    if (!reviewQueue) return;
    setStatus(queueStatus, "Loading submissions…");
    try {
      const response = await request("/api/submissions");
      if (!response.ok) {
        setStatus(queueStatus, await errorMessage(response), "error");
        return;
      }
      const body = await response.json();
      setStatus(queueStatus, `${body.submissions.length} submission${body.submissions.length === 1 ? "" : "s"}`);
      renderQueue(body.submissions);
    } catch {
      setStatus(queueStatus, "The review queue is unavailable.", "error");
    }
  }

  const refreshButton = root.querySelector("[data-refresh]");
  if (refreshButton) refreshButton.addEventListener("click", loadQueue);

  request("/api/admin/session")
    .then(async (response) => {
      if (!response.ok) {
        showAccessRequired(await errorMessage(response));
        return null;
      }
      return response.json();
    })
    .then((session) => {
      if (!session) return;
      if (session.authenticated) showPrivatePanel(session.email);
      else showAccessRequired();
    })
    .catch(() => {
      showAccessRequired("The upload service is unavailable.");
    });
})();
