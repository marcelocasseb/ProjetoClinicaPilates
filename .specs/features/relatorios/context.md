# Relatórios: decisões do usuário (2026-11-09)

Decisões **travadas** (o Design e as Tasks não reabrem):

| # | Tema | Decisão | Consequência |
|---|------|---------|--------------|
| D1 | Grupos | **Os 4**: Financeiro, Alunos, Ocupação da escala, Atendimento | Todos são P1 |
| D2 | Formato | **Tela + PDF para imprimir** (Excel não foi escolhido) | Botão "Imprimir / PDF" em cada relatório |
| D3 | Quem vê | **Só admin**: a aba inteira | Router com `require_admin` no `APIRouter` (como o Financeiro). A aba fica escondida para membro |
| D4 | Período | ~~Mês + evolução de 12 meses~~ → **revisto em 09/11 (após o 1º deploy): período personalizado em todos os relatórios de período**, com atalhos (Este mês, Mês passado, Últimos 7/30 dias, Este ano) + Personalizado (de/até) | `?de=&ate=` (o `?mes=` continua aceito). Até 2 anos, sem passar de hoje. Evolução = meses do período (ou os 12 meses até o fim, se o período cabe num mês). Mensalidades = do mês em que o período termina. Ocupação e Relação seguem retrato de hoje; Semana segue com seletor de semana. Relatório por profissional: a tabela do Atendimento basta (usuário, 09/11) |
| D5 | Atendimento | **Agenda + Pilates**, mostrados **separados** (nunca somados). Decisão de 16/10, reconfirmada em 09/11; substitui a resposta "só aulas registradas" dada mais cedo no mesmo dia | O Atendimento lê `SESSION#` **e** `AGENDA#`. A Agenda tem retenção de 4 meses (TTL), então os meses expirados aparecem como "sem dados" |
| D6 | PDF | **Os dois**: PDF por relatório **e** fechamento do mês | O fechamento é P2 e reaproveita os componentes dos relatórios |
| D7 | Extrato do Caixa | **Entra** (pedido de 16/10): lançamentos do mês linha a linha no relatório Financeiro e no PDF | Um mês por PDF (D4). Vários meses = um PDF por mês |
| D8 | Relação de alunos | **Entra** (pedido de 16/10): ativos com contato, plano e horários; tela + PDF | Retrato de hoje, sem mês. Fica fora do fechamento |
| D9 | Quem passou na semana | **Entra** (pedido de 16/10): seletor de semana (seg–dom), alunos × dias, marcando a fonte | Fica fora do fechamento (não é do mês) |

## Livre para o Design decidir (com recomendação inicial)

- **Gráficos sem biblioteca nova**: o front hoje só depende de React. Barras e linhas em SVG/CSS próprios mantêm o bundle leve e imprimem bem. Avaliar se uma lib leve compensa.
- **PDF via impressão do navegador** (`window.print()` + CSS `@media print`): sem lib de PDF e sem trabalho no back. O usuário escolhe "Salvar como PDF". Alternativa: gerar PDF no back, que é mais pesado e precisaria de dependência nova na Lambda (quebra o atalho de deploy sem Docker).
- **Atendimento em escala (REL-19)**: as aulas ficam sob a PK de cada aluno. Opções: (a) uma Query por aluno, em paralelo, no back; (b) GSI novo por clínica+data. Um GSI novo **altera a tabela de produção**, então a preferência é (a), medida contra o limite de 5 s.
- **Endpoints**: um por relatório (`GET /relatorios/financeiro?mes=`, `/alunos?mes=`, `/relacao-alunos`, `/ocupacao`, `/atendimento?mes=`, `/semana?inicio=`), cada um já agregado no back, para o front não somar milhares de itens.

## Relação com `PENDENCIAS.md`

- Seção 6 ("Relatórios pedidos 16/10"): os 4 pedidos são atendidos por REL-20 (extrato), REL-21 (relação), REL-14 (por profissional) e REL-22 (semana).
- Item 1.3 (paginação): `PacienteRepository.list_ativos` é paginado nesta feature (T2), porque a Relação, a Ocupação e as Mensalidades dependem dele.
- Seção 6, item 4 (GSI1 para sessões por mês): **não** é adotado agora. Ler aluno por aluno em paralelo dá conta do volume atual sem mudar a gravação das aulas nem rodar script de preenchimento. Fica como evolução se a medição em produção (T20) passar de 5 s.
- Seção 6, item 4 ("profissional da aula é texto livre"): hoje a aula já grava `profissionalId` quando escolhido do cadastro. O relatório agrupa por id e, só sem id, pelo texto.
