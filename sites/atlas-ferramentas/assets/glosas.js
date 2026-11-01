/* Calculadora de glosas: toda conta usa só os números informados. */
(function () {
  "use strict";
  var A = window.Atlas;

  function compute() {
    var fat = Math.max(0, A.val("fat"));
    var g = A.clamp(A.val("glosa"), 0, 100) / 100;
    var r = A.clamp(A.val("recorre"), 0, 100) / 100;
    var s = A.clamp(A.val("sucesso"), 0, 100) / 100;

    var glosa = fat * g;
    var recuperado = glosa * r * s;
    var perdidaRecurso = glosa * r * (1 - s);
    var nunca = glosa * (1 - r);
    var perda = glosa - recuperado;
    var potencialAno = nunca * s * 12;

    return { fat: fat, g: g, r: r, s: s, glosa: glosa, recuperado: recuperado,
      perdidaRecurso: perdidaRecurso, nunca: nunca, perda: perda, perdaAno: perda * 12,
      potencialAno: potencialAno };
  }

  function insight(c) {
    if (c.glosa <= 0) return "Informe o faturamento e o percentual glosado para ver a leitura.";
    if (c.r < 0.5) {
      return "Mais da metade da glosa nem chega a ser contestada (" + A.pct(1 - c.r) + "). Hipótese a testar: o recurso não tem dono nem prazo controlado. Antes de renegociar com o convênio, vale olhar quem responde pela glosa e em quantos dias.";
    }
    if (c.s < 0.4) {
      return "Vocês recorrem, mas recuperam pouco (" + A.pct(c.s) + "). Hipótese a testar: recurso sem fundamentação técnica, fora do prazo ou repetindo o mesmo motivo. O motivo da glosa mais frequente costuma dizer onde está a causa.";
    }
    return "O recurso funciona. O próximo ganho tende a estar antes da glosa: autorização, cadastro do convênio e conferência da conta antes do envio. Prevenir custa menos que recorrer.";
  }

  function render() {
    var c = compute();
    A.set("o-glosa-mes", A.brl(c.glosa));
    A.set("o-perda-ano", A.brl(c.perdaAno));
    var meses = c.fat > 0 ? c.perdaAno / c.fat : 0;
    A.set("o-perda-equiv", c.fat > 0
      ? "Equivale a " + A.n1(meses) + " " + (Math.abs(meses - 1) < 0.05 ? "mês" : "meses") + " de faturamento de convênio, perdidos todo ano."
      : "—");
    A.set("l-glosa", A.brl(c.glosa));
    A.set("l-rec", A.brl(c.recuperado));
    A.set("l-nunca", A.brl(c.nunca));
    A.set("l-perda", A.brl(c.perda));
    A.set("l-pot", "+ " + A.brl(c.potencialAno));
    A.set("insight", insight(c));

    var tot = c.glosa || 1;
    document.getElementById("bar-rec").style.width = (c.recuperado / tot * 100) + "%";
    document.getElementById("bar-perdida").style.width = (c.perdidaRecurso / tot * 100) + "%";
    document.getElementById("bar-nunca").style.width = (c.nunca / tot * 100) + "%";
    document.getElementById("bar").setAttribute("aria-label",
      "Da glosa: " + A.pct(c.recuperado / tot) + " recuperada, " + A.pct(c.perdidaRecurso / tot) + " recorrida e perdida, " + A.pct(c.nunca / tot) + " nunca recorrida");
  }

  function summary() {
    var c = compute();
    return [
      "CALCULADORA DE GLOSAS",
      "Faturamento convênios/mês: " + A.brl(c.fat),
      "Glosado: " + A.pct(c.g) + " | Recorrido: " + A.pct(c.r) + " | Recuperado no recurso: " + A.pct(c.s),
      "Glosa/mês: " + A.brl(c.glosa) + " | Recuperado/mês: " + A.brl(c.recuperado) + " | Nunca recorrida/mês: " + A.brl(c.nunca),
      "Perda definitiva/ano: " + A.brl(c.perdaAno),
      "Potencial se recorresse tudo (estimativa)/ano: " + A.brl(c.potencialAno)
    ].join("\n");
  }

  A.onInputs("inputs", render);
  A.bindLeadForm("lead", summary);
  render();
})();
