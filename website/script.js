// NautiCAI — minimal site script

// ═══ Demo link: point to signup gate (demo.html) — app opens only after signup
(function () {
  document.querySelectorAll(".demo-link").forEach(function (a) {
    a.href = "demo.html";
  });
})();

// ═══ Alert bar: dismiss and hide (persist in session)
(function () {
  var bar = document.getElementById("alert-bar");
  var dismiss = document.getElementById("alert-dismiss");
  if (bar && dismiss) {
    if (sessionStorage.getItem("nauticai-alert-dismissed") === "1") {
      bar.classList.add("hidden");
    }
    dismiss.addEventListener("click", function () {
      bar.classList.add("hidden");
      sessionStorage.setItem("nauticai-alert-dismissed", "1");
    });
  }
})();

// ═══ Toast: show one welcome toast on first visit (session)
function showToast(message, durationMs) {
  durationMs = durationMs || 5000;
  var container = document.getElementById("toast-container");
  if (!container) return;
  if (sessionStorage.getItem("nauticai-toast-shown") === "1") return;
  sessionStorage.setItem("nauticai-toast-shown", "1");

  var toast = document.createElement("div");
  toast.className = "toast toast--new";
  toast.setAttribute("role", "alert");
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(function () {
    toast.classList.add("toast-out");
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 320);
  }, durationMs);
}

// Hero background video: play when loaded, hide on error (fallback to gradient)
(function () {
  var wrap = document.querySelector(".hero-video-wrap");
  var video = document.querySelector(".hero-video");
  if (!wrap || !video) return;
  video.addEventListener("loadeddata", function () {
    video.play().catch(function () {});
  });
  video.addEventListener("error", function () {
    wrap.classList.add("hero-video-wrap--hidden");
  });
})();

// Show welcome toast after a short delay (only once per session)
setTimeout(function () {
  showToast("Book a demo — see underwater inspection in action.", 6000);
}, 1800);

// ═══ Scroll reveal (Intersection Observer)
(function () {
  var reveals = document.querySelectorAll(".reveal");
  if (!reveals.length) return;
  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
  );
  reveals.forEach(function (el) {
    observer.observe(el);
  });
})();

// Floating CTA: show after user scrolls past hero
(function () {
  var floatCta = document.getElementById("float-cta");
  if (!floatCta) return;
  function checkScroll() {
    var hero = document.querySelector(".hero");
    if (!hero) return;
    var heroBottom = hero.getBoundingClientRect().bottom;
    if (heroBottom < 100) {
      floatCta.classList.add("visible");
    } else {
      floatCta.classList.remove("visible");
    }
  }
  window.addEventListener("scroll", checkScroll, { passive: true });
  window.addEventListener("resize", checkScroll);
})();

// Nav: add class when scrolled (for border/background)
(function () {
  var nav = document.querySelector(".nav");
  if (!nav) return;
  function onScroll() {
    if (window.scrollY > 20) nav.classList.add("nav-scrolled");
    else nav.classList.remove("nav-scrolled");
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
})();

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// API status (footer) — ping backend health, show latency
(function () {
  var el = document.getElementById("api-status");
  if (!el) return;
  var apiUrl = document.body.getAttribute("data-api-url");
  if (!apiUrl && (window.location.port === "8080" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"))) {
    apiUrl = "http://localhost:8000";
  }
  if (!apiUrl) {
    el.textContent = "API: Configure data-api-url for status.";
    return;
  }
  function check() {
    var start = performance.now();
    fetch(apiUrl + "/api/health", { method: "GET", mode: "cors" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var ms = Math.round(performance.now() - start);
        el.textContent = "API " + (d.status === "ok" ? "Live" : "Degraded") + " · " + (d.model || "—") + " · " + ms + " ms";
        el.classList.add("api-live");
      })
      .catch(function () {
        el.textContent = "API offline";
        el.classList.remove("api-live");
      });
  }
  check();
  setInterval(check, 60000);
})();

// Contact form — mailto fallback (works without Formspree)
document.getElementById('contact-form')?.addEventListener('submit', function (e) {
  e.preventDefault();
  const form = e.target;
  const mailto = form.dataset.mailto || 'contact@nauticai-ai.com';
  const name = (form.querySelector('[name="name"]')?.value || '').trim();
  const email = (form.querySelector('[name="email"]')?.value || '').trim();
  const company = (form.querySelector('[name="company"]')?.value || '').trim();
  const message = (form.querySelector('[name="message"]')?.value || '').trim();
  const body = [
    'Name: ' + name,
    'Email: ' + email,
    company ? 'Company: ' + company : '',
    '',
    message
  ].filter(Boolean).join('%0D%0A');
  const subject = encodeURIComponent('NautiCAI — Contact request from ' + (name || 'website'));
  window.location.href = 'mailto:' + mailto + '?subject=' + subject + '&body=' + body;
});
