# Tasks — Fluxo de Caixa (Financeiro) F1

**Status:** 🚧 Em implementação. Feature **espelha `cadastro-aparelhos`/`escala`** (recurso de
nível clínica) com três diferenças conscientes: a partição é **mensal**
(`PK=CLINIC#<clinicId>#FIN#<AAAA-MM>`), o valor é **inteiro em centavos** (nunca float), e todas
as rotas exigem **admin** (`require_admin`, já existente em `deps.py`).

**Ordem:** backend primeiro (C1→C2→C3), front depois (C4→C5→C6). Deploy ao fim, no terminal do usuário.

**Gate por task:** `.\.venv\Scripts\python.exe -m pytest -q` verde (sem regressão na suíte existente).

**Dependências:** C2 depois de C1; C3 depois de C2; C5 depois de C3 e C4; C6 depois de C5.

**⚠️ Infra:** esta feature **não altera `template.yaml`** — nenhuma tabela, GSI, atributo indexado
ou permissão IAM nova (o `GSI1` já existe e já é esparso). Deploy = código Lambda + front, e
`src/requirements.txt` não muda (atalho de deploy sem Docker continua válido, AD-006).

---

## C1 — Schemas Pydantic (`src/app/schemas_financeiro.py`)

**What:** Modelos de validação do lançamento. `tipo` restrito a `entrada`/`saida`;
`valorCentavos` **inteiro estritamente positivo** (rejeita float, aceita string numérica);
`data` `AAAA-MM-DD` **realmente existente** (`date.fromisoformat`, que barra `2026-02-30`);
`descricao` 1..200 trimada. `pacienteId`/`competencia` opcionais (preparação F2), com a regra
"competência sem paciente → erro".

**Where:** `src/app/schemas_financeiro.py`, `tests/test_schemas_financeiro.py`

**Reuses:** `schemas_escala.py` (validadores `mode="before"` com mensagem legível em PT-BR →
o handler global de `main.py` converte em 400; `ConfigDict(extra="ignore")`);
`schemas_sessao.py` (`_vazio_para_none`).

**Done when:**
- `LancamentoCreate`: `tipo`, `data`, `valorCentavos`, `descricao`, `formaPagamento?`, `pacienteId?`, `competencia?`.
- `LancamentoUpdate`: mesmos campos editáveis (sem `id`).
- `LancamentoOut`: + `id`, `criadoEm`, `atualizadoEm`.
- `CaixaMesOut`: `mes`, `entradasCentavos`, `saidasCentavos`, `saldoCentavos`, `lancamentos`.
- `valida_mes(mes)` helper → `AAAA-MM` (usado pelo router no query param).
- Mensagens em PT-BR ("valor deve ser um número inteiro de centavos maior que zero", "data deve estar no formato AAAA-MM-DD").

**Tests:** `tipo` inválido → erro; `valorCentavos` 0/-1/`15000.5` → erro; `"15000"` → aceito como int;
`data` `"2026-02-30"`/`"28/09/2026"`/vazia → erro; `descricao` vazia/só-espaços/201 chars → erro;
200 chars → aceito; `competencia` sem `pacienteId` → erro; campos desconhecidos ignorados;
`mes` `"2026-13"`/`"2026-1"` → erro.

**Requirements:** FIN-01 (parte), FIN-05, FIN-12

---

## C2 — Repositório DynamoDB (`src/app/repository_financeiro.py`)

**What:** Lançamento na partição **mensal** da clínica. `PK=CLINIC#<clinicId>#FIN#<AAAA-MM>`
(mês derivado da `data` do lançamento, **não** de hoje), `SK=LANC#<id>`. Listagem por
Query + `begins_with`, **com loop de `LastEvaluatedKey`**, filtrando `ativo=True`. Update e soft
delete por condição. Chaves do GSI1 gravadas **só** quando há `pacienteId` (índice esparso).

**Where:** `src/app/repository_financeiro.py`, `tests/test_repository_financeiro.py`

**Reuses:** `repository_sessao.py` como molde (`_CAMPOS`, `update` com `SET` dinâmico,
soft delete por `ConditionExpression`, `_agora_iso`); `repository.py` (padrão de escrita das
chaves `GSI1PK`/`GSI1SK`).

**Done when:**
- `_pk(clinic_id, mes)` → `CLINIC#<clinicId>#FIN#<AAAA-MM>`; `_sk(id)` → `LANC#<id>`.
- ⚠️ **Desvio do desenho original:** a `data` saiu do SK. Com ela na chave, corrigir a data
  de um lançamento viraria put+delete (movimentação não-atômica de item) — inaceitável num
  livro-caixa. Ver a justificativa completa na spec, em "Data Model".
- `create(campos)` → dict com `id` uuid4; mês derivado de `campos["data"][:7]`.
- `list_mes(mes)` → lançamentos ativos do mês, **paginando** até acabar, ordenados por `data`.
- `get(mes, id)` / `update(mes, id, campos)` / `delete(mes, id)` (soft, `ativo=False`) → `None`/`False` quando não existe ou já está inativo.
- `GSI1PK`/`GSI1SK` presentes **só** com `pacienteId`; ausentes quando não há.

**Tests:** persistência PK/SK exata; mês vem da `data` (lançar 28/09 em outubro cai em `FIN#2026-09`);
`list_mes` ordenada por data; ignora inativos; ignora item de outro mês; paginação (>1 página) devolve tudo;
`update` altera e mexe em `atualizadoEm`; `delete` marca `ativo=False` **sem** apagar o item;
`delete` repetido → `False`; GSI1 esparso (com e sem `pacienteId`);
isolamento — repo de outra clínica não vê, não altera e não apaga.

**Requirements:** FIN-01, FIN-02, FIN-03, FIN-07, FIN-08, FIN-10, FIN-11, FIN-12

---

## C3 — Router + fiação (`src/app/routers/financeiro.py`, `main.py`)

**What:** Endpoints de nível clínica, **todos com `Depends(require_admin)`**. `GET` monta o caixa
do mês (lista + os três totais, somados só sobre ativos). `POST` cria. `PUT` edita, com `400` se a
`data` nova mudar de mês. `DELETE` cancela (soft).

**Where:** `src/app/routers/financeiro.py`, `src/app/main.py`, `tests/test_financeiro.py`

**Reuses:** `routers/aparelhos.py` como molde (router de nível clínica, `get_repository` com
`Depends(get_clinic_id)`); `routers/membros.py` (uso de `require_admin` como dependência de rota);
`routers/escala.py` (`_validar_chave`: converter `ValidationError` de path/query param no mesmo 400 legível);
handler global de `RequestValidationError` (`main.py`).

**Done when:**
- `APIRouter(prefix="/financeiro", tags=["financeiro"], dependencies=[Depends(require_admin)])` — o admin é exigido **no router**, não rota a rota (impossível esquecer numa rota nova).
- `GET "/lancamentos?mes=AAAA-MM"` → 200 `CaixaMesOut`; sem `mes` → mês corrente; `mes` inválido → 400.
- `POST "/lancamentos"` → 201 `LancamentoOut`.
- `PUT "/lancamentos/{mes}/{lancamento_id}"` → 200 | 404 | 400 (mudança de mês).
- `DELETE "/lancamentos/{mes}/{lancamento_id}"` → 200 `{"detail":"Lançamento cancelado"}` | 404.
- `main.py` inclui `financeiro.router`.

**Tests:** criar 201 + aparece no GET; totais (entradas, saídas, saldo) conferem; saldo negativo;
mês vazio → 200 com zeros; `mes` inválido → 400; mês corrente por padrão; cancelado some da lista **e** do total;
editar valor muda o total; editar mudando de mês → 400; editar/cancelar inexistente → 404;
**`role=membro` → 403 em todas as 4 rotas**; sem `custom:role` → 403; sem `clinicId` → 401;
isolamento entre clínicas (GET vazio, PUT/DELETE 404);
sem regressão em `/health`, `/pacientes`, `/aparelhos`, `/sessoes`, `/escala`.

**Requirements:** FIN-01, FIN-03, FIN-04, FIN-05, FIN-06, FIN-07, FIN-10, FIN-11

---

## C4 — Máscara de dinheiro (`frontend/src/utils/format.js`)

**What:** Três helpers puros para o dinheiro nunca virar float no front: máscara de digitação em
reais, centavos → texto BR, e texto BR → centavos.

**Where:** `frontend/src/utils/format.js`

**Reuses:** `onlyDigits` (já existe no arquivo) — a máscara é "só dígitos, dois últimos são os centavos",
o mesmo padrão de `maskCpf`/`maskTelefone`.

**Done when:**
- `maskMoeda(v)` → digitação progressiva (`"1"` → `"0,01"`, `"150"` → `"1,50"`, `"123456"` → `"1.234,56"`).
- `centavosParaBR(c)` → `"1.234,56"`; `0` → `"0,00"`; `null`/`undefined` → `"0,00"`.
- `brParaCentavos(s)` → inteiro (`"1.234,56"` → `123456`); vazio → `0`.
- `mesAnterior(mes)` / `mesSeguinte(mes)` → navegação `AAAA-MM` com virada de ano correta.
- `formatMesBR(mes)` → `"Outubro/2026"`.

**Requirements:** FIN-09 (parte)

---

## C5 — Front: aba "Financeiro" (`frontend/src/components/Financeiro.jsx`)

**What:** Tela do caixa mensal: cabeçalho com `‹ Outubro/2026 ›`, três totais (entradas, saídas,
saldo — saldo negativo em vermelho), tabela do extrato e formulário curto de lançamento.

**Where:** `frontend/src/components/Financeiro.jsx` (novo), `financeiroApi` em `frontend/src/api.js`

**Reuses:** padrões de `Escala.jsx`/`Pilates.jsx` (estado `.loading`/`.spinner`, bloco `.erro`,
`useEffect` de carregamento); `formatDataBR`/`hojeISO` de `utils/format.js`; classes `.card`,
`.tbl`, `.btn`, `.link.danger`, `.muted` já existentes no `App.css`.

**Done when:**
- Carrega o mês corrente ao abrir; `‹`/`›` trocam o mês sem recarregar a página.
- Três totais no topo; saldo negativo destacado.
- Formulário: tipo (entrada/saída), data (default hoje), valor com `maskMoeda`, descrição, forma de pagamento — envia **centavos inteiros**.
- Linha do extrato com data, descrição, forma, valor (verde/vermelho por tipo) e "cancelar" com confirmação.
- Mês sem lançamento → mensagem orientando o primeiro lançamento (não tabela vazia).
- Erro de API no bloco `.erro` **sem** limpar o formulário.
- **Mobile:** a tabela rola na horizontal (`overflow-x: auto`), como a grade da Escala.
- ⚠️ `type="button"` em todo botão dentro de form/estado alternante ([[react-button-type-swap-submit]]).

**Requirements:** FIN-09, FIN-01, FIN-03, FIN-04, FIN-10, FIN-11

---

## C6 — Fiação do front (`App.jsx`, `App.css`)

**What:** Aba "Financeiro" na navegação, **visível só para admin** (`clinic.role === "admin"`,
que já vem das claims em `clinicDasClaims`). Estilos dos cards de total.

**Where:** `frontend/src/App.jsx`, `frontend/src/App.css`

**Reuses:** o padrão de abas já existente (`aba === "escala" && <Escala …/>`); `clinic.role`, que o
`App.jsx` já deriva da claim `custom:role`.

**Done when:**
- Aba aparece para admin e **não** aparece para membro.
- `{aba === "financeiro" && <Financeiro clinic={clinic} />}`.
- Se um membro cair na aba por estado antigo, a API responde 403 e a tela mostra a mensagem — sem tela branca.
- `npm run build` e `npm run lint` sem erro novo.

**Requirements:** FIN-09, FIN-06

---

## Deploy — stack `clinica-pilates` + CloudFront (no terminal do usuário)

**What:** Back: `sam build --use-container` + `sam deploy` (ou o atalho sem Docker —
`requirements.txt` não mudou, ver ARQUITETURA.md). Front: `npm run build` + sync S3 + invalidação
do CloudFront. Smoke-test: lançar entrada e saída, conferir saldo, cancelar, trocar de mês,
e confirmar **403 com usuário membro**.

**Done when:** `/financeiro` no ar; aba funcionando no site; STATE.md/ROADMAP atualizados.

**Requirements:** FIN-01..12 Verified.

---

## Execution Log

| Task | Status | Commit | Notas |
| ---- | ------ | ------ | ----- |
| C1 — Schemas | ✅ Done | — | valor int em centavos (float e bool recusados), data que existe de verdade; **71 testes** |
| C2 — Repositório | ✅ Done | — | partição mensal vinda da `data`; `SK=LANC#<id>` (desvio: data fora do SK); soft delete; GSI1 esparso; paginação; **31 testes** |
| C3 — Router + fiação | ✅ Done | — | `require_admin` **no APIRouter** (rota nova nasce protegida); totais no back; **38 testes** (suíte 294 → **434**) |
| C4 — Máscara de dinheiro | ✅ Done | — | `maskMoeda`/`centavosParaBR`/`brParaCentavos` + navegação de mês; 21 casos conferidos no Node |
| C5 — Aba Financeiro | ✅ Done | — | totais, `‹ mês ›`, formulário, extrato, cancelar; `npm run build` OK |
| C6 — Fiação do front | ✅ Done | — | aba só com `isAdmin` (const que já existia no `App.jsx`); lint sem erro novo |
| Deploy | ⏳ | — | usuário (back sem mudança de infra + front no CloudFront) |

**Requirements coverage:** FIN-01..12 implementados; back coberto por **140 testes novos**
(suíte 294 → **434**, `pytest -q` verde).

⚠️ **Front NÃO verificado em browser nesta sessão** — mesma limitação da feature `escala`
(sem Playwright no ambiente automatizado). Verificação pendente: `cd frontend; npm run dev` →
aba **Financeiro** contra a API real. Ver [[front-verify-mock-sandbox]]. O que **está**
verificado: `npm run build`, `npm run lint` (só o mesmo aviso `exhaustive-deps` que todos os
outros componentes têm) e os helpers de dinheiro executados no Node (round-trip
centavos → texto → centavos sem perda).
