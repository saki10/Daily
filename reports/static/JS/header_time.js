document.addEventListener("DOMContentLoaded", function () {
  const target = document.getElementById("realtime-datetime");
  if (!target) return;

  function updateDateTime() {
    const now = new Date();

    const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const weekday = weekdays[now.getDay()];
    const hour = String(now.getHours()).padStart(2, "0");
    const minute = String(now.getMinutes()).padStart(2, "0");
    const second = String(now.getSeconds()).padStart(2, "0");

    target.textContent = `${year}/${month}/${day}（${weekday}） ${hour}:${minute}:${second}`;
  }

  updateDateTime();
  setInterval(updateDateTime, 1000);
});