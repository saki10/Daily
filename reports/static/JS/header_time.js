document.addEventListener("DOMContentLoaded", function () {
  function updateDateTime() {
    const target = document.getElementById("realtime-datetime");
    if (!target) return;

    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hour = String(now.getHours()).padStart(2, "0");
    const minute = String(now.getMinutes()).padStart(2, "0");

    target.textContent = `${year}/${month}/${day} ${hour}:${minute}`;
  }

  updateDateTime();
  setInterval(updateDateTime, 1000);
});
