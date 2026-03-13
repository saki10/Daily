(function () {
  const el = document.getElementById("realtime-datetime");
  if (!el) return;

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function render() {
    const now = new Date();

    const datePart = new Intl.DateTimeFormat("ja-JP", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "long",
      day: "2-digit",
      weekday: "long",
    }).format(now);

    const h = pad2(now.getHours());
    const m = pad2(now.getMinutes());
    const s = pad2(now.getSeconds());
    const timePart = `${h}:${m}:${s}`;

    el.textContent = `${datePart}  ${timePart}`;
  }

  render();
  setInterval(render, 1000);
})();

