---
title: Submit a Recipe
hide:
  - toc
---

# Submit a Recipe

<p class="cb-page-intro">
Have a recipe card, cookbook clipping, or handwritten favorite to add? Upload
clear photos here and they will be held privately for review before anything is
published to the cookbook.
</p>

<div class="cb-upload-app" data-upload-app data-mode="submit">
  <section class="cb-auth-panel" data-auth-panel hidden>
    <div>
      <p class="cb-eyebrow">Private submissions</p>
      <h2>Cloudflare Access required</h2>
      <p>This upload area is protected by Cloudflare Access. Open this page through the production domain and sign in with an allowed account.</p>
    </div>
    <div class="cb-access-actions">
      <button class="md-button md-button--primary" type="button" data-retry-auth>Check access again</button>
      <p class="cb-form-status" data-auth-status role="status"></p>
    </div>
  </section>

  <section class="cb-upload-panel" data-private-panel hidden>
    <div class="cb-panel-heading">
      <div>
        <p class="cb-eyebrow">New submission</p>
        <h2>Upload recipe photos</h2>
      </div>
      <p class="cb-access-identity" data-access-identity></p>
    </div>
    <form data-upload-form>
      <label for="recipe-title">Recipe name</label>
      <input id="recipe-title" name="title" type="text" minlength="2" maxlength="120" placeholder="Grandma's apple pie" required>

      <label for="recipe-notes">Notes for the reviewer <span>(optional)</span></label>
      <textarea id="recipe-notes" name="notes" rows="4" maxlength="5000" placeholder="Photo order, missing steps, family notes, or anything else that helps."></textarea>

      <label class="cb-file-picker" for="recipe-images">
        <span class="cb-file-picker__icon" aria-hidden="true">＋</span>
        <strong>Choose recipe images</strong>
        <span>JPEG, PNG, or WebP · up to 20 images · 15 MB each · 90 MB total</span>
      </label>
      <input class="cb-visually-hidden" id="recipe-images" name="images" type="file" accept="image/jpeg,image/png,image/webp" multiple required data-file-input>
      <div class="cb-selected-files" data-selected-files aria-live="polite"></div>

      <div class="cb-form-footer">
        <p>Uploads stay private until they are reviewed and manually added to the cookbook.</p>
        <button class="md-button md-button--primary" type="submit" data-submit-button>Send for review</button>
      </div>
      <p class="cb-form-status" data-upload-status role="status"></p>
    </form>
  </section>
</div>
