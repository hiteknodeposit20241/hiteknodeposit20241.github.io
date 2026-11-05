(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  var themeColor = document.getElementById("theme-color");

  function sync() {
    var latte = root.getAttribute("data-theme") === "latte";
    toggle.textContent = latte ? "◐ 深色" : "◐ 浅色";
    toggle.setAttribute("aria-label", latte ? "切换到深色配色" : "切换到浅色配色");
    themeColor.setAttribute("content", latte ? "#a7d7d8" : "#14151a");
  }

  toggle.addEventListener("click", function () {
    var latte = root.getAttribute("data-theme") !== "latte";
    if (latte) root.setAttribute("data-theme", "latte"); else root.removeAttribute("data-theme");
    try { localStorage.setItem("graph-theme", latte ? "latte" : "dark"); } catch (e) {}
    if (location.search) history.replaceState(null, "", location.pathname + location.hash);
    sync();
    document.dispatchEvent(new Event("themechange"));
  });
  sync();
})();
