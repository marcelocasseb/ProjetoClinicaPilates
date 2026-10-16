# Pendências

Melhorias de desempenho, confiabilidade, backup e rastreio levantadas em 28/09/2026.
Nada disto está quebrado hoje; são os pontos que vão doer quando entrarem mais clínicas.

**Retrato em 28/09/2026:** 4 clínicas, 7 usuários, 317 itens (160 KB) na tabela, cerca de 1.075
chamadas à API em 30 dias, 0 erros e 0 chamadas recusadas. Metade das respostas sai em até 0,3 s,
e 5% levam cerca de 1,9 s (a Lambda "acordando").

**Já feito em 28/09/2026 (commit `f2f4884`):** backup contínuo (PITR) na tabela e log de acesso
da API em `/clinica-pilates/api-access`, guardado por 1 ano.

---

## 1. Desempenho e capacidade

### 1.1 ~~Aumentar o limite de execuções simultâneas da Lambda~~ (CONCLUÍDO)
- **Problema:** a conta da AWS está com o limite de uma conta nova, **10 execuções simultâneas**
  (o normal é 1.000). O pico dos últimos 30 dias já foi 5. Com umas 20 a 40 pessoas clicando ao
  mesmo tempo, as chamadas passam a ser recusadas e o usuário vê erro.
- **Como fazer:** Console AWS → Service Quotas → AWS services → AWS Lambda → *Concurrent
  executions* → Request increase → 1000 (região us-east-1). É gratuito e costuma sair em 1 ou 2 dias.
- **Conferir:** `aws lambda get-account-settings --region us-east-1` (o `ConcurrentExecutions`
  deve mostrar 1000).
- **Status:** aumento solicitado em 29/09/2026 e aprovado; conferido em 16/10/2026
  (`ConcurrentExecutions` = 1000).

### 1.2 Subir a memória da Lambda de 256 MB para 512 ou 1024 MB
- **Problema:** a Lambda leva de 1,1 a 1,4 s para iniciar; é por isso que 5% das chamadas levam
  cerca de 2 s.
- **Como fazer:** `MemorySize` em `Globals` no [template.yaml](template.yaml). Mais memória também
  dá mais processamento, então inicialização e chamadas ficam mais rápidas. O custo quase não muda.
- **Depois:** comparar a duração dos 5% mais lentos (p95) no CloudWatch, antes e depois.

### 1.3 Paginar as listas no DynamoDB
- **Problema:** o DynamoDB entrega no máximo 1 MB por busca. As listas abaixo leem só a primeira
  página, e o que passa disso **some sem aviso** (por exemplo, a clínica deixa de ver parte dos pacientes).
- **Precisa paginar** (repetir a busca usando `LastEvaluatedKey` até acabar):
  - [src/app/repository.py](src/app/repository.py): `list_ativos` (lista de pacientes)
  - [src/app/repository_sessao.py](src/app/repository_sessao.py): `list_ativos` (aulas do paciente)
  - [src/app/repository_avaliacao.py](src/app/repository_avaliacao.py)
  - [src/app/repository_imagem.py](src/app/repository_imagem.py)
  - [src/app/repository_aparelho.py](src/app/repository_aparelho.py)
  - [src/app/repository_clinica.py](src/app/repository_clinica.py): `list_membros`
- **Já paginam** (usar como modelo): `repository_escala.py`, `repository_financeiro.py`,
  `repository_plano.py`, `repository_agenda.py`, `repository_profissional.py`.
- **Depois:** se alguma clínica passar de alguns milhares de pacientes, avaliar paginação também
  na tela (carregar aos poucos) em vez de trazer tudo.

---

## 2. Backup

### 2.1 Versionamento no bucket de fotos dos pacientes
- **Problema:** o bucket `PatientImagesBucket` não tem versionamento. Foto apagada ou
  sobrescrita não volta.
- **Como fazer:** `VersioningConfiguration: Status: Enabled` no bucket, mais uma regra de ciclo de
  vida que apaga as versões antigas depois de uns 90 dias, para não acumular custo.

### 2.2 Impedir que a tabela e o bucket sejam apagados junto com a stack
- **Problema:** sem `DeletionPolicy`, apagar a stack, ou um deploy que precise recriar o recurso,
  apaga a tabela e as fotos.
- **Como fazer:** `DeletionPolicy: Retain` e `UpdateReplacePolicy: Retain` em `ClinicaTable`,
  `PatientImagesBucket` e `ClinicaUserPool` no [template.yaml](template.yaml).
- **Cuidado:** adicionar essas opções não recria nada; é uma mudança segura.

### 2.3 Backup de longo prazo (mais de 35 dias)
- **Problema:** o backup contínuo (PITR) só volta até 35 dias atrás.
- **Como fazer:** AWS Backup com um plano mensal da tabela, guardado por 1 ano (ou mais, se a LGPD
  ou o contrato com as clínicas pedirem). Custa centavos com o tamanho atual.

### 2.4 Backup dos usuários do Cognito
- **Problema:** a AWS não oferece backup nativo do Cognito. Se o User Pool for apagado, todos
  precisam se cadastrar de novo.
- **Como fazer:** a proteção de exclusão do User Pool (`DeletionProtection: ACTIVE`) mais o item 2.2.
  Opcional: um script que exporta a lista de usuários (e-mail, clínica, papel) para o S3.
  Senhas não são exportáveis.

### 2.5 Testar uma restauração
- Restaurar a tabela via PITR para uma tabela nova, conferir os dados e apagar a cópia.
- Escrever o passo a passo em `.specs/` para não precisar descobrir na hora do aperto.

---

## 3. Rastreio e auditoria

### 3.1 Preservar a data de criação quando o registro for regravado
- **Problema:** `set_membro` em [src/app/repository_clinica.py](src/app/repository_clinica.py) usa
  `put_item` e sobrescreve o `criadoEm`. Os 7 membros ficaram com 28/09/2026 19:20 (hora em que os
  nomes foram preenchidos), e a data original se perdeu.
- **Como fazer:** usar `update_item` com `if_not_exists(criadoEm, :agora)`. Revisar outros
  `put_item` que possam regravar registros existentes.
- **Recuperar os 7 membros:** a data real de criação está no Cognito (`UserCreateDate`); um script
  pontual pode regravar o `criadoEm` a partir dela.

### 3.2 Adicionar data de alteração onde falta
- **Sem `atualizadoEm`:** escalas (ESCALA), imagens (IMAGE), membros (MEMBRO) e dados da clínica
  (METADATA). METADATA também não tem `criadoEm`.
- **Financeiro (FIN):** 1 dos 3 registros está sem `criadoEm`. Descobrir qual caminho do
  [src/app/repository_financeiro.py](src/app/repository_financeiro.py) grava sem a data e corrigir.

### 3.3 Registrar quem criou e quem alterou
- **Problema:** nenhum registro guarda qual pessoa o criou; só dá para saber a clínica.
- **Como fazer:** gravar `criadoPor` e `atualizadoPor` (sub ou e-mail do login) em todos os
  repositórios. O usuário já chega na rota pelo token em [src/app/deps.py](src/app/deps.py).

### 3.4 Histórico de alterações (antes e depois)
- **Opção simples:** cada rota que grava registra no log usuário, clínica, ação e registro alterado.
- **Opção completa:** ligar o DynamoDB Streams na tabela, com uma Lambda que grava cada alteração
  (valor antigo e novo) numa tabela ou log de auditoria. Pega também o que for alterado por scripts.
- **Observação:** hoje o log de acesso da API já responde "quem chamou qual rota e quando", mas não
  "o que mudou".

### 3.5 Clínica no log de acesso
- O log de acesso grava o sub e o e-mail do usuário, mas não o `custom:clinicId` (o nome tem
  dois-pontos). Testar se `$context.authorizer.claims.custom:clinicId` funciona; senão, dá para
  descobrir a clínica pelo sub.

---

## 4. Operação e confiabilidade

### 4.1 Alarmes por e-mail
- Criar alarmes no CloudWatch e avisar por e-mail (via SNS) quando houver:
  - erros na Lambda (`Errors` > 0 em 5 min);
  - chamadas recusadas por limite (`Throttles` > 0);
  - erros 5xx na API;
  - lentidão (p95 da `Duration` > 3 s).
- Hoje, se a API começar a falhar, você só descobre quando alguém reclamar.

### 4.2 Ambiente de teste (homologação)
- **Problema:** cada deploy vai direto para a produção que as clínicas usam.
- **Como fazer:** uma segunda stack (`clinica-pilates-hml`) com a própria tabela, o próprio Cognito
  e o próprio front, usando `samconfig.toml` com ambientes separados. Testar lá e só depois publicar
  em produção.

### 4.3 Deploy sem depender do build antigo
- O [scripts/deploy-back.ps1](scripts/deploy-back.ps1) reaproveita as bibliotecas Linux do último
  build porque o Docker não sobe na máquina. Se `src/requirements.txt` mudar, é preciso outro
  caminho: GitHub Actions fazendo `sam build --use-container` e o deploy, ou um build no CodeBuild.

### 4.4 Limite de requisições por clínica
- Hoje, uma clínica (ou um script com defeito) pode gastar a capacidade de todas as outras.
- Avaliar limites na rota da API Gateway (`ThrottlingBurstLimit` / `ThrottlingRateLimit`) e,
  mais adiante, limites por clínica.

---

## 5. LGPD (dados de saúde)

Avaliações, sessões e fotos de pacientes são **dados pessoais sensíveis** (saúde) pela LGPD.
Com mais clínicas, deixam de ser opcionais:
- rastreio de quem acessou e quem alterou (itens 3.3 e 3.4);
- backup e plano de restauração testado (seção 2);
- política de retenção e exclusão: o que acontece com os dados quando a clínica cancela ou o
  paciente pede exclusão;
- termo de uso e contrato com as clínicas, definindo o sistema como **operador** e a clínica
  como **controladora** dos dados;
- criptografia: a tabela e o bucket já são criptografados pela AWS. Conferir se basta ou se vale
  chave própria (KMS).

---

## 6. Banco de dados: DynamoDB ou relacional? (análise de 16/10/2026)

Tudo fica numa **tabela única** do DynamoDB, separada por prefixos na chave (`CLIENT#`, `ESCALA#`,
`AGENDA#`, `PROFISSIONAL#`, `FIN#`...). **Decisão: não migrar agora.**

### Por que o DynamoDB ainda serve
- **Custo quase zero** no volume atual; um relacional na AWS (RDS/Aurora) custa no mínimo uns
  US$ 15 a 50 por mês, mesmo parado.
- **Nada para administrar.** Lambda + relacional exige VPC e gerenciador de conexões (RDS Proxy),
  com mais custo e mais coisas que podem quebrar.
- **As telas atuais têm consultas previsíveis** ("agenda da semana", "caixa do mês", "escala"),
  cada uma resolvida com uma Query rápida.
- **Backup contínuo de 35 dias** já ativo.

### Onde ele já cobra o preço
- **Sem join:** nomes de paciente e profissional são cruzados no código (o router busca a lista
  e monta o resultado).
- **Relatórios cruzados são difíceis:** "quanto cada profissional faturou", "quem mais faltou",
  "ocupação por horário" não têm consulta pronta; cada pergunta nova pede um índice novo (GSI) ou
  ler tudo e somar no código.
- **Busca flexível limitada:** parte do nome, vários filtros, ordenações diferentes.

### Sinais de que chegou a hora de migrar
1. Relatórios e painéis cruzando agenda, profissionais e financeiro com filtros variados.
2. Muitas clínicas e volume grande, com consultas de análise lentas ou caras.
3. Integrações que esperam SQL (ERP, nota fiscal, BI, contabilidade).

**Destino, se migrar:** PostgreSQL sem servidor (Neon, Supabase ou Aurora Serverless) para manter
o custo baixo. Os repositórios (`src/app/repository_*.py`) já isolam o banco: a migração é
trabalhosa, mas organizada (trocar a implementação de cada repositório + script de cópia dos dados).

### Tela de relatórios (próximo passo planejado)
Antes de migrar o banco por causa de relatórios, avaliar nesta ordem:
1. **Relatórios simples no próprio backend:** para um período curto (um mês) e uma clínica, ler
   os itens do período (Query por prefixo, já paginada) e somar em Python. Atende bem o volume
   atual: faturamento por profissional, por forma de pagamento, marcações e pagos x não pagos.
2. **Exportação para análise:** export diário da tabela para o S3 (Export to S3 do DynamoDB, que
   exige o PITR já ativo) e consultas SQL pelo Athena. Custa centavos e não muda o banco do sistema.
3. **Migrar para PostgreSQL** só se os relatórios virarem o centro do produto (filtros livres,
   muitos meses, muitas clínicas).

### Relatórios pedidos (16/10/2026) e o que falta decidir
| Relatório | Situação |
|---|---|
| Fluxo de caixa em PDF (um ou vários meses) | Viável já: o caixa é particionado por mês; PDF gerado no navegador |
| Relação de pacientes da clínica (PDF/planilha) | Viável, mas antes corrigir a paginação de `list_ativos` (item 1.3) |
| Atendimentos por profissional no mês | Viável, depende das decisões abaixo |
| Pacientes que passaram na semana | Viável, depende das decisões abaixo |

**Decidido:** os relatórios de atendimento incluem **Agenda e Pilates** (aulas registradas).

**Decidir quando formos fazer:**
1. **Retenção da Agenda (hoje 4 meses, via TTL):** relatórios de histórico longo perdem os dados.
   Opções: aumentar a retenção ou gravar um **resumo mensal permanente** antes de expirar.
2. **Comparecimento:** a Agenda sabe quem foi *marcado*, não quem *compareceu*. Adicionar status
   por marcação (**Compareceu / Faltou / Desmarcou**); sem isso, falta conta como atendimento.
   De quebra, gera o relatório de faltas.
3. **"Por clínicas":** cada clínica vendo os seus pacientes (simples) ou o dono do sistema vendo
   todas juntas (exige um perfil "super admin" novo e cuidado com LGPD; hoje o isolamento por
   clínica é proposital).
4. **Aulas do Pilates por data/profissional:** as sessões (`SESSION#`) ficam na partição de cada
   paciente, então somar por período exige ler paciente a paciente. Solução: indexar as sessões
   por mês no **GSI1 que já existe** (esparso, hoje só usado pelas mensalidades), com
   `GSI1PK = CLINIC#<id>#SESSAO#<AAAA-MM>` e `GSI1SK = <data>#<id>`, gravado no create/update de
   `repository_sessao.py` + um script único que preenche as sessões antigas. Não precisa de índice
   novo nem mexe na tabela. Atenção: o `profissional` da sessão é **texto livre** (diferente do
   cadastro de profissionais da Agenda) — decidir se a aula passa a escolher do cadastro, senão
   "Ana" e "Dra. Ana" contam como pessoas diferentes.

---

## Ordem sugerida

| # | Item | Quem | Esforço |
|---|---|---|---|
| 1 | 1.1 Aumentar o limite de execuções simultâneas | Você (console AWS) | 5 min + espera |
| 2 | 2.1 e 2.2 Versionamento do S3 e proteção contra exclusão | Claude + seu deploy | Pequeno |
| 3 | 1.2 Memória da Lambda | Claude + seu deploy | Pequeno |
| 4 | 1.3 Paginação das listas | Claude | Médio |
| 5 | 4.1 Alarmes por e-mail | Claude + seu deploy | Pequeno |
| 6 | 3.1 a 3.3 Datas e autor em todos os registros | Claude | Médio |
| 7 | 2.3 a 2.5 Backup de longo prazo e teste de restauração | Claude + você | Médio |
| 8 | 4.2 Ambiente de teste | Claude + você | Grande |
| 9 | 3.4 Histórico completo de alterações | Claude | Grande |
| 10 | Seção 5 (LGPD) | Você (jurídico) + Claude (técnico) | Contínuo |
