/* Calculadora de agenda ociosa e faltas: toda conta usa só os números informados. */
(function () {
  "use strict";
  var A = window.Atlas;
  var SEMANAS_MES = 52 / 12; // 4,33

  function compute() {
    var prof = Math.max(0, A.val("prof"));
    var horas = Math.max(0, A.val("horas"));
    var dur = Math.max(5, A.val("dur"));
    var ticket = Math.max(0, A.val("ticket"));
    var ocup = A.clamp(A.val("ocup"), 0, 100) / 100;
    var faltas = A.clamp(A.val("faltas"), 0, 100) / 100;
    var espera = Math.max(0, A.val("espera"));

    var slots = prof * horas * (60 / dur) * SEMANAS_MES;
    var marcados = slots * ocup;
    var realizados = marcados * (1 - faltas);
    var perdFalta = marcados - realizados;
    var vazios = slots - marcados;
    var perdaMes = (perdFalta + vazios) * ticket;

    return { prof: prof, horas: horas, dur: dur, ticket: ticket, ocup: ocup, faltas: faltas, espera: espera,
      slots: slots, marcados: marcados, realizados: realizados, perdFalta: perdFalta, vazios: vazios,
      util: slots > 0 ? realizados / slots : 0, perdaMes: perdaMes, perdaAno: perdaMes * 12,
      potFaltasAno: (perdFalta / 2) * ticket * 12 };
  }

  function insight(c) {
    if (c.slots <= 0) return "Informe profissionais, horas e duração para ver a leitura.";
    var vazioPct = c.vazios / c.slots;
    if (c.espera >= 7 && vazioPct >= 0.15) {
      return "Há " + A.n0(c.espera) + " dias de espera e, ao mesmo tempo, " + A.pct(vazioPct) + " da agenda nunca é marcada. Isso raramente é falta de paciente. Hipótese a testar: bloqueios, regras de encaixe ou horários abertos que não casam com a procura.";
    }
    if (c.faltas >= 0.1) {
      return "De cada 10 pacientes marcados, " + A.n1(c.faltas * 10) + " não vêm. Hipótese a testar: confirmação passiva e ausência de lista de espera para reocupar o horário. É o ganho mais rápido, porque o paciente já existe.";
    }
    if (vazioPct >= 0.25) {
      return A.pct(vazioPct) + " da agenda fica sem marcação. Antes de investir em captação, vale conferir quantos contatos chegam e quantos viram agendamento: a perda pode estar no atendimento do WhatsApp e do telefone.";
    }
    return "A agenda é bem aproveitada. O próximo ganho tende a vir do que ocupa a agenda (mix de procedimentos) e do valor por atendimento, não de mais horários.";
  }

  function render() {
    var c = compute();
    A.set("o-util", A.pct(c.util));
    A.set("o-util-det", A.n0(c.realizados) + " atendimentos de " + A.n0(c.slots) + " horários disponíveis por mês.");
    A.set("o-perda-mes", A.brl(c.perdaMes));
    A.set("o-perda-ano", A.brl(c.perdaAno) + " por ano, contando horários vazios e faltas.");
    A.set("l-slots", A.n0(c.slots));
    A.set("l-real", A.n0(c.realizados));
    A.set("l-falta", A.n0(c.perdFalta) + " · " + A.brl(c.perdFalta * c.ticket));
    A.set("l-vazio", A.n0(c.vazios) + " · " + A.brl(c.vazios * c.ticket));
    A.set("l-pot", "+ " + A.brl(c.potFaltasAno));
    A.set("insight", insight(c));

    var tot = c.slots || 1;
    document.getElementById("bar-real").style.width = (c.realizados / tot * 100) + "%";
    document.getElementById("bar-falta").style.width = (c.perdFalta / tot * 100) + "%";
    document.getElementById("bar-vazio").style.width = (c.vazios / tot * 100) + "%";
    document.getElementById("bar").setAttribute("aria-label",
      "Da agenda: " + A.pct(c.realizados / tot) + " atendida, " + A.pct(c.perdFalta / tot) + " com falta, " + A.pct(c.vazios / tot) + " nunca marcada");
  }

  function summary() {
    var c = compute();
    return [
      "CALCULADORA DE AGENDA OCIOSA E FALTAS",
      "Profissionais: " + A.n0(c.prof) + " | Agenda: " + A.n1(c.horas) + " h/semana cada | Duração: " + A.n0(c.dur) + " min | Valor médio: " + A.brl(c.ticket),
      "Marcados: " + A.n0(c.ocup * 100) + "/100 | Faltas: " + A.n0(c.faltas * 100) + "/100 | Espera: " + A.n0(c.espera) + " dias",
      "Horários/mês: " + A.n0(c.slots) + " | Realizados/mês: " + A.n0(c.realizados) + " | Utilização: " + A.pct(c.util),
      "Capacidade paga e não usada: " + A.brl(c.perdaMes) + "/mês | " + A.brl(c.perdaAno) + "/ano",
      "Faltas pela metade (estimativa): +" + A.brl(c.potFaltasAno) + "/ano"
    ].join("\n");
  }

  A.onInputs("inputs", render);
  A.bindLeadForm("lead", summary);
  render();
})();
