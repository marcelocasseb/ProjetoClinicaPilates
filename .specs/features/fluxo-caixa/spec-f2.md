# Fluxo de Caixa — F2: Mensalidades e Inadimplência

> Continuação de [`spec.md`](spec.md) (F1 — livro-caixa). A F1 respondeu "quanto entrou
> e saiu"; a F2 responde **"quanto DEVERIA ter entrado, e quem não pagou"**. É a fase que
> justifica o produto: nenhum caixa genérico sabe disso, porque nenhum deles conhece os
> alunos da clínica.

## Problem Statement

Com só o livro-caixa, a dona vê que entraram R$ 6.200 no mês — mas não sabe se era para
ter entrado R$ 6.200 ou R$ 8.450, nem quem está devendo. Descobrir isso hoje significa
conferir aluno por aluno numa planilha paralela, que é exatamente o trabalho que o
sistema deveria eliminar. E a informação chega tarde: a recepção só descobre que alguém
está inadimplente quando alguém decide procurar.

## Goals

- [ ] Ver, num mês, **previsto × recebido × em aberto** da clínica inteira, e o mesmo aluno a aluno.
- [ ] Definir **quanto cada aluno paga** por mês, com desconto/bolsa/acordo cabendo sem gambiarra.
- [ ] Dar **baixa no pagamento** de um aluno em um clique, sem digitar descrição nem data.
- [ ] Fazer a **mensalidade atrasada** cair no lugar certo: pagou em outubro a de setembro → conta no caixa de outubro e quita setembro.
- [ ] Mostrar a inadimplência **onde a recepção já olha** — um marcador no nome do aluno dentro da aba Escala.
- [ ] Poupar digitação com uma **tabela de preços por frequência**, sem nunca tornar a tabela obrigatória.
- [ ] Apontar **divergência** entre o plano e a grade ("paga 2x, está em 3 horários").
- [ ] **Sem mudança de infraestrutura** e sem migração de dado da F1.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Cobrança automática (boleto, PIX, link de pagamento) | Fora do produto — exige adquirente, compliance e custo por transação |
| Lembrete/notificação ao aluno | Não há canal com o aluno; o sistema é interno da clínica |
| Multa e juros por atraso | Não pedido. A clínica negocia caso a caso; um campo errado aqui vira cobrança indevida |
| Contrato/carnê, parcelamento formal | Não pedido. "Pagou parte" já é representável por dois lançamentos |
| Reajuste em massa da tabela de preços | A tabela existe, mas aplicar reajuste a todos os planos de uma vez é F3 |
| Histórico de mudança de plano | Não pedido. O plano é **estado atual**; o histórico de dinheiro está nos lançamentos |
| Cobrar aula avulsa/reposição automaticamente | Os preços são cadastrados (para consulta e futuro pré-preenchimento), mas a cobrança segue manual |

---

## User Stories

### P1: Ver o mês de mensalidades ⭐ MVP

**User Story**: Como administradora, quero ver numa tabela todos os alunos com o valor que
cada um paga, quanto já pagou no mês e quem está devendo, para saber onde cobrar.

**Why P1**: É a tela da fase. Sem ela, a F2 não existe.

**Acceptance Criteria**:

1. WHEN a admin abre as mensalidades de um mês THEN o sistema SHALL retornar `200` com `previstoCentavos`, `recebidoCentavos`, `emAbertoCentavos` e a lista `alunos`.
2. WHEN a lista é montada THEN ela SHALL vir do **cadastro de pacientes ativos**, não da Escala — a tela SHALL funcionar integralmente numa clínica que nunca usou a grade.
3. WHEN um aluno não tem plano THEN o sistema SHALL marcá-lo `sem_plano` e SHALL **não** somá-lo ao previsto.
4. WHEN um aluno tem plano com valor zero THEN o sistema SHALL marcá-lo `isento` — um estado **diferente** de `sem_plano`.
5. WHEN o pago é maior ou igual ao valor THEN o status SHALL ser `pago`; maior que zero e menor que o valor, `parcial`; zero, `aberto`.
6. WHEN o em aberto da clínica é totalizado THEN ele SHALL ser a soma do em aberto **por aluno** — um aluno que pagou adiantado não pode mascarar a dívida de outro.
7. WHEN um aluno é removido do cadastro THEN ele SHALL sumir da tela e do previsto.
8. WHEN a clínica não tem aluno THEN o sistema SHALL retornar `200` com lista vazia e totais zerados.
9. WHEN os alunos são listados THEN eles SHALL vir ordenados por nome.

**Independent Test**: Com 3 alunos (R$ 260 pago, R$ 340 com R$ 100 pago, R$ 160 nada), a tela mostra previsto R$ 760, recebido R$ 360 e em aberto R$ 400.

---

### P1: Definir quanto o aluno paga ⭐ MVP

**User Story**: Como administradora, quero definir o valor mensal e o dia de vencimento de
cada aluno direto na linha dele, para não precisar de planilha.

**Why P1**: Sem plano não há previsto, e sem previsto não há inadimplência.

**Acceptance Criteria**:

1. WHEN a admin define o plano de um aluno da sua clínica THEN o sistema SHALL retornar `200` com o plano gravado.
2. WHEN o plano é definido de novo THEN o sistema SHALL **substituir** o anterior (idempotente) e SHALL preservar o `criadoEm` original.
3. WHEN `valorCentavos` é zero THEN o sistema SHALL **aceitar** (bolsista/cortesia).
4. WHEN `valorCentavos` é negativo, float ou não numérico THEN o sistema SHALL retornar `400`.
5. WHEN `diaVencimento` está fora de 1..31, ou `frequencia` fora de 1..7 THEN o sistema SHALL retornar `400`.
6. WHEN o aluno não existe ou é de outra clínica THEN o sistema SHALL retornar `404`.
7. WHEN a admin remove o plano THEN o aluno SHALL voltar ao estado `sem_plano`.
8. WHEN a frequência é escolhida no front E existe faixa correspondente na tabela de preços THEN o front SHALL **pré-preencher** o valor — e SHALL permitir sobrescrevê-lo à mão.

**Independent Test**: Definir R$ 260,00 / dia 5 / 2x por semana para um aluno; a linha dele passa a mostrar o valor e a somar no previsto.

---

### P1: Dar baixa no pagamento ⭐ MVP

**User Story**: Como administradora, quero registrar que o aluno pagou a mensalidade do mês
em um clique, para não redigitar descrição, data e valor a cada recebimento.

**Why P1**: É o que liga a F2 ao caixa da F1 — sem isso o "recebido" nunca sai de zero.

**Acceptance Criteria**:

1. WHEN a admin dá baixa THEN o sistema SHALL criar um lançamento de **entrada** no caixa com `pacienteId` e `competencia` = o mês exibido.
2. WHEN a baixa é criada THEN a `data` do lançamento SHALL ser **hoje** (quando o dinheiro entrou) e a `competencia` SHALL ser o mês da tela — os dois são independentes.
3. WHEN a mensalidade de setembro é paga em outubro THEN o sistema SHALL contá-la no **caixa de outubro** e SHALL quitá-la na **competência de setembro**.
4. WHEN o aluno paga em duas parcelas THEN o sistema SHALL somar as duas no `pagoCentavos`.
5. WHEN um pagamento é cancelado no caixa THEN o aluno SHALL voltar a aparecer em aberto.
6. WHEN um lançamento de **saída** tem competência (estorno/devolução) THEN ele SHALL **não** contar como mensalidade paga.
7. WHEN a admin dá baixa THEN o front SHALL oferecer a **forma de pagamento** (as mesmas opções do Caixa) e SHALL enviá-la no lançamento — senão o extrato ficaria com recebimentos sem forma, incoerentes com os lançados na mão.
8. WHEN a baixa é registrada THEN a aba **Caixa** SHALL refletir o novo lançamento **sem recarregar a página**.

**Independent Test**: Dar baixa de R$ 260 num aluno em aberto; ele vira "pago", o recebido sobe R$ 260 e a linha aparece no extrato do caixa com a data de hoje.

---

### P1: Inadimplente visível na Escala ⭐ MVP

**User Story**: Como recepção, quero ver no nome do aluno dentro da grade que ele está
devendo, para saber disso no momento em que ele chega para a aula.

**Why P1**: É o diferencial do produto. Um relatório de inadimplência que vive numa aba
separada não muda comportamento; um marcador onde a pessoa já olha, muda.

**Acceptance Criteria**:

1. WHEN a usuária é **admin** E o aluno tem mensalidade em aberto no mês corrente THEN a grade SHALL exibir um marcador no chip dele, com o valor devido no `title`.
2. WHEN a usuária **não** é admin THEN a grade SHALL ser exibida **sem** nenhum marcador e sem chamar a API de financeiro (ela devolveria `403`).
3. WHEN a consulta de inadimplência falha THEN a grade SHALL continuar renderizando normalmente — o marcador é um extra, a grade é o que a recepção veio ver.

**Independent Test**: Com um aluno em aberto e matriculado na segunda às 7h, a célula mostra o nome dele com o ponto vermelho; passando o mouse, aparece o valor.

---

### P2: Tabela de preços por frequência

**User Story**: Como dona da clínica, quero cadastrar quanto custa 1x, 2x, 3x e 5x por
semana, para não redigitar o mesmo valor a cada aluno e enxergar meu desconto de volume.

**Why P2**: Conveniência. A tela de mensalidades funciona sem a tabela — o valor pode ser
digitado direto no aluno.

**Acceptance Criteria**:

1. WHEN a clínica nunca configurou preços THEN o sistema SHALL retornar `200` com a tabela vazia e zeros — **nunca** `404`.
2. WHEN a admin salva a tabela THEN o sistema SHALL persistir as faixas, o preço de aula avulsa e o de reposição.
3. WHEN uma faixa tem frequência fora de 1..7 ou valor inválido THEN o sistema SHALL retornar `400`.
4. WHEN um valor é zero THEN o sistema SHALL aceitar (reposição de cortesia).
5. WHEN o front exibe a tabela THEN ele SHALL mostrar o **valor por aula calculado** (÷ 4,33 semanas) como campo **read-only** — o por-aula nunca é digitado para mensalista.
6. WHEN uma frequência fica em branco THEN ela SHALL simplesmente não virar sugestão.

**Independent Test**: Salvar 2x = R$ 260,00; ao definir o plano de um aluno escolhendo "2x por semana", o valor já aparece preenchido com R$ 260,00.

---

### P2: Filtrar a lista de alunos

**User Story**: Como administradora de uma clínica com dezenas de alunos, quero buscar por
nome e filtrar por vencimento e situação, para achar quem eu preciso cobrar sem rolar a
tabela inteira.

**Why P2**: A tela é utilizável sem filtro numa clínica pequena; vira obrigatória quando a
lista passa de uma tela.

**Acceptance Criteria**:

1. WHEN a admin digita parte de um nome THEN a lista SHALL filtrar **ignorando acento e caixa** ("jose" acha "José").
2. WHEN a admin escolhe uma situação THEN a lista SHALL mostrar só os alunos naquele status.
3. WHEN a admin escolhe um dia de vencimento THEN a lista SHALL mostrar só quem vence naquele dia.
4. WHEN o combo de vencimento é montado THEN ele SHALL oferecer **apenas os dias em uso** na clínica, não 1..31.
5. WHEN há filtro ativo THEN os **três totais do topo SHALL continuar sendo os do mês inteiro** — filtrar a visão não pode alterar o previsto/recebido da clínica.
6. WHEN há filtro ativo THEN o cabeçalho SHALL indicar "N de M" alunos e SHALL oferecer "limpar filtros".
7. WHEN nenhum aluno casa com o filtro THEN a tela SHALL dizer isso — e SHALL ser uma mensagem **diferente** de "a clínica não tem alunos".

**Independent Test**: Buscar "bea" acha "Beatriz Nunes"; filtrar por "Em aberto" esconde quem já pagou; os totais do topo não mudam.

---

### P2: Divergência entre plano e grade

**User Story**: Como administradora, quero ser avisada quando um aluno paga por 2 aulas
mas está marcado em 3 horários, para não cobrar a menos sem perceber.

**Why P2**: Depende da clínica usar a Escala; a tela toda funciona sem isso.

**Acceptance Criteria**:

1. WHEN o plano tem frequência E o aluno tem horários na grade E os dois diferem THEN o sistema SHALL marcar `divergenciaEscala=true` e SHALL informar `frequenciaEscala`.
2. WHEN a clínica não usa a Escala THEN `frequenciaEscala` SHALL ser `null` e `divergenciaEscala` SHALL ser `false` — **nunca** um alarme falso.
3. WHEN o plano não tem frequência definida THEN não SHALL haver divergência (não há o que comparar).

**Independent Test**: Aluno com plano 2x matriculado em 3 horários mostra o aviso "⚠ grade: 3x"; ajustando o plano para 3x, o aviso some.

---

## Edge Cases

- WHEN o aluno paga a mais THEN o em aberto dele SHALL ser `0`, nunca negativo.
- WHEN um pagamento tem `pacienteId` mas **não** tem `competencia` (aula avulsa) THEN ele SHALL entrar no caixa mas **não** contar como mensalidade.
- WHEN dois pagamentos existem para o mesmo aluno e competência THEN ambos SHALL constar (o `id` no `GSI1SK` garante que um não sobrescreva o outro).
- WHEN o plano é definido para aluno de outra clínica THEN o sistema SHALL retornar `404` (isolamento).
- WHEN um usuário `membro` chama qualquer rota de mensalidade/plano/preço THEN o sistema SHALL retornar `403`.
- WHEN a clínica tem muitos alunos THEN as leituras de plano e de pagamento SHALL paginar (`LastEvaluatedKey`) — tela truncada esconderia inadimplente.

---

## Requirement Traceability

| Requirement ID | Story | Status |
| -------------- | ----- | ------ |
| FIN-13 | P1: Plano do aluno (upsert idempotente, valor zero válido, 404 fora da clínica) | Verified |
| FIN-14 | P1: Tela de mensalidades (previsto/recebido/em aberto + lista, vinda do cadastro) | Verified |
| FIN-15 | P1: Status por aluno (pago/parcial/aberto/isento/sem_plano) e em aberto somado por aluno | Verified |
| FIN-16 | P2: Tabela de preços da clínica + aula avulsa/reposição; por-aula derivado read-only | Verified |
| FIN-17 | P1: Baixa de pagamento (data = hoje, competência = mês exibido) e atrasado na competência certa | Verified |
| FIN-18 | P2: Divergência plano × grade, sem alarme falso quando não há escala | Verified |
| FIN-19 | P1: Marcador de inadimplente na aba Escala (só admin, degrada em silêncio) | Implementing |
| FIN-20 | Isolamento multi-tenant e `403` para membro em todas as rotas novas | Verified |
| FIN-21 | P1: Forma de pagamento na baixa + Caixa reflete a baixa sem recarregar a página | Implementing |
| FIN-22 | P2: Filtros da tela de mensalidades (nome sem acento, situação, vencimento) | Implementing |

**Coverage:** 10 total, 10 implementados. FIN-19, FIN-21 e FIN-22 viram **Verified** após o teste no browser.

---

## Data Model (adições à F1)

```
Plano do aluno — partição de NÍVEL CLÍNICA (não sob a PK do paciente):
  PK = CLINIC#<clinicId>
  SK = FIN#PLANO#<pacienteId>
  Atributos: valorCentavos (int >= 0), diaVencimento (1..31), frequencia (1..7), observacao

Tabela de preços — mesma partição:
  PK = CLINIC#<clinicId>
  SK = FIN#CONFIG
  Atributos: tabelaPrecos [{frequencia, valorCentavos}], aulaAvulsaCentavos, reposicaoCentavos

GSI1 do lançamento — REINDEXADO por competência (mudou em relação à F1):
  GSI1PK = CLINIC#<clinicId>#FIN#COMP#<competencia>
  GSI1SK = <pacienteId>#<id>
```

**Por que este desenho:**

- **O plano mora na partição da clínica, não sob a PK do paciente.** O acesso dominante é
  a tela de mensalidades, que precisa de **todos os planos de uma vez** — 1 Query. Sob a
  PK do paciente seria um `get_item` por aluno (30-60 por carregamento). É a mesma decisão
  da escala (AD-013): modela-se para o acesso dominante.
- **O GSI1 foi reindexado por competência** (a F1 indexava por aluno). A pergunta da tela
  é "quem pagou a competência de setembro?", e o pagamento de setembro pode ter sido feito
  em outubro — ou seja, mora na **partição de outubro**. Por competência, a tela é 1 Query;
  por aluno, seria uma Query por aluno. **Sem custo de migração: a F1 não chegou a ser
  deployada.**
- **O índice exige `pacienteId` E `competencia`.** Aula avulsa de um aluno tem paciente mas
  não tem competência — não é mensalidade e fica fora do índice, de propósito.
- **`<id>` no fim do `GSI1SK`** para o mesmo aluno poder pagar a competência em duas
  parcelas sem uma sobrescrever a outra.
- **Zero mudança de infraestrutura:** `template.yaml` intacto, `GSI1` já existia.
- **Custo da tela:** 4 Queries fixas (alunos, planos, pagamentos da competência, grade) —
  nenhuma delas por aluno.

**Remoção do plano é física** (como a escala): o plano é *estado atual*, e o histórico de
dinheiro vive nos lançamentos, que são soft-deleted.

---

## Success Criteria

- [ ] A dona responde "quanto falta entrar este mês?" em **menos de 5 segundos**, sem planilha.
- [ ] A recepção descobre que um aluno está devendo **no momento em que ele chega**, sem procurar.
- [ ] Uma clínica que **não usa a Escala** tem a tela funcionando integralmente.
- [ ] Mensalidade atrasada cai no mês certo dos **dois** pontos de vista (caixa e competência).
- [ ] Deploy sem alteração de `template.yaml` e **sem migração** de dado da F1.
