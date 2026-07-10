# Guia Completo: CI/CD com Databricks Bundles

## O que são Databricks Bundles?

Databricks Bundles (também chamados DABs - Databricks Asset Bundles) são a forma moderna de gerenciar e deployar recursos no Databricks. Pense neles como "Infrastructure as Code" específico para Databricks.

### Por que usar Bundles ao invés de criar Jobs manualmente?

**Problema com abordagem manual:**
- Você cria um Job pela UI
- Alguém modifica ele acidentalmente
- Você não sabe o que mudou nem quando
- Impossível replicar em outro ambiente
- Sem histórico de mudanças

**Solução com Bundles:**
- Toda configuração em arquivos YAML versionados no Git
- Deploy automatizado via CI/CD
- Histórico completo de mudanças
- Deploy idêntico em dev/staging/prod
- Rollback fácil se algo der errado

## Estrutura de um Bundle

```
teste_mlops/
├── databricks.yml          # Configuração principal do bundle
├── resources/              # Definições de recursos (Jobs, Pipelines, etc)
│   ├── training_job.yml
│   ├── evaluation_job.yml
│   ├── batch_inference_job.yml
│   └── monitoring_job.yml
├── src/                    # Código Python
├── tests/                  # Testes automatizados
└── .github/workflows/      # CI/CD do GitHub Actions
```

## Arquivo Principal: databricks.yml

### Seção 1: Informações Básicas

```yaml
bundle:
  name: iris-classification
```

**O que faz:** Define o nome do seu projeto. Esse nome será usado como prefixo/sufixo em recursos criados.

### Seção 2: Include (Importar Recursos)

```yaml
include:
  - resources/*
```

**O que faz:** Importa todos os arquivos YAML da pasta `resources/`. Cada arquivo pode definir Jobs, Pipelines, ou outros recursos.

**Por que separar em arquivos?**
- Organização: um arquivo por job
- Manutenção: mais fácil encontrar e editar
- Colaboração: menos conflitos no Git

### Seção 3: Artifacts (Empacotamento de Código)

```yaml
artifacts:
  default:
    type: whl
    build: uv build
    path: .
```

**O que faz:**
- `type: whl`: Empacota seu código Python em um wheel (.whl)
- `build: uv build`: Comando para gerar o wheel (usando uv, gerenciador de pacotes rápido)
- `path: .`: Empacota tudo a partir da raiz do projeto

**Por que wheel e não scripts Python soltos?**
- Wheels incluem dependências
- Versioning correto
- Instalação rápida
- Padrão da indústria Python

### Seção 4: Variables (Parametrização)

```yaml
variables:
  catalog_name:
    description: "Catálogo Unity Catalog"
    default: main
  schema_name:
    description: "Schema Unity Catalog"
    default: iris_mlops
```

**O que faz:** Define variáveis reutilizáveis em todo o bundle.

**Como usar:** Nos arquivos de resources, você referencia com `${var.catalog_name}`

### Seção 5: Targets (Ambientes)

A parte mais importante! Define ambientes separados (dev, staging, prod).

#### Target: dev (Desenvolvimento)

```yaml
targets:
  dev:
    default: true              # Ambiente padrão se não especificar
    mode: development          # Modo de desenvolvimento
    workspace:
      host: https://sua-workspace.databricks.com
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.target}/${bundle.name}
    variables:
      schedule_pause_status: PAUSED    # Jobs NÃO rodam automaticamente
      catalog_name: ${workspace.current_user.short_name}_dev
```

**Características:**
- `mode: development`: Databricks não valida algumas regras rigorosas
- `root_path`: Cada dev tem sua própria pasta
- `PAUSED`: Jobs não rodam sozinhos (você dispara manualmente)
- Catálogo isolado por usuário (`eduardo_dev`, `maria_dev`, etc)

**Quando usar:** Desenvolvimento local, experimentação, testes rápidos.

#### Target: staging (Homologação)

```yaml
staging:
  presets:
    name_prefix: 'stg_'      # Todos os recursos começam com stg_
  workspace:
    root_path: /Shared/.bundle/${bundle.target}/${bundle.name}
  variables:
    schedule_pause_status: PAUSED
    catalog_name: staging
```

**Características:**
- `name_prefix`: Jobs aparecem como "stg_mlops_training_pipeline"
- Pasta compartilhada `/Shared`
- Catálogo dedicado `staging`

**Quando usar:** Testes antes de produção, validação com dados realistas, demos.

#### Target: prod (Produção)

```yaml
prod:
  mode: production          # Validações rigorosas
  workspace:
    root_path: /Shared/.bundle/${bundle.target}/${bundle.name}
  variables:
    schedule_pause_status: UNPAUSED    # Jobs RODAM automaticamente
    catalog_name: prod
```

**Características:**
- `mode: production`: Databricks aplica validações rigorosas
- `UNPAUSED`: Jobs rodam nos horários agendados
- Catálogo de produção `prod`

**Quando usar:** Ambiente de produção real, dados reais, inferências para usuários.

## Arquivo de Resource: training_job.yml

Vamos entender como definir um Job:

```yaml
resources:
  jobs:
    mlops_training_pipeline:
      name: "MLOps Training Pipeline"
      description: "Pipeline completo de retreino"
      
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"  # 2AM diariamente
        timezone_id: "America/Sao_Paulo"
        pause_status: "${var.schedule_pause_status}"  # Usa variável do target
```

**Agendamento:**
- `quartz_cron_expression`: Formato Quartz Cron
  - `0 0 2 * * ?` = segundo=0, minuto=0, hora=2, todo dia, todo mês, qualquer dia da semana
  - Ou seja: 2AM todos os dias
- `pause_status`: Em dev/staging é PAUSED, em prod é UNPAUSED

### Tasks (Tarefas do Job)

```yaml
tasks:
  - task_key: "process_data"
    description: "Processa dados"
    python_wheel_task:
      package_name: "teste_mlops"      # Nome do seu wheel
      entry_point: "process_data"      # Entry point definido no pyproject.toml
      parameters:
        - "--catalog"
        - "${var.catalog_name}"          # Usa variável
        - "--schema"
        - "${var.schema_name}"
    libraries:
      - pypi:
          package: "scikit-learn"
```

**Entry Points:**

No `pyproject.toml`, você define:

```toml
[project.scripts]
process_data = "src.pipeline.01_process_data:main"
```

Isso permite chamar `process_data` como se fosse um comando.

### Dependências entre Tasks

```yaml
- task_key: "train_model"
  depends_on:
    - task_key: "process_data"    # Só roda após process_data ter sucesso
```

**Ordem de execução garantida:**
1. `process_data` roda primeiro
2. Se falhar, `train_model` não roda
3. Se passar, `train_model` roda

## CI/CD com GitHub Actions

### Workflow 1: CI (Continuous Integration)

**Arquivo:** `.github/workflows/ci.yml`

**Quando roda:** Em todo Pull Request e push no `develop`

**O que faz:**
1. Roda testes unitários
2. Valida code quality (linting)
3. Valida bundle YAML (sem erros de sintaxe)

```yaml
- name: Run unit tests
  run: pytest tests/ -v --cov=src

- name: Validate bundle
  run: databricks bundle validate
```

### Workflow 2: Deploy

**Arquivo:** `.github/workflows/deploy.yml`

**Quando roda:** Quando você faz push no `main` (produção)

**O que faz:**
1. Instala Databricks CLI
2. Faz deploy do bundle no ambiente
3. Atualiza todos os Jobs

```yaml
- name: Deploy to production
  run: databricks bundle deploy --target prod
```

## Comandos Essenciais

### Desenvolvimento Local

```bash
# Validar bundle (verifica erros)
databricks bundle validate

# Deploy no ambiente dev
databricks bundle deploy --target dev

# Rodar um job manualmente
databricks bundle run mlops_training_pipeline --target dev

# Ver recursos criados
databricks bundle resources --target dev
```

### Deploy em Staging

```bash
# Deploy em staging
databricks bundle deploy --target staging

# Verificar o que será deployado
databricks bundle deploy --target staging --dry-run
```

### Deploy em Produção

```bash
# IMPORTANTE: Sempre validar antes
databricks bundle validate --target prod

# Deploy em produção
databricks bundle deploy --target prod
```

## Fluxo de Trabalho Completo

### Cenário 1: Nova Feature

1. **Desenvolvimento:**
   ```bash
   git checkout -b feature/novo-preprocessamento
   # Edita código em src/
   # Testa localmente
   databricks bundle deploy --target dev
   databricks bundle run mlops_training_pipeline --target dev
   ```

2. **Code Review:**
   ```bash
   git push origin feature/novo-preprocessamento
   # Cria Pull Request
   # CI roda automaticamente (testes + validação)
   ```

3. **Merge e Deploy em Staging:**
   ```bash
   # Após aprovação, merge no develop
   git checkout develop
   git merge feature/novo-preprocessamento
   databricks bundle deploy --target staging
   # Valida em staging com dados reais
   ```

4. **Deploy em Produção:**
   ```bash
   # Se tudo OK em staging
   git checkout main
   git merge develop
   git push origin main
   # GitHub Actions faz deploy automático em prod
   ```

### Cenário 2: Hotfix em Produção

1. **Fix urgente:**
   ```bash
   git checkout -b hotfix/corrigir-drift-detection
   # Corrige o bug
   # Testa em dev
   databricks bundle deploy --target dev
   ```

2. **Deploy direto:**
   ```bash
   git checkout main
   git merge hotfix/corrigir-drift-detection
   git push origin main
   # Deploy automático em prod
   ```

## Boas Práticas

### 1. Sempre Teste em Dev Primeiro

Nunca deploye direto em prod sem testar.

```bash
# Errado
databricks bundle deploy --target prod  # Sem testar antes

# Certo
databricks bundle deploy --target dev
databricks bundle run mlops_training_pipeline --target dev
# Verifica logs, resultados
# Se OK, aí sim vai pra staging/prod
```

### 2. Use Variáveis para Parametrização

```yaml
# Errado - hardcoded
parameters:
  - "--catalog"
  - "study"  # E se quiser mudar?

# Certo - parametrizado
parameters:
  - "--catalog"
  - "${var.catalog_name}"  # Muda por ambiente
```

### 3. Documente Mudanças

Todo deploy significativo deve ter:
- Descrição do que mudou
- Por que mudou
- Como testar

```bash
git commit -m "feat: adiciona detecção de drift

Adiciona monitoramento de drift nas features de entrada.
Detecta quando distribuição muda >10% vs baseline.

Testado em dev com dataset sintético."
```

### 4. Monitore Jobs

Após deploy, sempre verifique:
- Jobs estão rodando?
- Sem erros?
- Métricas estão normais?

```bash
# Ver runs recentes
databricks jobs list-runs --job-id <id>

# Ver logs de um run
databricks jobs get-run <run-id>
```

## Troubleshooting

### Erro: "Resource already exists"

**Causa:** Alguém criou manualmente um Job com mesmo nome.

**Solução:**
```bash
# Opção 1: Deletar o recurso manual
# Opção 2: Mudar nome no bundle
# Opção 3: Usar --force-lock (último recurso)
databricks bundle deploy --target dev --force-lock
```

### Erro: "Invalid YAML syntax"

**Causa:** Erro de indentação ou sintaxe no YAML.

**Solução:**
```bash
# Valida bundle localmente
databricks bundle validate
# Mostra linha exata do erro
```

### Job não está rodando

**Causa:** `pause_status: PAUSED`

**Solução:**
```yaml
# Em databricks.yml, para o target específico
variables:
  schedule_pause_status: UNPAUSED
```

Ou rode manualmente:
```bash
databricks bundle run <job-name> --target dev
```

## Próximos Passos

1. **Leia:** `databricks.yml` completo
2. **Explore:** Arquivos em `resources/`
3. **Teste:** Deploy em dev
4. **Customize:** Adicione seus próprios jobs
5. **Documente:** Atualize este guia com suas descobertas

## 🎓 Conceitos Avançados

### Serverless vs Classic Clusters

**Serverless (Recomendado):**
```yaml
tasks:
  - task_key: "process"
    environment_key: "default"  # Usa serverless
    python_wheel_task:
      package_name: "teste_mlops"
      entry_point: "process_data"
```

**Classic Cluster (Legacy):**
```yaml
tasks:
  - task_key: "process"
    job_cluster_key: "default"  # Usa cluster clássico
    python_wheel_task:
      package_name: "teste_mlops"
      entry_point: "process_data"

job_clusters:
  - job_cluster_key: "default"
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.xlarge"
```

**Diferenças:**
| Aspecto | Serverless | Classic |
|---------|------------|--------|
| Startup | ~30s | ~5min |
| Cost | Pay-per-second | Pay-per-hour |
| Maintenance | Zero | Manual upgrades |
| Scaling | Automatic | Manual config |

### Wheel Path: Relativo vs Absoluto

**⚠️ Erro Comum:**
```yaml
# ERRADO - path relativo ao bundle root
dependencies:
  - "dist/*.whl"  # ❌ Não encontra!
```

**✅ Correto:**
```yaml
# Path relativo ao YAML file (em resources/)
dependencies:
  - "../dist/*.whl"  # ✅ Funciona!
```

**Por quê?**
- `training_job.yml` está em `resources/`
- Wheel está em `dist/`
- De `resources/` para `dist/` = `../dist/`

### Entry Points no pyproject.toml

**Estrutura do Entry Point:**
```toml
[project.scripts]
nome_comando = "modulo.submodulo:função"
```

**Exemplo Real:**
```toml
[project.scripts]
process_data = "teste_mlops.pipelines.training:process_data_main"
train_model = "teste_mlops.pipelines.training:train_model_main"
```

**Como funciona:**
1. Databricks instala o wheel
2. Entry point `process_data` vira um comando executável
3. Job chama `process_data` como se fosse CLI
4. Python executa `teste_mlops.pipelines.training:process_data_main()`

### Variáveis: Interpolação e Precedência

**Ordem de precedência (maior para menor):**
1. Target-specific variables
2. Bundle-level variables
3. Default values

**Exemplo:**
```yaml
variables:
  catalog_name:
    default: "dev"  # 3. Default

targets:
  staging:
    variables:
      catalog_name: "staging"  # 1. Target-specific (vence!)
```

**Interpolação:**
```yaml
# Simples
"${var.catalog_name}"

# Composição
"${var.catalog_name}.${var.schema_name}"

# Built-ins Databricks
"${workspace.current_user.userName}"
"${bundle.target}"
"${bundle.name}"
```

## 🧪 Exemplos Práticos

### Exemplo 1: Job com Múltiplas Tasks em Paralelo

```yaml
tasks:
  # Task 1 e 2 rodam em paralelo
  - task_key: "load_features"
    python_wheel_task:
      entry_point: "load_features"
  
  - task_key: "load_labels"
    python_wheel_task:
      entry_point: "load_labels"
  
  # Task 3 só roda após ambas terminarem
  - task_key: "merge_data"
    depends_on:
      - task_key: "load_features"
      - task_key: "load_labels"
    python_wheel_task:
      entry_point: "merge_data"
```

### Exemplo 2: Notificações Condicionais

```yaml
email_notifications:
  on_success:
    - "${var.email_success}"  # Apenas em prod
  on_failure:
    - "${var.email_failure}"  # Sempre alerta
  on_duration_warning_threshold_exceeded:
    - "sre-team@company.com"  # Se demorar muito

timeout_seconds: 3600
```

No `databricks.yml`:
```yaml
targets:
  dev:
    variables:
      email_success: ""  # Não envia em dev
      email_failure: "dev@company.com"
  
  prod:
    variables:
      email_success: "team@company.com"  # Envia em prod
      email_failure: "sre@company.com"
```

### Exemplo 3: Retry com Backoff

```yaml
tasks:
  - task_key: "api_call"
    retry_on_timeout: true
    max_retries: 3
    min_retry_interval_millis: 10000   # 10s
    python_wheel_task:
      entry_point: "call_external_api"
```

**Comportamento:**
- Tentativa 1 falha → espera 10s → retry
- Tentativa 2 falha → espera 10s → retry
- Tentativa 3 falha → job FAILED

### Exemplo 4: Parameters Dinâmicos

```yaml
parameters:
  - name: "start_date"
    default: "2024-01-01"
  - name: "end_date"
    default: "2024-12-31"
  - name: "model_type"
    default: "logistic_regression"

tasks:
  - task_key: "train"
    python_wheel_task:
      entry_point: "train_model"
      parameters:
        - "--start-date"
        - "{{job.parameters.start_date}}"  # Runtime override
        - "--end-date"
        - "{{job.parameters.end_date}}"
        - "--model"
        - "{{job.parameters.model_type}}"
```

**Override via CLI:**
```bash
databricks jobs run-now \
  --job-id 123 \
  --python-params '{"start_date": "2024-06-01", "model_type": "random_forest"}'
```

## 📚 Checklist de Deploy

### Antes de Deploy em Staging
- [ ] Testes unitários passando localmente
- [ ] `databricks bundle validate` sem erros
- [ ] Deploy em dev testado e funcionando
- [ ] Código revisado (pull request)
- [ ] Variáveis de staging configuradas
- [ ] Catálogo/schema de staging existem

### Antes de Deploy em Prod
- [ ] Deploy em staging testado por 24h+
- [ ] Métricas de staging validadas
- [ ] Rollback plan definido
- [ ] Stakeholders notificados
- [ ] Janela de manutenção agendada (se necessário)
- [ ] Monitoring/alertas configurados
- [ ] Documentação atualizada

## 🔍 Debug de Bundles

### Ver Bundle Expandido
```bash
# Mostra YAML final após interpolação
databricks bundle deployment --target dev
```

### Ver Recursos Criados
```bash
# Lista todos os recursos do bundle
databricks bundle summary --target dev
```

### Logs Detalhados
```bash
# Deploy com debug
databricks bundle deploy --target dev --debug
```

### Validar sem Deploy
```bash
# Dry-run (mostra o que faria)
databricks bundle deploy --target dev --dry-run
```

## Recursos Adicionais

- [Documentação oficial Databricks Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [Exemplos de Bundles](https://github.com/databricks/bundle-examples)
- [Quartz Cron Expression](https://www.quartz-scheduler.org/documentation/quartz-2.3.0/tutorials/crontrigger.html)
- [Databricks CLI Reference](https://docs.databricks.com/dev-tools/cli/index.html)