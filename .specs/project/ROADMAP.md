# Roadmap

**Current Milestone:** **Produção** — sistema no ar em https://pilatesone.com.br com **cliente real usando**
**Status:** M1, M2 e M3 concluídos. Login real (Cognito), domínio próprio e todas as features de prontuário
no ar. Próximo foco: front definitivo (spec "impecable", M4) com o feedback do cliente real.

---

## 🎯 Rota do Demo — ✅ CONCLUÍDA (superada pela produção)

**Objetivo (cumprido):** ter algo visual pra mostrar pro cliente cedo, validar a ideia e
destravar a venda. Deu certo: virou cliente real.

1. ✅ **Cadastro de Aparelhos** — deployado (APR-01..09, 96 tests)
2. ✅ ~~Login simples (seletor de clínica, `X-Clinic-Id`)~~ — **substituído pelo Cognito** no M3
3. ✅ **Front leve (demo)** — React+Vite, no ar
4. ✅ **DEMO pro cliente** — feito
5. ✅ **Pós-demo:** Cognito real + Registro de Sessões + Imagens — todos entregues

---

## M1 — Fundação + CRUD de Pacientes

**Goal:** Ter a infraestrutura serverless base provisionada e um CRUD de pacientes funcional end-to-end (API).
**Target:** Primeira versão utilizável do backend.

### Features

**Infraestrutura base (SAM)** - COMPLETE

- Template SAM com Lambda, API Gateway (proxy) e tabela DynamoDB
- Deploy via `sam deploy` (stack `clinica-pilates` no ar, us-east-1)
- Configuração de CORS
- Verificado: `GET /health` → `{"status":"ok"}`

**CRUD de Pacientes** - COMPLETE

- Modelagem da entidade Paciente no DynamoDB (single-table, `SK=PROFILE`)
- Endpoints: criar, listar, obter, editar, remover (soft delete) paciente
- Backend FastAPI + Mangum com roteamento interno em uma Lambda
- Validação via Pydantic
- 45 testes verdes (schemas + repositório com moto + endpoints); PAC-01..09 Verified
- ✅ Deployado na stack `clinica-pilates` (2026-07-20); smoke-test público OK

**Milestone M1 CONCLUÍDO** ✅

---

## M2 — Aparelhos e Registro de Sessões

**Goal:** Registrar, por paciente, os aparelhos utilizados em cada sessão (core do produto).
Cada clínica mantém seu próprio catálogo de aparelhos (multi-tenant, AD-007).

### Features

**1. Cadastro de Aparelhos (por clínica)** - COMPLETE ✅ (deployado 2026-07-21)

- Catálogo de aparelhos próprio de cada clínica (A pode ter o que B não tem)
- Modelagem: `PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>` (nível clínica, não paciente)
- Listagem por Query direto na PK da clínica (sem GSI necessário)
- CRUD (criar, listar, editar, remover — soft delete). APR-01..09 Verified, 96 tests
- ✅ Deployado; smoke-test público OK (CRUD + isolamento entre clínicas)

**2. Avaliação dos Pacientes (ficha clínica datada)** - COMPLETE ✅ (deployado 2026-07-22)

- Histórico de avaliações por paciente: `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=AVALIACAO#<id>` (AD-010)
- Campos (texto livre, opcionais): diagnósticoMédico, queixaPrincipal, HMA, PA, FC, avaliação postural (4 vistas, MAP), medidas (braço/abdômen/coxa/panturrilha, MAP), inspeção geral, exames complementares. `data` default hoje
- Endpoints aninhados `/pacientes/{id}/avaliacoes` (CRUD, soft delete); 404 se paciente inexistente na clínica
- AVL-01..10 Verified, 38 testes (suíte 135). Smoke-test público OK (ciclo + isolamento + validações)
- ✅ **Front no ar**: tela de Avaliações por paciente (link "avaliações" na linha) publicada no CloudFront

**3. Registro de Sessões (Aula de Pilates)** - COMPLETE ✅ (back deployado + front no CloudFront, 2026-07-27)

- Modelagem aula sob o paciente: `PK=CLINIC#<clinicId>#CLIENT#<clientId>`, `SK=SESSION#<id>` (id no SK, como AD-010)
- Aula = data + `aparelhos` (lista de maps `{aparelhoId, nome, treinos[]}`, snapshot ≥1) + `observacao` + `profissional`
- Tipos de treino = lista fixa hardcoded no front (Membros superiores/inferiores, Abdômen, Força, Mobilidade); back guarda snapshot de texto
- Endpoints aninhados `/pacientes/{id}/sessoes` (CRUD, soft delete, 404 se paciente inexistente na clínica). SES-01..11
- Back: S1 schemas + S2 repo + S3 router, **44 testes novos (suíte 180)**, deployado; smoke-test público OK
- ✅ Front (aba "Pilates", `components/Pilates.jsx`): registrar + consulta datada/editar/remover — **NO AR**

**4. Imagens do Paciente** - COMPLETE ✅ (back + front no ar, 2026-08-07)

- Painel de até **5 imagens por paciente** (não por consulta) no rodapé da ficha
- Binário no **S3 privado**; a Lambda só assina **URLs pré-assinadas** (5 min) — o arquivo nunca passa pela API
- Metadado `SK=IMAGE#<id>` sob a PK do paciente → a ficha carrega tudo em 1 Query
- Upload em **2 fases** (`POST` presigned → browser sobe → `PUT` confirma via `head_object`), sem órfãos no Dynamo
- IMG-01..09 Verified, **18 testes novos (suíte 219)**; end-to-end no browser aprovado

**Milestone M2 CONCLUÍDO** ✅

---

## M3 — Autenticação da Equipe — CONCLUÍDO ✅ (2026-07-28)

**Goal:** Proteger o sistema com login da equipe da clínica.

### Features

**Login simples (pré-demo)** - SUPERSEDED

- Era o seletor de clínica enviando `X-Clinic-Id` (andaime do demo)
- **Removido:** o `clinicId` agora vem da claim do token

**Login com Cognito** - COMPLETE ✅ (deployado e no ar)

- User Pool `us-east-1_tusTZNRL6`, App Client SPA `6cke2rskmcq3ogim7c7ns4qqbn`
- Sem auto-cadastro público (`AllowAdminCreateUserOnly`); convite por e-mail em PT-BR com a marca Pilates One
- **JWT Authorizer** no API Gateway valida o token na borda (`401` antes da Lambda); só `GET /health` é público
- `get_clinic_id()` lê `custom:clinicId` do token — o usuário não consegue escrever esse atributo (AD-012)
- Endpoint `/membros` (admin adiciona equipe, herda a clínica do token)
- ✅ Verificado end-to-end na stack real; **1º cliente real logado e cadastrando**

**Milestone M3 CONCLUÍDO** ✅

---

## M4 — Frontend + Domínio

**Goal:** Interface web publicada em domínio próprio.

### Features

**Front leve (demo)** - COMPLETE ✅

- React + Vite; abas Pacientes / Aparelhos / Pilates, ficha com Avaliações e Imagens
- Publicado em S3 + CloudFront (stack `clinica-pilates-frontend`)

**Domínio + SSL** - COMPLETE ✅

- **https://pilatesone.com.br** no ar com HTTPS

**Frontend definitivo (spec "impecable")** - PLANNED ← **próximo foco**

- Especificação "impecable" escrita **com o feedback do cliente real** (que já está usando)
- Implementação da SPA definitiva sobre a mesma API

---

## M5 — Financeiro (Fluxo de Caixa)

**Goal:** O sistema deixar de saber só do atendimento e passar a saber do dinheiro — começando
pelo livro-caixa mensal e terminando na mensalidade por aluno com inadimplência visível.
**Target:** A clínica abandonar o caderno/planilha paralela.

### Features

**F1 — Livro-caixa mensal** - COMPLETE (código) ⏳ deploy pendente

- Lançar entrada/saída, extrato do mês, entradas/saídas/saldo calculados no backend
- Editar e cancelar (soft delete — histórico financeiro não se apaga)
- Partição mensal `CLINIC#<id>#FIN#<AAAA-MM>`; dinheiro em **centavos inteiros**, nunca float (AD-014)
- **Restrito a admin** (`require_admin` no `APIRouter`): 403 para membro em todas as rotas
- FIN-01..12; **140 testes** novos (suíte 294 → **434**); `template.yaml` **não muda**
- Front: aba **Financeiro** (só admin), navegação de mês, máscara de reais

**F2 — Mensalidade por aluno e inadimplência** - COMPLETE (código) ⏳ deploy pendente ← **o diferencial**

- Plano do aluno (`SK=FIN#PLANO#<pacienteId>`, na partição da clínica) + tabela de preços por frequência
- Tela de mensalidades: **previsto × recebido × em aberto**, com os 5 status por aluno
  (pago / parcial / em aberto / isento / sem plano)
- **Dar baixa em 1 clique**: `data` = hoje, `competencia` = mês exibido → a mensalidade atrasada
  cai no caixa do mês em que o dinheiro entrou E quita a competência certa
- **Marcador de inadimplente na aba Escala** — o financeiro aparece onde a recepção já olha
- Aviso de **divergência** plano × grade ("paga 2x, está em 3 horários")
- Preço de aula avulsa e de reposição (esses sim por aula); o "por aula" do mensalista é
  **calculado e read-only**, nunca digitado
- Princípio fixado: **a Escala nunca é fonte da verdade do valor** — a fonte é o plano do aluno no
  cadastro. Tudo funciona numa clínica que não usa a Escala (a lista vem do cadastro de pacientes)
- GSI1 reindexado por **competência** (AD-015) — sem migração, a F1 não tinha sido deployada
- FIN-13..20; **106 testes** novos (suíte 434 → **540**); `template.yaml` **não muda**

**F3 — Relatório** - PLANNED

- Categorias de despesa, comparativo mês a mês, gráfico
- Export CSV para o contador
- Custo real por aula (despesas ÷ aulas registradas)

---

## Future Considerations

- ~~Upload de fotos, laudos e anexos por paciente (S3)~~ — ✅ **entregue** (Imagens do Paciente, M2/4)
- Relatórios/estatísticas de uso de aparelhos
- **Paginação da listagem de pacientes** — hoje 1 query sem loop de `LastEvaluatedKey`; trunca em silêncio a partir de ~1.000–1.500 perfis (adiado pelo usuário)
- Exportação de dados dos pacientes
- **Mobile** (mesma API): via PWA (front web responsivo/instalável) ou app nativo (React Native/Flutter). Backend já serve — não precisa refazer.
- Papéis/permissões dentro da clínica (roles via Cognito groups) — pós-Cognito
- Onboarding self-service de nova clínica (cria clinicId + admin)
