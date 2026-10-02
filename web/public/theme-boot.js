// Applies the saved (or ?theme=) colour theme before first paint, so there is no flash.
try {
  var q = new URLSearchParams(location.search).get("theme");
  var t = q === "light" || q === "dark" ? q : localStorage.getItem("cc-theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
} catch {}
