console.log("✅ ai_generate.js loaded");

function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

function bindGenerateButton() {
  const btn = document.getElementById("ai-generate-btn");
  console.log("🔎 btn:", btn);

  if (!btn) return;

  // 二重登録防止
  if (btn.dataset.bound === "1") return;
  btn.dataset.bound = "1";

  btn.addEventListener("click", onGenerateClick);
  console.log("✅ bound click handler");
}

// DOMContentLoadedを待つ版 + 念のため即時実行もする（どちらでも拾える）
document.addEventListener("DOMContentLoaded", bindGenerateButton);
bindGenerateButton();

async function onGenerateClick() {
  console.log("✅ onGenerateClick start");

  const btn = document.getElementById("ai-generate-btn");
  const generateUrl = btn?.dataset?.generateUrl || "/ai/generate/";
  const memoEl = document.getElementById("ai-memo");
  const userPrompt = memoEl?.value?.trim() || "";

  console.log("🔎 generateUrl:", generateUrl);
  console.log("🔎 prompt:", userPrompt);

  if (!userPrompt) {
    alert("素材入力を入力してください");
    return;
  }

  try {
    const res = await fetch(generateUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ prompt: userPrompt }),
    });

    console.log("✅ fetch done:", res.status);

    const data = await res.json();
    console.log("✅ response json:", data);

    if (!res.ok) {
      alert(data.error || "AI生成に失敗しました");
      return;
    }

    // Responseが {today_work, reflection, tomorrow_plan, note, warning} の形
    const todayWork = data.today_work || "";
    const reflection = data.reflection || "";
    const tomorrowPlan = data.tomorrow_plan || "";
    const note = data.note || "";
    const warning = data.warning || "";

    const elToday = document.getElementById("id_today_work");
    const elReflection = document.getElementById("id_reflection");
    const elTomorrow = document.getElementById("id_tomorrow_plan");
    const elNote = document.getElementById("id_note");

    console.log("🔎 fields:", {
      today: !!elToday,
      reflection: !!elReflection,
      tomorrow: !!elTomorrow,
      note: !!elNote,
    });

    if (elToday) elToday.value = todayWork;
    if (elReflection) elReflection.value = reflection;
    if (elTomorrow) elTomorrow.value = tomorrowPlan;
    if (elNote) elNote.value = note;

    if (warning) console.warn("AI warning:", warning);
    console.log("✅ filled fields");
  } catch (e) {
    console.error(e);
    alert("通信エラーが発生しました");
  }
}