const form = document.getElementById("loginForm");
const button = document.getElementById("loginButton");
const errorBox = document.getElementById("loginError");

async function alreadySignedIn() {
  try {
    const response = await fetch("/api/v1/auth/me", {credentials:"same-origin"});
    if (response.ok) location.replace("/");
  } catch (_) {}
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  errorBox.textContent = "";
  button.disabled = true;
  button.textContent = "Signing in…";

  try {
    const response = await fetch("/api/v1/auth/login", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      credentials:"same-origin",
      body:JSON.stringify({
        username:document.getElementById("username").value.trim(),
        password:document.getElementById("password").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.error?.message || data?.detail || "Sign in failed");
    localStorage.removeItem("apiToken");
    location.replace("/");
  } catch (error) {
    errorBox.textContent = error.message;
    button.disabled = false;
    button.textContent = "Sign in";
  }
});

alreadySignedIn();
