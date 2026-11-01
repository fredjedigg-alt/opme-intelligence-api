/* Calculadora de materiais e OPME: peso do material por procedimento e dispersão do preço de compra. */
(function () {
  "use strict";
  var A = window.Atlas;
  var MAX_ROWS = 12;

  var procs = [
    { nome: "Videoartroscopia de joelho", receb: 4200, mat: 2300, qtd: 6 },
    { nome: "Infiltração articular", receb: 650, mat: 180, qtd: 40 },
    { nome: "Consulta ortopédica", receb: 280, mat: 8, qtd: 220 }
  ];
  var buys = [
    { preco: 1180, qtd: 4 },
    { preco: 1450, qtd: 3 },
    { preco: 980, qtd: 2 },
    { preco: 1620, qtd: 2 }
  ];

  function num(v) { var n = parseFloat(String(v).replace(",", ".")); return isFinite(n) && n > 0 ? n : 0; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------- linhas editáveis ---------- */
  function procRowHtml(p, i) {
    return '<div class="row-card" data-i="' + i + '">' +
      '<div class="row-top"><label class="hp" for="pn' + i + '">Nome do procedimento</label>' +
      '<input id="pn' + i + '" type="text" data-k="nome" value="' + esc(p.nome) + '" placeholder="Nome do procedimento">' +
      '<button type="button" class="btn-x" data-del="' + i + '" aria-label="Remover ' + esc(p.nome || "procedimento") + '">×</button></div>' +
      '<div class="row-grid">' +
      '<div class="field"><label for="pr' + i + '">Valor recebido</label><div class="input-unit"><span>R$</span><input id="pr' + i + '" type="number" inputmode="decimal" min="0" data-k="receb" value="' + p.receb + '"></div></div>' +
      '<div class="field"><label for="pm' + i + '">Custo de material</label><div class="input-unit"><span>R$</span><input id="pm' + i + '" type="number" inputmode="decimal" min="0" data-k="mat" value="' + p.mat + '"></div></div>' +
      '<div class="field"><label for="pq' + i + '">Quantidade</label><div class="input-unit"><input id="pq' + i + '" type="number" inputmode="numeric" min="0" data-k="qtd" value="' + p.qtd + '"><span>/mês</span></div></div>' +
      '</div></div>';
  }
  function buyRowHtml(b, i) {
    return '<div class="row-card" data-i="' + i + '">' +
      '<div class="row-top"><strong>Compra ' + (i + 1) + '</strong><span style="flex:1"></span>' +
      '<button type="button" class="btn-x" data-del="' + i + '" aria-label="Remover compra ' + (i + 1) + '">×</button></div>' +
      '<div class="row-grid">' +
      '<div class="field"><label for="bp' + i + '">Preço unitário</label><div class="input-unit"><span>R$</span><input id="bp' + i + '" type="number" inputmode="decimal" min="0" data-k="preco" value="' + b.preco + '"></div></div>' +
      '<div class="field"><label for="bq' + i + '">Quantidade</label><div class="input-unit"><input id="bq' + i + '" type="number" inputmode="numeric" min="0" data-k="qtd" value="' + b.qtd + '"><span>un.</span></div></div>' +
      '</div></div>';
  }

  function drawRows(id, list, fn) {
    document.getElementById(id).innerHTML = list.map(fn).join("");
  }

  function wireRows(id, list, addId, blank, rowFn, onChange) {
    var root = document.getElementById(id);
    root.addEventListener("input", function (ev) {
      var t = ev.target, card = t.closest(".row-card");
      if (!card || !t.dataset.k) return;
      var row = list[+card.dataset.i];
      row[t.dataset.k] = t.dataset.k === "nome" ? t.value : num(t.value);
      onChange();
    });
    root.addEventListener("click", function (ev) {
      var d = ev.target.closest("[data-del]");
      if (!d) return;
      list.splice(+d.dataset.del, 1);
      drawRows(id, list, rowFn);
      onChange();
    });
    document.getElementById(addId).addEventListener("click", function () {
      if (list.length >= MAX_ROWS) return;
      list.push(blank());
      drawRows(id, list, rowFn);
      var inputs = root.querySelectorAll(".row-card:last-child input");
      if (inputs[0]) inputs[0].focus();
      onChange();
    });
  }

  /* ---------- modo 1: procedimentos ---------- */
  function computeProcs() {
    var rec = 0, mat = 0, rows = [];
    procs.forEach(function (p) {
      var r = num(p.receb), m = num(p.mat), q = num(p.qtd);
      rec += r * q; mat += m * q;
      rows.push({ nome: p.nome || "Sem nome", pct: r > 0 ? m / r : 0, sobra: r - m, sobraMes: (r - m) * q, q: q, r: r, m: m });
    });
    rows.sort(function (a, b) { return b.pct - a.pct; });
    return { rec: rec, mat: mat, pct: rec > 0 ? mat / rec : 0, rows: rows };
  }

  function renderProcs() {
    var c = computeProcs();
    A.set("p-receita", A.brl(c.rec));
    A.set("p-pct", A.pct(c.pct));
    A.set("p-mat", A.brl(c.mat) + " por mês em material, " + A.brl(c.mat * 12) + " por ano.");
    document.getElementById("p-table").innerHTML = c.rows.map(function (r, i) {
      return '<tr' + (i === 0 && r.pct > 0 ? ' class="top"' : "") + '><td>' + esc(r.nome) + '</td><td class="r">' + A.pct(r.pct) +
        '</td><td class="r">' + A.brl(r.sobra) + '</td><td class="r">' + A.brl(r.sobraMes) + '</td></tr>';
    }).join("") || '<tr><td colspan="4">Adicione um procedimento.</td></tr>';

    var top = c.rows[0], txt;
    if (!top || top.r <= 0) txt = "Informe valor recebido e custo de material para ver a leitura.";
    else if (top.sobra < 0) txt = top.nome + " custa mais em material do que recebe. Cada unidade feita tira " + A.brl(-top.sobra) + " do caixa antes de pagar qualquer outra coisa.";
    else if (top.pct >= 0.5) txt = "Mais da metade do valor de " + top.nome + " sai em material (" + A.pct(top.pct) + "). Antes de fazer mais dele, vale conferir o preço de compra e se o material pode ser cobrado à parte quando o contrato com o convênio permite.";
    else {
      var porSobra = c.rows.slice().sort(function (a, b) { return b.sobraMes - a.sobraMes; })[0];
      txt = "O material pesa mais em " + top.nome + " (" + A.pct(top.pct) + "), mas quem mais deixa dinheiro no mês é " + porSobra.nome + " (" + A.brl(porSobra.sobraMes) + "). O que ocupa a agenda deveria seguir essa ordem.";
    }
    document.getElementById("p-insight").textContent = txt;
  }

  /* ---------- modo 2: compras ---------- */
  function median(arr) {
    var a = arr.slice().sort(function (x, y) { return x - y; }), n = a.length;
    if (!n) return 0;
    return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2;
  }

  function computeBuys() {
    var valid = buys.filter(function (b) { return num(b.preco) > 0 && num(b.qtd) > 0; });
    var precos = valid.map(function (b) { return num(b.preco); });
    var periodo = Math.max(1, A.val("periodo"));
    var gasto = 0, q = 0;
    valid.forEach(function (b) { gasto += num(b.preco) * num(b.qtd); q += num(b.qtd); });
    var min = precos.length ? Math.min.apply(null, precos) : 0;
    var max = precos.length ? Math.max.apply(null, precos) : 0;
    var med = median(precos);
    var acima = 0;
    valid.forEach(function (b) { var p = num(b.preco); if (p > med) acima += (p - med) * num(b.qtd); });
    var teto = gasto - min * q;
    return { n: valid.length, gasto: gasto, q: q, min: min, max: max, med: med, periodo: periodo,
      disp: min > 0 ? max / min - 1 : 0, acima: acima, acimaAno: acima / periodo * 12, tetoAno: teto / periodo * 12,
      item: (document.getElementById("item").value || "o item").trim() };
  }

  function renderBuys() {
    var c = computeBuys();
    A.set("b-gasto", A.brl(c.gasto));
    A.set("b-faixa", c.n ? A.n0(c.q) + " unidades de " + c.item + " em " + A.n0(c.periodo) + " " + (c.periodo === 1 ? "mês" : "meses") + "." : "Lance ao menos uma compra.");
    A.set("b-eco-ano", A.brl(c.acimaAno));
    A.set("b-eco-det", "Pago acima do preço mediano das suas próprias compras, projetado para 12 meses.");
    A.set("b-minmax", c.n ? A.brl(c.min) + " a " + A.brl(c.max) : "—");
    A.set("b-disp", c.n > 1 ? A.pct(c.disp) : "—");
    A.set("b-med", c.n ? A.brl(c.med) : "—");
    A.set("b-eco", A.brl(c.acima));
    A.set("b-teto", A.brl(c.tetoAno));
    var txt;
    if (c.n < 2) txt = "Com duas ou mais compras dá para ver quanto o preço do mesmo item varia.";
    else if (c.disp >= 0.3) txt = "O mesmo item foi comprado com " + A.pct(c.disp) + " de diferença entre o maior e o menor preço. Hipótese a testar: compra sem tabela de referência, por urgência ou por fornecedor indicado sem cotação.";
    else txt = "A variação de preço está contida (" + A.pct(c.disp) + "). O próximo passo é saber se a sua mediana está alta frente ao mercado: é aí que entra a comparação com compras públicas.";
    document.getElementById("b-insight").textContent = txt;
  }

  /* ---------- abas ---------- */
  var current = "proc";
  function showTab(name) {
    current = name;
    ["proc", "compra"].forEach(function (n) {
      document.getElementById("tab-" + n).setAttribute("aria-selected", n === name ? "true" : "false");
      document.getElementById("view-" + n).hidden = n !== name;
    });
    if (window.history && window.history.replaceState) {
      try { window.history.replaceState(null, "", window.location.pathname + window.location.search + (name === "compra" ? "#compras" : "")); } catch (e) {}
    }
  }

  function summary() {
    var p = computeProcs(), b = computeBuys();
    var out = ["CALCULADORA DE MATERIAIS E OPME", "", "PROCEDIMENTOS (receita/mês " + A.brl(p.rec) + ", material " + A.pct(p.pct) + "):"];
    p.rows.forEach(function (r) {
      out.push("- " + r.nome + ": recebe " + A.brl(r.r) + ", material " + A.brl(r.m) + " (" + A.pct(r.pct) + "), " + A.n0(r.q) + "/mês");
    });
    out.push("", "COMPRAS de " + b.item + " em " + A.n0(b.periodo) + " meses:");
    buys.forEach(function (x, i) { out.push("- Compra " + (i + 1) + ": " + A.brl(num(x.preco)) + " × " + A.n0(num(x.qtd))); });
    out.push("Faixa " + A.brl(b.min) + "–" + A.brl(b.max) + " | mediana " + A.brl(b.med) + " | acima da mediana/ano " + A.brl(b.acimaAno));
    out.push("Aba aberta no envio: " + (current === "compra" ? "compras" : "procedimentos"));
    return out.join("\n");
  }

  drawRows("proc-rows", procs, procRowHtml);
  drawRows("buy-rows", buys, buyRowHtml);
  wireRows("proc-rows", procs, "add-proc", function () { return { nome: "", receb: 0, mat: 0, qtd: 0 }; }, procRowHtml, renderProcs);
  wireRows("buy-rows", buys, "add-buy", function () { return { preco: 0, qtd: 0 }; }, buyRowHtml, renderBuys);
  document.getElementById("item").addEventListener("input", renderBuys);
  document.getElementById("periodo").addEventListener("input", renderBuys);
  document.getElementById("tab-proc").addEventListener("click", function () { showTab("proc"); });
  document.getElementById("tab-compra").addEventListener("click", function () { showTab("compra"); });
  if (window.location.hash === "#compras") showTab("compra");

  A.bindLeadForm("lead", summary);
  renderProcs();
  renderBuys();
})();
