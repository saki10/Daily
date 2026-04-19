document.addEventListener("DOMContentLoaded", function () {
  console.log("✅ ai_generate.js loaded");

  const btn = document.getElementById("ai-generate-btn");
  if (!btn) return;

  if (btn.dataset.bound === "1") return;
  btn.dataset.bound = "1";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  btn.addEventListener("click", async function (e) {
    e.preventDefault();
    console.log("✅ onGenerateClick start");

    const memoEl = document.getElementById("ai-memo");
    const toneToggle = document.getElementById("tone-toggle");

    const generateUrl = btn.dataset.generateUrl || "/ai/generate/";
    const tone = toneToggle?.checked ? "casual" : "formal";
    const userPrompt = memoEl?.value.trim() || "";

    console.log("🔎 generateUrl:", generateUrl);
    console.log("🔎 prompt:", userPrompt);
    console.log("🔎 tone:", tone);

    if (!userPrompt) {
      alert("素材入力を入力してください");
      return;
    }

    btn.disabled = true;
    btn.textContent = "生成中...";

    try {
      const res = await fetch(generateUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          prompt: userPrompt,
          tone: tone,
        }),
      });

      console.log("✅ fetch done:", res.status);

      const data = await res.json();
      console.log("✅ response json:", data);

      if (!res.ok) {
        alert(data.error || "AI生成に失敗しました");
        return;
      }

      const todayWork = data.today_work || "";
      const reflection = data.reflection || "";
      const tomorrowPlan = data.tomorrow_plan || "";
      const note = data.note || "";
      const warning = data.warning || "";

      const elToday = document.getElementById("id_today_work");
      const elReflection = document.getElementById("id_reflection");
      const elTomorrow = document.getElementById("id_tomorrow_plan");
      const elNote = document.getElementById("id_note");

      if (elToday) elToday.value = todayWork;
      if (elReflection) elReflection.value = reflection;
      if (elTomorrow) elTomorrow.value = tomorrowPlan;
      if (elNote) elNote.value = note;

      if (warning) console.warn("AI warning:", warning);
      console.log("✅ filled fields");

      if (window.reportAutosaveNow) {
        window.reportAutosaveNow();
      }
    } catch (e) {
      console.error("❌ 通信エラー:", e);
      alert("通信エラーが発生しました");
    } finally {
      btn.disabled = false;
      btn.textContent = "AIで文章生成";
    }
  });

  console.log("✅ bound click handler");
});