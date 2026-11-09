# Relatórios Tasks

**Design**: `.specs/features/relatorios/design.md`
**Status**: Done — no ar em 2026-11-09 (falta só medir o REL-19 com uso real)

---

## Execution Plan

### Fase 1: Back, base (paralelo OK)

```
T1 [P]   mensalidades.py (extração)
T2 [P]   PacienteRepository: list_todos + paginar list_ativos
T3 [P]   repository_atendimento.py
T4       relatorios.py: base + financeiro + extrato
           ──→ T5 alunos + relação ──→ T6 ocupação ──→ T7 atendimento ──→ T8 semana
```
T1, T2, T3 e T4 não dependem entre si. T4→T8 são sequenciais porque mexem no mesmo arquivo.

### Fase 2: Back, API (sequencial)

```
T1,T2,T3,T8 ──→ T9 schemas_relatorio ──→ T10 router /relatorios (6 GETs + main)
```

### Fase 3: Front (paralelo parcial)

```
T10 ──→ T11 relatoriosApi
T12 [P] graficos.jsx              (não depende do back)
T11,T12 ──→ T13 RelFinanceiro      ─┐
            T14 RelAlunos          ─┤
            T15 RelRelacaoAlunos   ─┤  (T13–T18 [P] entre si)
            T16 RelOcupacao        ─┤
            T17 RelAtendimento     ─┤
            T18 RelSemana          ─┘──→ T19 Relatorios.jsx + aba ──→ T20 impressão ──→ T21 fechamento (P2)
```

### Fase 4: Verificação e entrega (sequencial)

```
T21 ──→ T22 verificação visual + PDFs (Playwright mock) ──→ T23 deploy + smoke + docs
```

---

## Task Breakdown

### T1: Extrair `calcular_mensalidades` [P]
**What**: mover a lógica de `mensalidades_do_mes` (e `_status`) para `src/app/mensalidades.py::calcular_mensalidades(alunos, planos, lancamentos_competencia, escala)`. O router financeiro passa a chamar a função.
**Where**: `src/app/mensalidades.py` (novo), `src/app/routers/financeiro.py`, `tests/test_mensalidades_calculo.py`
**Depends on**: None · **Reuses**: código atual do router · **Requirement**: REL-06
**Done when**: [ ] router só busca e delega · [ ] `test_mensalidades.py` inalterado e verde · [ ] teste unit da função pura (pago/parcial/aberto/isento/sem plano)
**Tests**: unit · **Gate**: quick

### T2: `PacienteRepository.list_todos()` + paginar `list_ativos` [P]
**What**: novo `list_todos` (GSI1 sem filtro, paginado) e `list_ativos` com paginação (PENDENCIAS 1.3).
**Where**: `src/app/repository.py`, `tests/test_repository.py`
**Depends on**: None · **Reuses**: padrão de paginação de `repository_financeiro.list_mes` · **Requirement**: REL-07, REL-13, REL-21
**Done when**: [ ] `list_todos` devolve ativos e removidos · [ ] as duas não veem outra clínica · [ ] paginação coberta (itens grandes no moto forçando mais de uma página) · [ ] testes existentes de pacientes verdes
**Tests**: unit (moto) · **Gate**: quick

### T3: `repository_atendimento.list_sessoes_periodo` [P]
**What**: Queries em paralelo (ThreadPoolExecutor, 16 workers, client boto3 + TypeDeserializer) das aulas ativas de N alunos com `data` entre `de` e `ate`. Cada item volta com `pacienteId`.
**Where**: `src/app/repository_atendimento.py` (novo), `tests/test_repository_atendimento.py`
**Depends on**: None · **Reuses**: chaves de `repository_sessao.py` · **Requirement**: REL-13, REL-19, REL-22
**Done when**: [ ] filtra período e `ativo` · [ ] ignora avaliações e imagens sob a mesma PK · [ ] isolamento: ids de outra clínica não retornam nada · [ ] lista vazia de ids devolve `[]` sem chamar o DynamoDB
**Tests**: unit (moto) · **Gate**: quick

### T4: `relatorios.py`: base + financeiro + extrato
**What**: `mes_local`, `meses_ate`, `resumo_caixa`, `receita_por_forma`, `resumo_mensalidades`, `extrato`.
**Where**: `src/app/relatorios.py` (novo), `tests/test_relatorios.py`
**Depends on**: None · **Requirement**: REL-03..06, REL-20
**Done when**: [ ] `meses_ate` atravessa a virada de ano · [ ] `mes_local("2026-10-01T01:30:00Z") == "2026-09"` · [ ] `cartao` e sem forma rotulados · [ ] pct ~100 · [ ] extrato na ordem do Caixa e com soma = saldo · [ ] listas vazias dão zeros
**Tests**: unit · **Gate**: quick

### T5: `relatorios.py`: alunos + relação
**What**: `indicadores_alunos`, `evolucao_alunos`, `carteira_planos`, `relacao_alunos`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T4 · **Requirement**: REL-07..10, REL-21
**Done when**: [ ] regras de novo/saída/ativo-no-fim · [ ] criado e removido no mesmo mês · [ ] planos de removidos fora · [ ] ticket médio sem isentos · [ ] relação em ordem alfabética, com plano/isento/sem plano e horários "Seg 07:00" em ordem
**Tests**: unit · **Gate**: quick

### T6: `relatorios.py`: ocupação
**What**: `ocupacao(matriculas, alunos_ativos)`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T5 · **Requirement**: REL-11, REL-12
**Done when**: [ ] contagem por célula · [ ] top 5 com desempate · [ ] média só sobre horários ocupados · [ ] fora da escala · [ ] órfã ignorada · [ ] grade vazia dá zeros
**Tests**: unit · **Gate**: quick

### T7: `relatorios.py`: atendimento (Pilates + Agenda)
**What**: `meses_agenda_disponiveis(meses, agora)` (via `expira_em`) e `atendimento(sessoes, agenda, perfis, mes, meses, disponiveis)`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T6 · **Reuses**: `repository_agenda.expira_em` · **Requirement**: REL-13..15
**Done when**: [ ] as duas fontes separadas, nunca somadas · [ ] mês da Agenda expirado = `null` (não 0) · [ ] por profissional por id, com fallback de texto e "Sem profissional" · [ ] por aluno com marcação de aluno novo pelo nome (`novo=true`) · [ ] aparelho 1 por aula · [ ] treinos · [ ] snapshot preservado
**Tests**: unit · **Gate**: quick

### T8: `relatorios.py`: semana
**What**: `segunda_da_semana(data)`, `semana(sessoes, agenda, perfis, inicio, agenda_disponivel)`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T7 · **Requirement**: REL-22
**Done when**: [ ] dias 1..7 com contagem por fonte · [ ] ordem alfabética · [ ] distintos/totais · [ ] semana atravessando a virada do mês/ano · [ ] `agendaDisponivel=false` zera a parte da Agenda e sinaliza
**Tests**: unit · **Gate**: quick

### T9: `schemas_relatorio.py`
**What**: os 6 modelos de saída do design.
**Where**: `src/app/schemas_relatorio.py`
**Depends on**: T8 · **Requirement**: REL-03..22
**Done when**: [ ] modelos batem com as saídas das funções (validados pelos testes de T10)
**Tests**: unit (coberto via endpoints em T10) · **Gate**: build

### T10: Router `/relatorios` + registro no `main.py`
**What**: `financeiro`, `alunos`, `relacao-alunos`, `ocupacao`, `atendimento`, `semana`, com `require_admin` no APIRouter e validação de `?mes=` / `?inicio=` (inválido, futuro ou não-segunda = 400; ausente = atual em UTC−3).
**Where**: `src/app/routers/relatorios.py` (novo), `src/app/main.py`, `tests/test_relatorios_api.py`
**Depends on**: T1, T2, T3, T9 · **Requirement**: REL-01..22
**Done when**: [ ] membro recebe 403 nos 6 · [ ] **isolamento** A/B nos 6 · [ ] o Financeiro bate com `/financeiro/lancamentos` e `/mensalidades` · [ ] a Agenda entra no Atendimento e na Semana · [ ] clínica vazia dá 200 com zeros nos 6 · [ ] 400 para mês/semana futuros ou inválidos · [ ] suíte inteira verde
**Tests**: unit (moto) · **Gate**: full

### T11: `relatoriosApi` no front
**Where**: `frontend/src/api.js` · **Depends on**: T10 · **Requirement**: REL-01
**Done when**: [ ] 6 chamadas · [ ] build e lint sem erro novo
**Tests**: none · **Gate**: build (npm)

### T12: `graficos.jsx` [P]
**What**: `Kpi`, `BarrasMensais` (aceita `null` = "sem dados", desenhado diferente de zero), `Ranking`, `MapaCalor`. SVG/CSS próprios, legíveis em P&B.
**Where**: `frontend/src/components/relatorios/graficos.jsx`, `App.css` (`rel-*`)
**Depends on**: None · **Tools**: Skill **dataviz** (carregar antes) · **Requirement**: REL-04, 08, 11, 13, 16 AC4
**Done when**: [ ] valores escritos · [ ] 12 meses a 390 px · [ ] build e lint OK
**Tests**: none · **Gate**: build (npm)

### T13–T18: componentes de apresentação [P]
Um arquivo cada em `frontend/src/components/relatorios/`, `({dados, ...})`, com estado vazio e as notas da spec. **Tools**: Skill dataviz. **Depends on**: T11, T12. **Tests**: none · **Gate**: build (npm).
| Task | Arquivo | Requirement | Done when (além de build/lint) |
|---|---|---|---|
| T13 | `RelFinanceiro.jsx` | REL-03..06, REL-20 | KPIs, evolução, formas, mensalidades, **extrato** com total |
| T14 | `RelAlunos.jsx` | REL-07..10 | KPIs, evolução, carteira, novos do mês |
| T15 | `RelRelacaoAlunos.jsx` | REL-21 | tabela completa + total, nota "retrato de hoje" |
| T16 | `RelOcupacao.jsx` | REL-11, 12 | mapa de calor + top 5 + fora da escala + nota "grade atual" |
| T17 | `RelAtendimento.jsx` | REL-13..15 | duas fontes separadas, "sem dados" na Agenda expirada, aviso "marcação ≠ comparecimento" |
| T18 | `RelSemana.jsx` | REL-22 | "‹ semana ›", tabela aluno × dias com ● aula / ○ Agenda + legenda, resumo, aviso de retenção |

### T19: `Relatorios.jsx` + aba no `App.jsx`
**What**: container com sub-abas (Financeiro · Alunos [Indicadores | Relação] · Ocupação · Atendimento · Semana), seletor de mês só onde se aplica ("›" travado no atual), carregamento/erro/tentar de novo. Aba só admin depois de Financeiro. Exportar `DIAS`/`HORARIOS` do `Escala.jsx` se preciso.
**Where**: `frontend/src/components/Relatorios.jsx`, `frontend/src/App.jsx`
**Depends on**: T13–T18 · **Requirement**: REL-01, 02, 18
**Done when**: [ ] membro não vê a aba · [ ] troca de mês recarrega · [ ] Relação, Ocupação e Semana sem seletor de mês · [ ] build e lint OK
**Tests**: none · **Gate**: build (npm)

### T20: Impressão por relatório
**What**: `CabecalhoImpressao`, botão "Imprimir / PDF" + dica "Salvar como PDF", bloco `@media print` (A4, sem menus, `thead` repetido, quebras, `print-color-adjust`).
**Where**: `relatorios/CabecalhoImpressao.jsx`, `Relatorios.jsx`, `App.css`
**Depends on**: T19 · **Requirement**: REL-16, REL-21 AC3, REL-22 AC5
**Done when**: [ ] `page.pdf` (Playwright) sem topbar/abas, com cabeçalho, sem coluna cortada; extrato e relação longos quebram página com o cabeçalho da tabela repetido
**Tests**: none (visual em T22) · **Gate**: build (npm)

### T21: Fechamento do mês (P2)
**What**: botão "Fechamento do mês", `allSettled` dos 4 do mês (Financeiro com extrato, Alunos indicadores, Ocupação, Atendimento), capa, `.rel-secao` com quebra de página, print e desmontagem no `afterprint`. Aborta com aviso se um grupo falhar.
**Where**: `Relatorios.jsx` (ou `relatorios/Fechamento.jsx`), `App.css`
**Depends on**: T20 · **Requirement**: REL-17
**Done when**: [ ] PDF com capa + 4 seções em páginas novas · [ ] falha simulada dá aviso e não imprime · [ ] build e lint OK
**Tests**: none (visual em T22) · **Gate**: build (npm)

### T22: Verificação visual (Playwright + API mockada)
**What**: prints desktop/celular dos 6 relatórios (com dados e vazios), PDFs (Financeiro com extrato longo, Relação longa, Semana, fechamento), aba escondida para membro. Segue [[front-verify-mock-sandbox]].
**Where**: scratchpad · **Depends on**: T21 · **Requirement**: REL-01, 16, 17, 18, 21, 22
**Done when**: [ ] prints e PDFs conferidos · [ ] ajustes aplicados
**Tests**: none · **Gate**: visual

### T23: Deploy + smoke + documentação
**What**: back pelo atalho sem Docker (changeset só `Modify ClinicaApiFunction`, **sem** `ClinicaTable` e sem Cognito), front com `deploy-front.ps1`, smoke (`/relatorios/*` sem token dá 401; com admin real, tempo do Atendimento < 5 s, REL-19). Atualizar STATE/ROADMAP/ARQUITETURA/TESTING e **PENDENCIAS** (seção 6 atendida, item 1.3 parcial: `list_ativos` de pacientes paginado).
**Depends on**: T22 · **Requirement**: REL-19 + entrega
**Done when**: [ ] no ar · [ ] < 5 s · [ ] docs · [ ] commit
**Tests**: none · **Gate**: smoke

---

## Validação pré-aprovação

### Check 1: Granularidade
| Task | Entrega única? | OK |
|---|---|---|
| T1–T3 | 1 módulo/método cada (T2 = dois métodos irmãos, mesma mudança de paginação) | ✅ |
| T4–T8 | 1 grupo de funções cada (mesmo arquivo, por isso sequenciais) | ✅ |
| T9, T10 | schemas / router | ✅ |
| T11, T12 | api / gráficos | ✅ |
| T13–T18 | 1 componente cada | ✅ |
| T19–T21 | container / impressão / fechamento | ✅ |
| T22, T23 | verificação / entrega | ✅ |

### Check 2: Diagrama × Depends on
| Task | Depends on | No diagrama | OK |
|---|---|---|---|
| T1, T2, T3, T4 | None | Fase 1, sem entrada | ✅ |
| T5 / T6 / T7 / T8 | T4 / T5 / T6 / T7 | cadeia T4→T5→T6→T7→T8 | ✅ |
| T9 | T8 | "T1,T2,T3,T8 → T9" | ✅ |
| T10 | T1, T2, T3, T9 | T1, T2, T3 → (T9) → T10 | ✅ |
| T11 | T10 | T10 → T11 | ✅ |
| T12 | None | sem entrada | ✅ |
| T13–T18 | T11, T12 | T11, T12 → T13–T18 | ✅ |
| T19 | T13–T18 | → T19 | ✅ |
| T20 / T21 / T22 / T23 | T19 / T20 / T21 / T22 | cadeia | ✅ |

### Check 3: Testes co-localizados (TESTING.md)
| Task | Camada | Exigido | Na task | OK |
|---|---|---|---|---|
| T1 | lógica de negócio + endpoint existente | unit | unit + suíte existente | ✅ |
| T2, T3 | repositório DynamoDB | unit (moto) + isolamento | unit (moto) + isolamento | ✅ |
| T4–T8 | lógica de negócio pura | unit | unit | ✅ |
| T9 | modelos Pydantic | unit | coberto via T10 | ✅ |
| T10 | endpoints + isolamento | unit (moto) | unit (moto) + isolamento + 403 | ✅ |
| T11–T21 | front | sem framework de teste no front (TESTING.md cobre só o back) | build + lint, visual em T22 | ✅ |
| T23 | deploy | none | smoke | ✅ |

**Paralelismo**: unit (moto) é parallel-safe, então `[P]` em T1–T3 vale. T12–T18 são de front sem testes, então o `[P]` depende só do código.
