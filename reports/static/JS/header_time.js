document.addEventListener("DOMContentLoaded", function () {
  const target = document.getElementById("realtime-datetime");
  if (!target) return;

  const weekDays = ["日", "月", "火", "水", "木", "金", "土"];

  function updateDateTime() {
    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const date = String(now.getDate()).padStart(2, "0");
    const day = weekDays[now.getDay()];
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");

    target.textContent = `${year}/${month}/${date}(${day}) ${hours}:${minutes}:${seconds}`;
  }

  updateDateTime();
  setInterval(updateDateTime, 1000);
});