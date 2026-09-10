# Tasks — Fluxo de Caixa F2 (Mensalidades e Inadimplência)

Continuação de [`tasks.md`](tasks.md) (F1). Spec: [`spec-f2.md`](spec-f2.md).

**Status:** ✅ Implementada, verde e **em produção desde 2026-09-09**. ⏳ Teste de browser pendente.

**⚠️ Infra:** continua **sem alterar `template.yaml`** — o `GSI1` já existia e já era
esparso; a F2 só mudou o **conteúdo** das chaves que a F1 escrevia nele. Como a F1 **não
chegou a ser deployada**, essa mudança não custou migração nenhuma.

**Gate:** `.\.venv\Scripts\python.exe -m pytest -q` verde.

---

## D1 — Reindexar o GSI1 por competência (`repository_financeiro.py`)

**What:** A F1 indexava por aluno (`FIN#CLIENT#<pacienteId>` / `GSI1SK=<competencia>`).
A F2 reindexa por **competência**: `GSI1PK=CLINIC#<id>#FIN#COMP#<competencia>`,
`GSI1SK=<pacienteId>#<id>`. `list_por_paciente` vira `list_por_competencia`.

**Why:** A pergunta da tela é "quem pagou setembro?", e o pagamento de setembro pode ter
sido feito em outubro — mora na partição de **outubro**. Por competência: 1 Query.
Por aluno: uma Query por aluno (30-60 por carregamento de tela).

**Where:** `src/app/repository_financeiro.py`, `tests/test_repository_financeiro.py`

**Done when:**
- Índice exige `pacienteId` **E** `competencia` (aula avulsa de aluno fica fora — não é mensalidade).
- `<id>` no fim do `GSI1SK` (mesmo aluno pode pagar em duas parcelas).
- `update` que tira a competência **remove** as chaves do índice.

**Tests:** chaves exatas; sem competência fica fora; alcança outra partição mensal;
duas parcelas coexistem; cancelado sai; isolamento entre clínicas.

**Requirements:** FIN-17, FIN-20

---

## D2 — Repositório de Planos e Preços (`repository_plano.py`)

**What:** `SK=FIN#PLANO#<pacienteId>` e `SK=FIN#CONFIG`, ambos na **partição de nível
clínica** — todos os planos saem de 1 Query. `upsert` idempotente preservando `criadoEm`;
remoção física; `get_config` nunca devolve `None`.

**Where:** `src/app/repository_plano.py`, `tests/test_repository_plano.py`

**Reuses:** `repository_aparelho.py`/`repository_escala.py` (partição de nível clínica);
`repository_clinica.py` (item singleton `METADATA` como molde do `FIN#CONFIG`).

**Done when:**
- `list_all` pagina e **não** traz `FIN#CONFIG`, `METADATA`, `APARELHO#` nem `ESCALA#`.
- `Decimal` nunca vaza (conversão recursiva, inclusive dentro de `tabelaPrecos`).

**Tests:** 17 testes — chaves, idempotência, valor zero, paginação, isolamento, config padrão.

**Requirements:** FIN-13, FIN-16, FIN-20

---

## D3 — Schemas do plano e da tabela de preços (`schemas_plano.py`)

**What:** `PlanoUpsert` (valor **>= 0**, ao contrário do lançamento onde zero é erro),
`FaixaPreco`, `ConfigPrecos`, e os modelos de saída da tela (`MensalidadeAluno`,
`MensalidadesOut`).

**Where:** `src/app/schemas_plano.py`, `tests/test_schemas_plano.py`

**Done when:** float e `bool` recusados; `diaVencimento` 1..31; `frequencia` 1..7;
`observacao` <= 200; mensagens em PT-BR.

**Requirements:** FIN-13, FIN-16

---

## D4 — Rotas da F2 (`routers/financeiro.py`)

**What:** `GET /financeiro/mensalidades`, `PUT|DELETE /financeiro/planos/{pacienteId}`,
`GET|PUT /financeiro/config`. O cruzamento aluno × plano × pago acontece aqui.

**Where:** `src/app/routers/financeiro.py`, `tests/test_mensalidades.py`

**Done when:**
- A lista vem de `PacienteRepository.list_ativos()` — **não** da escala (funciona sem grade).
- Só `tipo=entrada` conta como pagamento (estorno com competência não quita).
- Em aberto somado **por aluno** (`max(0, valor - pago)`), para pagamento adiantado de um não mascarar a dívida de outro.
- `sem_plano` ≠ `isento`.
- Herdam o `require_admin` do `APIRouter` — nasceram protegidas sem uma linha a mais.
- **4 Queries fixas** por carregamento, nenhuma por aluno.

**Tests:** 45 testes — os 5 status, totais, atrasado na competência certa, cancelamento,
divergência com a escala, validações, 403 para membro, isolamento entre clínicas.

**Requirements:** FIN-14, FIN-15, FIN-17, FIN-18, FIN-20

---

## D5 — Front: tela de Mensalidades (`Mensalidades.jsx`)

**What:** Previsto/recebido/em aberto + tabela de alunos com status colorido, formulário
de plano inline (frequência pré-preenche o valor pela tabela de preços) e "dar baixa".

**Where:** `frontend/src/components/Mensalidades.jsx`, `financeiroApi` em `api.js`

**Done when:**
- Dar baixa manda `data = hoje` e `competencia = mês exibido` (os dois separados).
- Chip "⚠ grade: Nx" quando há divergência.
- ⚠️ `<Fragment key>` em vez de `<>` (fragmento curto não aceita `key` — quebra a lista).

**Requirements:** FIN-14, FIN-15, FIN-17, FIN-18

---

## D6 — Front: tabela de preços e sub-abas (`TabelaPrecos.jsx`, `Financeiro.jsx`)

**What:** Sub-abas **Caixa | Mensalidades | Preços** dentro da aba Financeiro, com o mês
como estado do **shell** (trocar de sub-aba mantém o mês). Tela de preços com o
"≈ por aula" **calculado e read-only** (÷ 4,33).

**Where:** `frontend/src/components/TabelaPrecos.jsx`, `Financeiro.jsx`, `App.css`

**Requirements:** FIN-16, FIN-14

---

## D7 — Marcador de inadimplente na Escala (`Escala.jsx`)

**What:** Ponto vermelho no chip do aluno que está devendo o mês corrente, com o valor no
`title`. **É o diferencial do produto:** o financeiro aparece onde a recepção já olha.

**Where:** `frontend/src/components/Escala.jsx`, `App.css`

**Done when:**
- Só busca a inadimplência se `clinic.role === "admin"` (membro tomaria 403).
- Falha da chamada **não** derruba a grade (catch próprio e silencioso) — o marcador é
  extra, a grade é o que a recepção veio ver.

**Requirements:** FIN-19

---

## D8 — Ajustes do feedback do usuário (front)

**What:** Três correções depois do primeiro teste na tela.

**1. Caixa não refletia a baixa sem F5 (bug).** O `Financeiro` é o shell e **não desmonta**
ao trocar de sub-aba — só o conteúdo muda. Então o `useEffect` que carrega o caixa
(`[clinic.id, mes]`) nunca reexecutava quando a aba Mensalidades criava um lançamento.
Corrigido com um contador `recarga` nas dependências, incrementado por um callback
(`aoMexerNoCaixa`) que a tela de Mensalidades dispara após registrar o pagamento.
O caminho inverso já funcionava por acaso: a `Mensalidades` **desmonta** ao sair da
sub-aba, então remonta e recarrega sozinha.

**2. Forma de pagamento na baixa.** O pagamento ia com `formaPagamento: null`, deixando o
extrato incoerente (recebimento lançado na mão tinha forma, o vindo da baixa não). A lista
de formas saiu de dentro do `Financeiro.jsx` para `utils/format.js` (`FORMAS_PAGAMENTO` +
`labelForma`), porque agora **duas telas** precisam exatamente das mesmas opções — e essa
lista espelha a que o backend valida.

**3. Filtros na tela de Mensalidades.** Busca por nome **sem acento** (`NFD` + remoção do
bloco de diacríticos combinantes), filtro por situação e por dia de vencimento. O combo de
vencimento oferece só os dias em uso. Os três totais do topo **continuam sendo os do mês
inteiro**: filtrar muda a visão, não a verdade do mês.

**Where:** `frontend/src/components/Financeiro.jsx`, `Mensalidades.jsx`,
`frontend/src/utils/format.js`, `App.css`

**Done when:** baixa aparece no Caixa na hora; forma vai no lançamento; filtros combinam
entre si; "N de M" e "limpar filtros" quando filtrando; vazio-por-filtro tem mensagem
própria.

⚠️ **Armadilha de encoding:** o range de diacríticos combinantes da regex de busca
precisa ficar como **sequência de escape ASCII** (`U+0300`–`U+036F` escritos com barra-u)
no fonte. Escrito com os caracteres literais (que é o que várias
ferramentas de edição produzem) ela funciona, mas fica invisível no editor e some numa
conversão de encoding. Conferido: a linha é ASCII puro.

**Requirements:** FIN-21, FIN-22

---

## Execution Log

| Task | Status | Commit | Notas |
| ---- | ------ | ------ | ----- |
| D1 — GSI1 por competência | ✅ Done | — | mudança sem custo: a F1 não tinha sido deployada; 32 testes |
| D2 — Repositório de planos/preços | ✅ Done | — | plano na partição da clínica (1 Query na tela); 17 testes |
| D3 — Schemas | ✅ Done | — | valor **zero é válido** aqui (bolsista); 30 testes |
| D4 — Rotas da F2 | ✅ Done | — | 4 Queries fixas; em aberto somado por aluno; 45 testes |
| D5 — Tela de Mensalidades | ✅ Done | — | `npm run build` OK |
| D6 — Preços + sub-abas | ✅ Done | — | por-aula derivado, nunca digitado |
| D7 — Marcador na Escala | ✅ Done | — | degrada em silêncio para membro |
| D8 — Ajustes do feedback | ✅ Done | — | bug do Caixa desatualizado; forma de pagamento na baixa; filtros (nome/situação/vencimento) |
| Deploy | ✅ Done | — | **no ar 2026-09-09**: back via atalho sem Docker + front no CloudFront |

**Requirements coverage:** FIN-13..20 implementados. Suíte **434 → 540 testes** (106 novos),
`pytest -q` verde em **115s**.

🐞 **Bug encontrado pelo próprio smoke-test (D6):** o "≈ por aula" da tabela de preços
dividia o mensal só pelas semanas do mês, esquecendo a frequência — 2x/semana aparecia como
R$ 60,05 em vez de R$ 30,02. Só o caso 1x saía certo, por coincidência. Corrigido.

⚠️ **Front NÃO verificado em browser nesta sessão** (mesma limitação da F1 e da `escala`).
O que **está** verificado: `npm run build`, `npm run lint` sem erro, e todos os fluxos
exercitados via API contra o servidor local (os 5 status, a mensalidade atrasada caindo na
competência certa e no caixa do mês certo, e a divergência com a grade).

📝 **Nota de ambiente:** rodar duas suítes completas ao mesmo tempo com o uvicorn e o vite
de pé fez a suíte levar **1h43** em vez de 115s (contenção de RAM — ver
[[maquina-ram-limitada-docker]]). Rodar uma de cada vez.
