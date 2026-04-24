document.addEventListener("DOMContentLoaded", function () {
  const textarea = document.getElementById("template-text");
  const previewBox = document.getElementById("preview-box");
  const formal = document.getElementById("formal");
  const casual = document.getElementById("casual");
  const toneInput = document.getElementById("tone");

  if (!textarea || !previewBox || !formal || !casual || !toneInput) return;

  const previewUrl = previewBox.dataset.previewUrl;

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.substring(0, name.length + 1) === (name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function syncToneFromHidden() {
    const tone = toneInput.value || "formal";

    if (tone === "formal") {
      formal.checked = true;
      casual.checked = false;
    } else if (tone === "casual") {
      formal.checked = false;
      casual.checked = true;
    }
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderPreview(text) {
    previewBox.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  }

  let debounceTimer = null;

  async function generatePreview() {
    const text = textarea.value.trim();
    const style = toneInput.value || "formal";

    if (!text) {
      renderPreview("");
      return;
    }

    try {
      const response = await fetch(previewUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          text: text,
          style: style
        })
      });

      const data = await response.json();

      if (!response.ok) {
        console.error("preview error:", data);
        renderPreview(text);
        return;
      }

      renderPreview(data.preview_text || text);
    } catch (error) {
      console.error("通信エラー:", error);
      renderPreview(text);
    }
  }

  function requestPreviewWithDelay() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(generatePreview, 400);
  }

  formal.addEventListener("change", function () {
    if (formal.checked) {
      casual.checked = false;
      toneInput.value = "formal";
    } else {
      formal.checked = true;
      toneInput.value = "formal";
    }
    requestPreviewWithDelay();
  });

  casual.addEventListener("change", function () {
    if (casual.checked) {
      formal.checked = false;
      toneInput.value = "casual";
    } else {
      casual.checked = true;
      toneInput.value = "casual";
    }
    requestPreviewWithDelay();
  });

  textarea.addEventListener("input", requestPreviewWithDelay);

  syncToneFromHidden();
  generatePreview();
});