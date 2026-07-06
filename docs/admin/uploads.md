---
title: Review Uploads
hide:
  - toc
---

# Review Uploads

<p class="cb-page-intro">
Private review queue for submitted recipe images. Inspect the originals, remove
individual images, and delete a submission after the recipe has been published.
</p>

<div class="cb-upload-app" data-upload-app data-mode="admin">
  <section class="cb-auth-panel" data-auth-panel hidden>
    <div>
      <p class="cb-eyebrow">Admin access</p>
      <h2>Cloudflare Access required</h2>
      <p>This review queue is protected by Cloudflare Access. Open this page through the production domain and sign in with an allowed admin account.</p>
    </div>
    <div class="cb-access-actions">
      <button class="md-button md-button--primary" type="button" data-retry-auth>Check access again</button>
      <p class="cb-form-status" data-auth-status role="status"></p>
    </div>
  </section>

  <section class="cb-review-panel" data-private-panel hidden>
    <div class="cb-panel-heading">
      <div>
        <p class="cb-eyebrow">Private queue</p>
        <h2>Recipe submissions</h2>
      </div>
      <div class="cb-panel-actions">
        <p class="cb-access-identity" data-access-identity></p>
        <button class="cb-link-button" type="button" data-refresh>Refresh</button>
      </div>
    </div>
    <p class="cb-form-status" data-queue-status role="status"></p>
    <div class="cb-review-queue" data-review-queue></div>
  </section>
</div>
