# Relatórios Specification

## Problem Statement

O sistema já guarda o dia a dia da clínica: Caixa, mensalidades, cadastro de alunos, escala,
aulas registradas e profissionais. Mas cada tela mostra **um mês ou um aluno por vez**. Para
responder perguntas de gestão ("o mês fechou no azul?", "quantos alunos entraram?", "quais
horários estão vazios?", "quantas aulas cada profissional deu?"), a dona da clínica precisa
somar na mão. Esta feature cria uma aba **Relatórios** (só admin) com 4 grupos (Financeiro,
Alunos, Ocupação da escala e Atendimento). Cada relatório aparece em tela, com gráfico e tabela,
e pode ser impresso ou salvo em PDF. Há também um **fechamento do mês**: um PDF único com os 4
grupos.

Com a segunda cliente (High Performance Fisio, 2026-11-09), o sistema passa a ser vendido para
mais de uma clínica, e relatórios de gestão estão entre as primeiras coisas que um dono de
clínica pede.

## Goals

- [ ] A admin responde as perguntas de gestão do mês **sem fazer conta na mão**: resultado do Caixa, mensalidades, alunos, ocupação e aulas, todos em uma única aba.
- [ ] Cada número tem **comparação com os últimos 12 meses** (onde existe histórico), para mostrar tendência.
- [ ] Qualquer relatório vira um **PDF limpo** (cabeçalho com nome da clínica e mês, sem menus). Também existe um **fechamento do mês** com os 4 grupos juntos.
- [ ] **Sem dado novo e sem mudança na tabela de produção**: tudo sai do que já está gravado (nada de GSI ou tabela nova; `ClinicaTable` e Cognito ficam intactos).
- [ ] Isolamento multi-tenant (AD-007): uma clínica só vê os próprios números.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Despesas por categoria (aluguel, salário, material) | A saída do Caixa só tem `descricao` livre, sem categoria. Exige um dado novo, então fica para uma fase 2 |
| Faltas e presença | A escala é fixa e não registra quem veio em cada dia. Precisa de feature própria (check-in) |
| Inadimplência acumulada de meses anteriores | O plano não tem data de início, então o sistema acusaria dívida de quem ainda não era aluno (mesma limitação da Tela Inicial). Cada mês é visto isolado |
| Intervalo de datas livre (ex.: 15/03 a 10/05) | Decisão do usuário: **mês + evolução de 12 meses** |
| Contar agendamentos da Agenda como aula dada | Decisão do usuário: só as **aulas registradas** (aba Pilates) contam. Agendar não garante que a aula aconteceu |
| Relatórios para membros não-admin | Decisão do usuário: a aba inteira é **só admin** |
| Exportar para Excel/CSV | Não foi escolhido (formato = tela + PDF). Pode entrar depois sem retrabalho |
| Envio automático do fechamento por e-mail | Sem pedido. O PDF é gerado sob demanda |
| Relatórios clínicos (evolução do paciente, avaliações) | São relatórios por paciente, não de gestão. Já existem na ficha |

---

## User Stories

### P1: Aba Relatórios com seletor de mês ⭐ MVP

**User Story**: Como admin da clínica, quero uma aba "Relatórios" onde escolho um mês e navego
entre os 4 grupos, para ver a gestão da clínica em um lugar só.

**Why P1**: É a estrutura em que todos os relatórios encaixam.

**Acceptance Criteria**:

1. WHEN uma admin entra no sistema THEN o sistema SHALL mostrar a aba **Relatórios** na barra (junto do Financeiro).
2. WHEN um membro não-admin entra THEN o sistema SHALL **não** mostrar a aba, AND qualquer endpoint de relatório chamado por ele SHALL responder **403**.
3. WHEN a aba abre THEN o sistema SHALL selecionar o **mês corrente** e mostrar o grupo **Financeiro**, com navegação para Alunos, Ocupação e Atendimento.
4. WHEN a admin troca o mês THEN todos os relatórios que dependem de mês SHALL recarregar para o mês escolhido.
5. WHEN a admin escolhe um mês futuro THEN o sistema SHALL impedir a escolha (o seletor vai até o mês corrente).

**Independent Test**: Entrar como admin, ver a aba e trocar o mês. Entrar como membro: não aparece a aba e `GET /relatorios/...` dá 403.

---

### P1: Relatório Financeiro ⭐ MVP

**User Story**: Como admin, quero ver o resultado do Caixa no mês e a evolução no ano, quanto
entrou por forma de pagamento e como estão as mensalidades, para saber se a clínica está
saudável.

**Why P1**: É a pergunta de gestão número 1, e todos os dados já existem.

**Acceptance Criteria**:

1. WHEN o mês é escolhido THEN o sistema SHALL mostrar **entradas, saídas e saldo** do mês, com os mesmos números da tela Caixa daquele mês.
2. WHEN o relatório abre THEN o sistema SHALL mostrar um gráfico com **entradas × saídas × saldo dos 12 meses** que terminam no mês escolhido. Mês sem lançamento aparece como **zero**, não some.
3. WHEN o mês tem entradas THEN o sistema SHALL mostrar a **receita por forma de pagamento** (dinheiro, pix, crédito, débito, transferência), com valor e % do total. Lançamentos antigos com `cartao` aparecem como **"Cartão (antigo)"**, e entradas sem forma aparecem como **"Não informado"**.
4. WHEN o mês é escolhido THEN o sistema SHALL mostrar o **resumo das mensalidades** (previsto, recebido, em aberto, nº de alunos pagos/parciais/em aberto/sem plano) com os mesmos números da tela Mensalidades daquele mês.
5. WHEN o mês não tem nenhum lançamento THEN o sistema SHALL mostrar o relatório zerado com o aviso "Nenhum lançamento neste mês", sem erro.

**Independent Test**: Comparar entradas, saídas e saldo com a tela Caixa e o resumo de mensalidades com a tela Mensalidades no mesmo mês. Os números têm de bater.

---

### P1: Relatório de Alunos ⭐ MVP

**User Story**: Como admin, quero saber quantos alunos ativos tenho, quantos entraram e saíram
no mês, e quanto a carteira de planos rende por mês, para acompanhar o crescimento.

**Why P1**: É o segundo indicador mais pedido (crescimento), e os dados já existem (`criadoEm`, `ativo`, planos).

**Acceptance Criteria**:

1. WHEN o mês é escolhido THEN o sistema SHALL mostrar **alunos ativos no fim do mês**, **novos no mês** (cadastrados no mês) e **saídas no mês** (removidos no mês).
2. WHEN o relatório abre THEN o sistema SHALL mostrar um gráfico com a **evolução de ativos, novos e saídas nos 12 meses** que terminam no mês escolhido.
3. WHEN o relatório abre THEN o sistema SHALL mostrar a **carteira de planos**: total mensal contratado, ticket médio por aluno com plano, nº de alunos **sem plano** e distribuição por frequência (1x, 2x, 3x… por semana).
4. WHEN o relatório abre THEN o sistema SHALL listar os **alunos novos do mês** (nome e data de cadastro).
5. WHEN um aluno foi removido THEN a data de saída SHALL ser a da remoção (o `atualizadoEm` do perfil inativo, já que um perfil removido não é mais editado).

**Independent Test**: Cadastrar um aluno e remover outro no mês corrente. O relatório mostra +1 novo, +1 saída e o número de ativos certo.

---

### P1: Relatório de Ocupação da escala ⭐ MVP

**User Story**: Como admin, quero ver quantos alunos tenho em cada dia e horário da grade, e
quais horários estão vazios ou cheios, para encaixar alunos novos e decidir horários de
funcionamento.

**Why P1**: É o que mais ajuda a vender horário livre, e a grade já está toda gravada.

**Acceptance Criteria**:

1. WHEN o relatório abre THEN o sistema SHALL mostrar um **mapa de calor** (dias × horários) com a contagem de alunos por célula. Quanto mais alunos, mais forte a cor.
2. WHEN o relatório abre THEN o sistema SHALL mostrar os totais: **matrículas na grade**, **alunos distintos na grade**, **média de alunos por horário ocupado** e os **horários mais cheios** (top 5).
3. WHEN existem alunos ativos sem nenhum horário na grade THEN o sistema SHALL mostrar a contagem e a lista desses alunos ("fora da escala").
4. WHEN o relatório abre THEN o sistema SHALL avisar que a ocupação é a da **grade atual**. A escala não guarda histórico, então este relatório **não muda com o mês** escolhido e não tem evolução de 12 meses.
5. WHEN a clínica não usa a escala (grade vazia) THEN o sistema SHALL mostrar "A clínica ainda não usa a Escala", sem erro.

**Independent Test**: Matricular 3 alunos às 07:00 de segunda e 1 às 18:00 de quarta. O mapa mostra 3 e 1 nessas células, e o top 5 traz segunda 07:00 primeiro.

---

### P1: Relatório de Atendimento ⭐ MVP

**User Story**: Como admin, quero saber quantas aulas foram dadas no mês, por profissional e por
aluno, e quais aparelhos e treinos mais aparecem, para acompanhar a equipe e o uso do estúdio.

**Why P1**: Serve para acompanhar a produtividade da equipe, e é a base para pagar os profissionais.

**Acceptance Criteria**:

1. WHEN o mês é escolhido THEN o sistema SHALL contar **só as aulas registradas** (aba Pilates, ativas) com data no mês. Agendamentos da Agenda **não** contam.
2. WHEN o relatório abre THEN o sistema SHALL mostrar o **total de aulas no mês** e um gráfico da **evolução nos 12 meses**.
3. WHEN o relatório abre THEN o sistema SHALL mostrar **aulas por profissional** (nome e nº de aulas). Aulas sem profissional aparecem como **"Sem profissional"**.
4. WHEN o relatório abre THEN o sistema SHALL mostrar **aulas por aluno** no mês, ordenadas da maior para a menor quantidade.
5. WHEN o relatório abre THEN o sistema SHALL mostrar o **ranking de aparelhos** (em quantas aulas cada um aparece) e o **ranking de tipos de treino**.
6. WHEN um aparelho ou tipo de treino foi renomeado ou removido depois da aula THEN o relatório SHALL usar o **nome gravado na aula** (snapshot), sem quebrar.

**Independent Test**: Registrar 2 aulas de um aluno com a profissional A e 1 aula de outro aluno sem profissional. O relatório mostra total 3, A=2, "Sem profissional"=1, e os aparelhos daquelas aulas no ranking.

---

### P1: Imprimir / PDF por relatório ⭐ MVP

**User Story**: Como admin, quero um botão "Imprimir / PDF" em cada relatório, para guardar ou
mandar para sócio ou contador.

**Why P1**: É o formato que o usuário pediu.

**Acceptance Criteria**:

1. WHEN a admin clica em "Imprimir / PDF" num relatório THEN o sistema SHALL abrir a impressão do navegador só com aquele relatório. Na impressão é possível escolher "Salvar como PDF".
2. WHEN imprime THEN a página SHALL ter um **cabeçalho** com nome da clínica, nome do relatório, mês de referência e data/hora da emissão, **sem** menus, abas ou botões.
3. WHEN imprime THEN gráficos e tabelas SHALL caber em **A4 retrato** sem cortar colunas, e tabelas longas SHALL quebrar de página sem partir linhas ao meio.
4. WHEN imprime THEN as cores SHALL sair legíveis em impressora preto e branco (o gráfico não depende só de cor: tem rótulo ou legenda com valor).

**Independent Test**: Gerar o PDF do Financeiro de um mês e conferir cabeçalho, ausência de menu, gráfico e tabela inteiros em A4.

---

### P2: Fechamento do mês (PDF único)

**User Story**: Como admin, quero gerar com um clique um PDF de fechamento do mês com os 4
grupos, para ter um relatório mensal completo para sócio ou contador.

**Why P2**: Usa as mesmas peças dos relatórios P1. Só faz sentido depois que eles existem.

**Acceptance Criteria**:

1. WHEN a admin clica em "Fechamento do mês" THEN o sistema SHALL montar um documento com **Financeiro, Alunos, Ocupação e Atendimento** do mês escolhido, nessa ordem, e abrir a impressão.
2. WHEN imprime THEN cada grupo SHALL começar em **página nova**, AND a primeira página SHALL ter capa/cabeçalho com nome da clínica, mês e data de emissão.
3. WHEN o fechamento é gerado THEN os números SHALL ser **idênticos** aos dos relatórios em tela do mesmo mês.
4. WHEN um dos grupos falha ao carregar THEN o sistema SHALL avisar qual falhou e **não** gerar um fechamento incompleto em silêncio.

**Independent Test**: Gerar o fechamento de um mês e conferir as 4 seções, com quebra de página entre elas e números iguais aos da tela.

---

## Edge Cases

- WHEN a clínica é nova e vazia (ex.: High Performance Fisio no 1º dia) THEN todos os relatórios SHALL abrir zerados, com mensagens de "sem dados", sem erro.
- WHEN o mês escolhido é anterior ao cadastro da clínica THEN o sistema SHALL mostrar zeros (não erro).
- WHEN a admin vê as mensalidades de um mês passado THEN o resumo SHALL usar os **planos e alunos ativos de hoje** (mesmo comportamento da tela Mensalidades). O relatório SHALL dizer isso numa nota, porque o plano não guarda histórico.
- WHEN existem muitos alunos (ex.: 300) THEN o relatório de Atendimento SHALL abrir em **menos de 5 s**. Hoje as aulas ficam sob cada aluno, então contar a clínica inteira exige ler aluno por aluno. O Design SHALL resolver isso sem mudar a tabela de produção.
- WHEN valores são exibidos THEN o sistema SHALL formatar em R$ com centavos (vêm em centavos inteiros do back) e datas em dd/mm/aaaa.
- WHEN a tela é de celular THEN os relatórios SHALL ser legíveis (gráfico e tabelas com rolagem horizontal se preciso). O PDF continua A4.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| REL-01 | P1: Aba — visível só para admin, 403 para membro | Design | Pending |
| REL-02 | P1: Aba — seletor de mês (padrão mês corrente, sem futuro) | Design | Pending |
| REL-03 | P1: Financeiro — entradas/saídas/saldo do mês (bate com Caixa) | Design | Pending |
| REL-04 | P1: Financeiro — evolução 12 meses | Design | Pending |
| REL-05 | P1: Financeiro — receita por forma de pagamento | Design | Pending |
| REL-06 | P1: Financeiro — resumo de mensalidades (bate com Mensalidades) | Design | Pending |
| REL-07 | P1: Alunos — ativos, novos e saídas no mês | Design | Pending |
| REL-08 | P1: Alunos — evolução 12 meses | Design | Pending |
| REL-09 | P1: Alunos — carteira de planos (total, ticket médio, sem plano, frequência) | Design | Pending |
| REL-10 | P1: Alunos — lista de novos do mês | Design | Pending |
| REL-11 | P1: Ocupação — mapa de calor dia × horário | Design | Pending |
| REL-12 | P1: Ocupação — totais, top 5, alunos fora da escala | Design | Pending |
| REL-13 | P1: Atendimento — total do mês + evolução 12 meses (só aulas registradas) | Design | Pending |
| REL-14 | P1: Atendimento — por profissional e por aluno | Design | Pending |
| REL-15 | P1: Atendimento — ranking de aparelhos e tipos de treino | Design | Pending |
| REL-16 | P1: Imprimir/PDF por relatório (cabeçalho, sem menus, A4, P&B) | Design | Pending |
| REL-17 | P2: Fechamento do mês (4 grupos, página nova por grupo, números idênticos) | Design | Pending |
| REL-18 | Edge: clínica vazia / mês sem dados → zeros sem erro | Design | Pending |
| REL-19 | Edge: Atendimento < 5 s com 300 alunos, sem mudar a tabela | Design | Pending |

**Coverage:** 19 total, 0 mapped to tasks, 19 unmapped ⚠️ (Design e Tasks a seguir)

---

## Success Criteria

- [ ] A admin responde "o mês fechou no azul?", "quantos alunos entraram e saíram?", "qual horário está vazio?" e "quantas aulas cada profissional deu?" em **menos de 1 minuto**, sem calculadora.
- [ ] Os números do Financeiro **batem 100%** com as telas Caixa e Mensalidades do mesmo mês.
- [ ] O PDF de fechamento sai **pronto para mandar** (sem menu, sem coluna cortada) na primeira tentativa.
- [ ] O deploy **não toca** `ClinicaTable` nem o Cognito (changeset só com Lambda e API).
