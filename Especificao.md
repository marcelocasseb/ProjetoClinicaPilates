# Especificação de Arquitetura — Sistema de Gestão de Pilates

## Objetivo
Sistema para cadastro de pacientes e registro dos aparelhos utilizados por eles em cada sessão, com foco em menor custo operacional possível na AWS.

## Stack definida

### Frontend
- **S3 + CloudFront**: hospedagem de aplicação estática (React, Vue ou similar).
- Custo: centavos por mês, praticamente gratuito para baixo tráfego.

### Backend
- **Linguagem**: Python (sem uso de Docker).
- **Compute**: AWS Lambda, deploy via ZIP (pacote com dependências).
- **Framework sugerido**: FastAPI ou Flask, adaptado ao Lambda com um handler (ex: Mangum, para FastAPI).
- **Cold start**: naturalmente baixo em Python, não é necessário SnapStart.
- **Organização**: uma única função Lambda com roteamento interno das rotas (em vez de uma função por endpoint), para reduzir complexidade e número de cold starts.

### API / Integração
- **API Gateway**: porta de entrada HTTP, com integração do tipo *proxy* para a Lambda.
- API Gateway cuida de: roteamento, CORS, autenticação (via Cognito), rate limiting.
- Lambda recebe o evento no formato padrão de proxy integration e devolve `statusCode` + `headers` + `body`.

### Banco de dados
- **DynamoDB**, modo *on-demand* (pay-per-request, sem custo fixo de instância).
- Modelagem inicial sugerida (a detalhar): partition key = paciente, sort key = data/sessão (aparelhos utilizados).
- Dentro do free tier: 25GB de armazenamento.

### Autenticação
- **Amazon Cognito**: gerenciamento de usuários (equipe da clínica).
- Free tier: até 10 mil usuários ativos por mês (bem acima da necessidade do projeto).

### Armazenamento de arquivos
- **S3**: fotos, laudos ou anexos relacionados aos pacientes, se necessário.

### Domínio (opcional)
- **Route 53** (~$0.50/mês) + **ACM** (certificado SSL gratuito).

## Justificativa de custo
Toda a stack é *serverless* e paga por uso, sem instância ociosa rodando continuamente. Para o volume esperado (clínica pequena, uso concentrado em horário comercial), o custo estimado fica entre **$0 e $5/mês** no primeiro ano (dentro do free tier) e permanece baixo depois, pois escala com uso real.

## Decisões descartadas (e por quê)
| Alternativa | Motivo da não escolha |
|---|---|
| Docker (Lambda container image ou ECS/Fargate) | Adiciona complexidade sem benefício real para uma aplicação CRUD pequena; cold start maior; custo fixo mais alto no caso do Fargate. |
| RDS | Custo fixo de instância mesmo com baixo uso; DynamoDB on-demand é mais econômico para este volume. |
| EC2/Lightsail sempre ligado | Paga por tempo de servidor ligado, não por uso real — menos econômico que Lambda para tráfego baixo e intermitente. |

## Em aberto (próximos passos)
- Modelagem de dados no DynamoDB (tabelas, atributos, chaves).
- Estrutura do projeto Python (dependências, camadas, endpoints).
- Fluxo de autenticação com Cognito (login da equipe da clínica).
- Infraestrutura como código (SAM, Terraform ou CDK) para provisionar tudo.
