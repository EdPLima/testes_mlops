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

## Recursos Adicionais

- [Documentação oficial Databricks Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [Exemplos de Bundles](https://github.com/databricks/bundle-examples)
- [Quartz Cron Expression](https://www.quartz-scheduler.org/documentation/quartz-2.3.0/tutorials/crontrigger.html)