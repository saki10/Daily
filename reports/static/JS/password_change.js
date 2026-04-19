document.addEventListener("DOMContentLoaded", function () {
  const oldPassword = document.getElementById("id_old_password");
  const newPassword1 = document.getElementById("id_new_password1");
  const newPassword2 = document.getElementById("id_new_password2");

  if (oldPassword) {
    oldPassword.placeholder = "現在のパスワードを入力";
  }

  if (newPassword1) {
    newPassword1.placeholder = "新しいパスワードを入力";
  }

  if (newPassword2) {
    newPassword2.placeholder = "新しいパスワード（確認）を入力";
  }

  const errorElements = document.querySelectorAll(".js-password-error");
  const errorMessages = [];

  errorElements.forEach(function (element) {
    const text = element.textContent.trim();
    if (text && !errorMessages.includes(text)) {
      errorMessages.push(text);
    }
  });

  if (errorMessages.length > 0) {
    alert(errorMessages.join("\n"));
  }
});