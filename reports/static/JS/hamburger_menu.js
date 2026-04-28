document.addEventListener("DOMContentLoaded", function () {
  const hamburgerBtn = document.getElementById("hamburgerBtn");
  const sidebar = document.getElementById("sidebar");
  const sidebarOverlay = document.getElementById("sidebarOverlay");

  if (!hamburgerBtn || !sidebar) {
    return;
  }

  function openMenu() {
    document.body.classList.add("is-menu-open");
    hamburgerBtn.setAttribute("aria-expanded", "true");
    hamburgerBtn.setAttribute("aria-label", "メニューを閉じる");
  }

  function closeMenu() {
    document.body.classList.remove("is-menu-open");
    hamburgerBtn.setAttribute("aria-expanded", "false");
    hamburgerBtn.setAttribute("aria-label", "メニューを開く");
  }

  hamburgerBtn.addEventListener("click", function () {
    if (document.body.classList.contains("is-menu-open")) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", closeMenu);
  }

  sidebar.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", closeMenu);
  });
});