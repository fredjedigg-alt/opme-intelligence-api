/* ATLAS · utilitários compartilhados: formatação pt-BR, origem do lead e envio do formulário (Netlify Forms). */
(function () {
  "use strict";

  var brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  var num0 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
  var num1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

  function val(id) {
    var el = document.getElementById(id);
    if (!el) return 0;
    var v = parseFloat(String(el.value).replace(",", "."));
    return isFinite(v) ? v : 0;
  }
  function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
  function set(id, text) { var el = document.getElementById(id); if (el) el.textContent = text; }

  // Origem do lead: ?o=ig-glosa vira campo oculto "origem". Sem cookies, sem rastreador.
  function origem() {
    try {
      var o = new URLSearchParams(window.location.search).get("o") || "";
      return o.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 40) || "direto";
    } catch (e) { return "direto"; }
  }

  // Repassa ?o= para os links internos (hub → calculadora), para não perder a origem.
  function carryOrigin() {
    var o = origem();
    if (o === "direto") return;
    var links = document.querySelectorAll("a[data-carry]");
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      try {
        var u = new URL(a.getAttribute("href"), window.location.href);
        u.searchParams.set("o", o);
        a.setAttribute("href", u.pathname + u.search + u.hash);
      } catch (e) { /* mantém o link original */ }
    }
  }

  function encode(form) {
    var data = new FormData(form);
    return new URLSearchParams(data).toString();
  }

  // getSummary: função da calculadora que devolve o texto do resultado no momento do envio.
  function bindLeadForm(formId, getSummary) {
    var form = document.getElementById(formId);
    if (!form) return;
    var msg = form.querySelector(".form-msg");
    var btn = form.querySelector("button[type=submit]");
    var origemEl = form.querySelector("input[name=origem]");
    if (origemEl) origemEl.value = origem();

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (msg) { msg.textContent = ""; msg.className = "form-msg"; }
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      var resumo = form.querySelector("textarea[name=resumo]");
      if (resumo && typeof getSummary === "function") resumo.value = getSummary();
      if (btn) { btn.disabled = true; btn.textContent = "Enviando…"; }

      fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: encode(form)
      }).then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        var done = document.getElementById(formId + "-done");
        form.hidden = true;
        if (done) { done.hidden = false; done.focus(); }
      }).catch(function () {
        if (msg) {
          msg.textContent = "Não foi possível enviar agora. Verifique a conexão e tente de novo.";
          msg.className = "form-msg err";
        }
        if (btn) { btn.disabled = false; btn.textContent = btn.getAttribute("data-label") || "Enviar"; }
      });
    });
  }

  // Liga todos os inputs de um container a uma função de recálculo.
  function onInputs(root, fn) {
    var el = typeof root === "string" ? document.getElementById(root) : root;
    if (!el) return;
    el.addEventListener("input", fn);
    el.addEventListener("change", fn);
  }

  window.Atlas = {
    brl: function (v) { return brl.format(Math.round(v || 0)); },
    n0: function (v) { return num0.format(v || 0); },
    n1: function (v) { return num1.format(v || 0); },
    pct: function (v) { return num1.format((v || 0) * 100) + "%"; },
    val: val, clamp: clamp, set: set,
    origem: origem, carryOrigin: carryOrigin,
    bindLeadForm: bindLeadForm, onInputs: onInputs
  };

  document.addEventListener("DOMContentLoaded", carryOrigin);
})();
