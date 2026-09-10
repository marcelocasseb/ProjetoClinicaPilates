# Fluxo de Caixa (Financeiro) — F1 Specification

> **Esta spec cobre só a F1 (MVP).** O produto financeiro foi fatiado em três fases
> (ver "Fases futuras" no fim). A F1 entrega o livro-caixa do mês; a F2 entrega o que
> torna a feature única (mensalidade por aluno e inadimplência visível); a F3 entrega
> relatório. Cada fase é utilizável sozinha.

## Problem Statement

O sistema hoje sabe tudo sobre o **atendimento** (paciente, avaliação, aula, escala) e
**nada** sobre o dinheiro. O caixa da clínica vive num caderno ou numa planilha paralela:
ninguém sabe, sem fazer conta à mão, quanto entrou no mês, quanto saiu e o que sobrou.
Pior: os dois mundos nunca se cruzam — a mesma clínica que tem a grade da semana no
sistema não consegue responder "quanto essa grade vale por mês?".

A F1 fecha a lacuna mais básica e mais urgente: **registrar o que entra e o que sai, por
mês, com saldo na tela.** É o que substitui o caderno já na primeira semana.

## Goals

- [ ] Registrar uma **entrada** (recebimento) ou **saída** (despesa) em menos de 15 segundos, sem sair da tela.
- [ ] Ver, numa tela só, **todos os lançamentos de um mês** ordenados por data, com **entradas, saídas e saldo** no topo.
- [ ] Navegar entre meses (anterior / próximo) sem recarregar a página.
- [ ] Corrigir um valor digitado errado e **cancelar** um lançamento sem perder o rastro (soft delete, é dinheiro).
- [ ] Restringir todo o financeiro a **administradores** — a equipe comum não vê faturamento.
- [ ] Manter isolamento multi-tenant (AD-007): a clínica A nunca vê o caixa da B.
- [ ] **Sem mudança de infraestrutura**: nenhuma tabela nova, nenhum GSI novo, nenhuma permissão IAM nova.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Plano/mensalidade por aluno, previsto × recebido, inadimplência | **É a F2.** Depende do livro-caixa existir primeiro. A F1 já grava os campos que a F2 vai ler (`pacienteId`, `competencia`), para a F2 não precisar de migração |
| Tabela de preços por frequência, preço de aula avulsa/reposição | **É a F2** — só faz sentido junto do plano do aluno |
| Marcador de inadimplente na aba Escala | **É a F2** — precisa do plano para saber quem deve |
| Categorias de despesa, comparativo mês a mês, gráfico, export CSV | **É a F3** — relatório em cima de dado que ainda não existe |
| Custo por aula (despesas ÷ aulas registradas) | **É a F3** — precisa de meses de histórico para significar algo |
| Emissão de nota fiscal | Fora do produto. Exige integração com prefeitura/certificado digital — projeto próprio |
| Integração bancária, PIX automático, conciliação | Fora do produto. Exige Open Finance/adquirente, com custo e compliance que não cabem numa clínica pequena |
| Comissão de professor | Fora do produto (por ora). Regra de negócio muito variável entre clínicas |
| Contas a pagar futuras / recorrência de despesa | Não pedido. O caixa é do que **já aconteceu** (regime de caixa) |
| Múltiplas contas/carteiras (banco A, banco B, dinheiro) | Não pedido. A clínica tem um caixa só; `formaPagamento` já dá a granularidade útil |

---

## User Stories

### P1: Lançar entrada e saída ⭐ MVP

**User Story**: Como administradora da clínica, quero registrar um dinheiro que entrou ou
que saiu, com data, descrição e valor, para parar de anotar no caderno.

**Why P1**: Sem escrita não há caixa. É a única forma de o dado nascer.

**Acceptance Criteria**:

1. WHEN uma admin envia um lançamento com `tipo`, `data`, `valorCentavos` e `descricao` válidos THEN o sistema SHALL retornar `201` com o lançamento criado, incluindo um `id` gerado.
2. WHEN o lançamento é gravado THEN o sistema SHALL derivar a partição da **`data` informada** (`AAAA-MM`), nunca da data de hoje — lançar dia 02/10 uma despesa paga em 28/09 cai em **setembro**.
3. WHEN `tipo` não é `entrada` nem `saida` THEN o sistema SHALL retornar `400`.
4. WHEN `valorCentavos` é zero, negativo ou não-inteiro THEN o sistema SHALL retornar `400` — o sinal vem do `tipo`, nunca do valor.
5. WHEN `data` não está no formato `AAAA-MM-DD` válido THEN o sistema SHALL retornar `400`.
6. WHEN `descricao` vem vazia ou só com espaços THEN o sistema SHALL retornar `400`.
7. WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (não persistir lixo).

**Independent Test**: `POST /financeiro/lancamentos` com `{tipo:"saida", data:"2026-09-28", valorCentavos:15000, descricao:"Conta de luz"}` retorna `201`; o item aparece na partição `FIN#2026-09`.

---

### P1: Ver o caixa do mês com saldo ⭐ MVP

**User Story**: Como administradora, quero abrir a aba Financeiro e ver todos os lançamentos
do mês com o total que entrou, o total que saiu e o saldo, para saber se o mês fechou no azul.

**Why P1**: É a tela da feature. Sem ela o dado entra e não volta — não entrega nada.

**Acceptance Criteria**:

1. WHEN uma admin solicita o caixa de um mês THEN o sistema SHALL retornar `200` com `mes`, `entradasCentavos`, `saidasCentavos`, `saldoCentavos` e a lista `lancamentos`.
2. WHEN o caixa é montado THEN o sistema SHALL devolver os lançamentos **ordenados por data crescente** (ordem de extrato).
3. WHEN os totais são calculados THEN o sistema SHALL somar **apenas lançamentos ativos** e SHALL calcular `saldo = entradas − saidas`.
4. WHEN o mês não tem lançamento THEN o sistema SHALL retornar `200` com lista vazia e totais zerados (a tela aparece vazia, não quebra).
5. WHEN o parâmetro `mes` é omitido THEN o sistema SHALL assumir o **mês corrente**.
6. WHEN o parâmetro `mes` não está no formato `AAAA-MM` THEN o sistema SHALL retornar `400`.
7. WHEN o mês tem muitos lançamentos THEN o repositório SHALL paginar (`LastEvaluatedKey`) — o extrato nunca trunca em silêncio.

**Independent Test**: Com 2 entradas (R$ 100,00 + R$ 260,00) e 1 saída (R$ 150,00) em outubro, `GET /financeiro/lancamentos?mes=2026-10` retorna `saldoCentavos = 21000` e os 3 itens em ordem de data.

---

### P1: Aba Financeiro no front ⭐ MVP

**User Story**: Como administradora, quero uma aba Financeiro no sistema onde eu vejo o mês,
navego para o anterior e lanço uma entrada ou saída num formulário curto.

**Why P1**: A feature só entrega valor com a tela; o back sozinho não fecha o vertical slice.

**Acceptance Criteria**:

1. WHEN a usuária logada é **admin** THEN o front SHALL exibir a aba "Financeiro" na navegação.
2. WHEN a usuária logada **não** é admin THEN o front SHALL **omitir** a aba (a proteção real é do backend; esconder é só higiene de UI).
3. WHEN a aba é aberta THEN o front SHALL carregar o **mês corrente** e exibir os três totais no topo (entradas, saídas, saldo).
4. WHEN o saldo é negativo THEN o front SHALL destacá-lo visualmente (o vermelho é a informação).
5. WHEN a usuária clica em "‹" ou "›" THEN o front SHALL carregar o mês anterior/seguinte sem recarregar a página.
6. WHEN a usuária digita o valor THEN o front SHALL aceitar máscara em reais (`R$ 1.234,56`) e enviar **centavos inteiros** para a API.
7. WHEN a lista está vazia THEN o front SHALL exibir uma mensagem orientando o primeiro lançamento (não uma tabela vazia).
8. WHEN um erro de API acontece THEN o front SHALL exibir a mensagem no bloco `.erro` sem perder o que foi digitado.
9. WHEN a tela é aberta em celular THEN a tabela SHALL permanecer utilizável (rolagem horizontal, como a grade da Escala).

**Independent Test**: Na aba Financeiro, lançar "Conta de luz / R$ 150,00 / saída", ver a linha aparecer e o saldo cair R$ 150,00; recarregar a página e a linha continuar lá.

---

### P1: Financeiro só para administradores ⭐ MVP

**User Story**: Como dona da clínica, quero que só administradores vejam e lancem no
financeiro, para o faturamento não circular entre a equipe.

**Why P1**: É dado sensível desde o primeiro lançamento. Abrir agora e fechar depois é
vazamento; fechar agora e abrir depois é uma linha de código.

**Acceptance Criteria**:

1. WHEN a requisição vem de um token com `custom:role` diferente de `admin` THEN o sistema SHALL retornar `403` em **todas** as rotas de `/financeiro`.
2. WHEN a claim `custom:role` está ausente THEN o sistema SHALL retornar `403` (fail-closed).
3. WHEN o token não tem `custom:clinicId` THEN o sistema SHALL retornar `401`.

**Independent Test**: A mesma chamada com token `role=membro` retorna `403`; com `role=admin`, `200`.

---

### P2: Corrigir e cancelar lançamento

**User Story**: Como administradora, quero corrigir um valor que digitei errado e cancelar
um lançamento indevido, sem que ele suma do histórico.

**Why P2**: O caixa é utilizável sem isso por alguns dias, mas erro de digitação em dinheiro
é questão de quando, não de se.

**Acceptance Criteria**:

1. WHEN uma admin edita um lançamento existente THEN o sistema SHALL retornar `200` com os campos atualizados e SHALL registrar `atualizadoEm`.
2. WHEN uma admin cancela um lançamento THEN o sistema SHALL marcá-lo `ativo=False` (**soft delete**) e SHALL mantê-lo na tabela.
3. WHEN o caixa do mês é listado THEN o sistema SHALL **omitir** os cancelados e SHALL excluí-los dos totais.
4. WHEN o lançamento não existe, já foi cancelado, ou é de outra clínica THEN o sistema SHALL retornar `404`.
5. WHEN a edição muda a `data` para **outro mês** THEN o sistema SHALL retornar `400` — a data é parte da chave; mudar de mês é cancelar e relançar.

**Independent Test**: Criar um lançamento de R$ 150,00, editar para R$ 180,00 e ver o saldo mudar; cancelar e ver a linha sumir da lista e do total, mas o item continuar na tabela com `ativo=False`.

---

## Edge Cases

- WHEN `valorCentavos` vem como float (`15000.5`) THEN o sistema SHALL retornar `400` — dinheiro é inteiro em centavos, sem exceção.
- WHEN `valorCentavos` vem como string numérica (`"15000"`) THEN o sistema SHALL aceitar e converter.
- WHEN `data` é futura THEN o sistema SHALL **aceitar** (pagamento adiantado é normal) e gravá-la na partição do mês dela.
- WHEN `data` é `2026-02-30` (data inexistente) THEN o sistema SHALL retornar `400`.
- WHEN dois lançamentos têm a mesma data THEN o sistema SHALL aceitar ambos (o `id` no fim do SK garante unicidade).
- WHEN `descricao` excede 200 caracteres THEN o sistema SHALL retornar `400`.
- WHEN `pacienteId` é informado THEN o sistema SHALL gravar as chaves do GSI1 (preparação da F2); WHEN é ausente THEN o item SHALL ficar **fora** do índice (esparso).
- WHEN `competencia` é informada sem `pacienteId` THEN o sistema SHALL retornar `400` (competência só existe para mensalidade de aluno).
- WHEN o mesmo mês é consultado por duas clínicas THEN cada uma SHALL ver **apenas** os próprios lançamentos (partições diferentes).
- WHEN o front pede um mês antigo sem movimento THEN o sistema SHALL retornar `200` vazio (nunca `404` — mês sem movimento é um fato, não um erro).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ------ | ------ |
| FIN-01 | P1: Criar lançamento (`POST`), partição derivada da `data` | C1, C2, C3, C5 | Verified |
| FIN-02 | P1: Persistência PK/SK na partição mensal (`FIN#<AAAA-MM>` / `LANC#<id>`) | C2 | Verified |
| FIN-03 | P1: Listar o mês ordenado por data (`GET`), mês corrente por padrão | C2, C3, C5 | Verified |
| FIN-04 | P1: Totais do mês (entradas, saídas, saldo) só com ativos | C3, C5 | Verified |
| FIN-05 | P1: Validações → `400` (tipo, valor inteiro > 0, data, descrição) | C1, C3 | Verified |
| FIN-06 | P1: Restrição a admin (`403`) em todas as rotas de `/financeiro` | C3 | Verified |
| FIN-07 | P1: Isolamento multi-tenant (clínica A não lê nem escreve na B) | C2, C3 | Verified |
| FIN-08 | P1: Paginação da leitura do mês (`LastEvaluatedKey`) | C2 | Verified |
| FIN-09 | P1: Front — aba Financeiro (totais, navegação de mês, formulário, máscara, mobile) | C4, C5, C6 | Implementing |
| FIN-10 | P2: Editar lançamento; mudança de mês → `400` | C2, C3, C5 | Verified |
| FIN-11 | P2: Cancelar (soft delete); omitido da lista e dos totais | C2, C3, C5 | Verified |
| FIN-12 | Preparação F2: `pacienteId`/`competencia` opcionais gravados no GSI1 esparso | C1, C2 | Verified |

**ID format:** `FIN-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 12 total, 12 mapped to tasks, 0 unmapped ✅ — back coberto por **140 testes**
(suíte 294 → **434**). FIN-09 fica **Implementing** até o teste da aba no browser; o resto vira
**Verified** após o deploy + smoke-test.

---

## Data Model (referência AD-005 / AD-007)

Lançamento na tabela única, em **partição própria por mês**:

```
PK = CLINIC#<clinicId>#FIN#<AAAA-MM>       ex.: CLINIC#abc#FIN#2026-10
SK = LANC#<id>                             ex.: LANC#a3f2-…
Atributos:
  id              (string uuid4)
  tipo            ("entrada" | "saida")
  data            (string "AAAA-MM-DD" — quando o dinheiro andou; regime de caixa)
  valorCentavos   (int > 0 — sempre positivo; o sinal é o `tipo`)
  descricao       (string, 1..200)
  formaPagamento  (string opcional: "dinheiro" | "pix" | "cartao" | "transferencia")
  pacienteId      (string opcional — preparação F2)
  competencia     (string opcional "AAAA-MM" — a que mês a mensalidade se refere; F2)
  clinicId        (string)
  ativo           (bool — soft delete)
  criadoEm        (ISO timestamp)
  atualizadoEm    (ISO timestamp)

Chaves do GSI1 (só quando há `pacienteId` E `competencia` — índice esparso):
  GSI1PK = CLINIC#<clinicId>#FIN#COMP#<competencia>
  GSI1SK = <pacienteId>#<id>
  ⚠️ REINDEXADO na F2 (era por aluno). Ver spec-f2.md, "Data Model", e AD-015.
```

**Por que este desenho:**

- **Partição por mês = a unidade da tela.** O usuário sempre olha um mês; a partição espelha
  isso, então **o extrato inteiro sai de 1 Query** por `PK` + `SK begins_with "LANC#"`. Uma
  clínica com 10 anos de histórico fica com 120 partições pequenas, em vez de uma partição
  quente que só cresce.
- **A `data` NÃO entra no SK** (mudança decidida durante a implementação — o desenho original
  era `LANC#<data>#<id>`, para o SK já sair ordenado por data). Com a data na chave, o item
  fica não-endereçável por `id` e, pior, **corrigir a data de 05 para 03 viraria uma
  movimentação de item** (put na chave nova + delete na antiga): duas escritas não-atômicas
  num livro-caixa, onde uma falha no meio duplica ou some com dinheiro. Com `SK=LANC#<id>` a
  correção é um `update_item` atômico, e a ordenação por data é feita na aplicação — barata,
  porque a partição de um mês é pequena por construção (é o motivo de ela existir).
- **Zero mudança de infra**: nenhuma tabela nova, nenhum GSI novo, nenhum atributo indexado
  novo (o `GSI1` já existe e já é esparso), nenhuma permissão IAM nova → o deploy é **só
  código Lambda + front**, e `src/requirements.txt` não muda (o atalho de deploy sem Docker
  continua valendo, AD-006).
- **Dinheiro é `int` em centavos, nunca float.** `0.1 + 0.2 != 0.3` em ponto flutuante, e um
  centavo perdido no total destrói a confiança na tela inteira. O `Decimal` do boto3
  resolveria a persistência, mas voltaria como `Decimal` e viraria float na serialização
  JSON — então a API **trafega centavos inteiros de ponta a ponta** e o front formata só na
  exibição.
- **A partição vem da `data` do lançamento, não de hoje.** Lançar no dia 02/10 uma conta paga
  em 28/09 tem que cair em setembro, senão o fechamento do mês mente.
- **`pacienteId`/`competencia` já entram na F1** mesmo sem tela que os use: são dois atributos
  opcionais no mesmo `put_item`, custo zero agora — e é o que permitiu a F2 nascer sem
  migração. (O *formato* das chaves do GSI1 acabou mudando na F2, de "por aluno" para "por
  competência" — de graça, porque a F1 não chegou a ser deployada. Ver AD-015.)
- **Não colide com nada**: a PK `CLINIC#<clinicId>#FIN#<AAAA-MM>` é distinta da partição de
  nível clínica (`CLINIC#<clinicId>`, onde vivem `METADATA`, `APARELHO#` e `ESCALA#`) e da
  partição do paciente (`CLINIC#<clinicId>#CLIENT#<id>`).

**Soft delete (segue a convenção do sistema):** ao contrário da Escala — que é *estado atual*
e apaga fisicamente — o caixa é **histórico**, e histórico financeiro não se apaga. Cancelar
marca `ativo=False`; o item permanece na tabela para auditoria ("essa despesa de R$ 800,00 foi
lançada e cancelada em 03/10, por engano").

---

## Fases futuras (contexto, não escopo)

| Fase | Entrega | Por que depois |
| ---- | ------- | -------------- |
| **F2 — o diferencial** | Plano do aluno (`SK=FIN#PLANO`: valor mensal + dia de vencimento), tabela de preços por frequência, tela de mensalidades com **previsto × recebido × inadimplentes**, marcador de inadimplência na aba Escala, preço de aula avulsa/reposição | Precisa do livro-caixa da F1 como base de "recebido". Princípio arquitetural fixado: **a Escala nunca é fonte da verdade do valor** — a fonte é o plano do aluno no cadastro; a grade só pré-preenche a frequência e aponta divergência, e tudo funciona numa clínica que não usa a Escala |
| **F3 — relatório** | Categorias de despesa, comparativo mês a mês, gráfico, export CSV para o contador, custo real por aula | Relatório em cima de dado que só existe depois de F1+F2 rodarem alguns meses |

---

## Success Criteria

- [ ] A administradora registra um lançamento em **menos de 15 segundos** (abrir aba → salvar).
- [ ] O saldo na tela **bate com a soma feita à mão** dos lançamentos do mês — zero divergência de centavo.
- [ ] Um usuário `membro` **não consegue** ler nem escrever nada em `/financeiro` (403 em todas as rotas).
- [ ] A clínica consegue **abandonar o caderno** para entradas e saídas na primeira semana de uso.
- [ ] Deploy **sem alteração de `template.yaml`** e sem rebuild de dependências.
