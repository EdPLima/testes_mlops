# Guia de CI/CD

Integração e deploy automatizados com GitHub Actions.

## Workflows

### 1. CI (Pull Request)
**Arquivo**: `.github/workflows/ci.yml`

**Triggers**:
* Pull requests para `main`

**Etapas**:
1. Checkout código
2. Setup Python
3. Instalar dependências
4. Rodar linting (black, flake8)
5. Rodar testes (pytest)
6. Validar bundle

### 2. Deploy Staging (Push main)
**Arquivo**: `.github/workflows/deploy-staging.yml`

**Triggers**:
* Push para `main`

**Etapas**:
1. Validar bundle
2. Deploy para ambiente staging

### 3. Deploy Production (Release)
**Arquivo**: `.github/workflows/deploy-prod.yml`

**Triggers**:
* Tags `v*` (ex: v1.0.0)

**Etapas**:
1. Validar bundle
2. Deploy para ambiente prod

## Configuração GitHub

### Secrets Necessários

Você precisa criar **2 secrets separados**:

**Secret 1:**
- Nome: `DATABRICKS_HOST`
- Valor: `https://dbc-6181e49f-87e5.cloud.databricks.com`

**Secret 2:**
- Nome: `DATABRICKS_TOKEN`
- Valor: (token gerado - veja como gerar abaixo)

### Como Gerar o Token do Databricks

1. Acesse o Databricks → clique no **ícone do usuário** (canto superior direito)
2. Clique em **Settings**
3. No menu lateral, clique em **Developer**
4. Clique em **Access tokens** (ou **Manage** se já tiver tokens)
5. Clique em **Generate new token**
6. Preencha:
   - **Comment**: `GitHub Actions CI/CD`
   - **Lifetime**: `90 days` (ou o período desejado)
7. Clique em **Generate**
8. **Copie o token imediatamente** (formato: `dapi...`)
   - ⚠️ Você não conseguirá ver esse token novamente!

### Como Adicionar Secrets no GitHub

1. Acesse seu repositório no GitHub
2. Clique em **Settings** (aba do repositório)
3. No menu lateral esquerdo: **Secrets and variables** → **Actions**
4. Clique em **New repository secret**
5. Adicione o primeiro secret:
   - Nome: `DATABRICKS_HOST`
   - Valor: `https://dbc-6181e49f-87e5.cloud.databricks.com`
   - Clique em **Add secret**
6. Clique novamente em **New repository secret**
7. Adicione o segundo secret:
   - Nome: `DATABRICKS_TOKEN`
   - Valor: (cole o token `dapi...` que você copiou)
   - Clique em **Add secret**

### Proteção de Branch

Recomendado para `main`:
* Require pull request reviews
* Require status checks to pass
* Require branches to be up to date

## Fluxo de Trabalho

```
1. Criar branch feature
   git checkout -b feature/nova-feature

2. Fazer alterações e commit
   git add .
   git commit -m "feat: adicionar nova feature"

3. Push e criar PR
   git push origin feature/nova-feature

4. CI roda automaticamente
   - Testes passam ✓
   - PR aprovado ✓

5. Merge para main
   - Deploy staging automático

6. Criar release (tag)
   git tag v1.0.0
   git push origin v1.0.0
   - Deploy prod automático
```

## Convenções de Commit

* `feat:` - Nova funcionalidade
* `fix:` - Correção de bug
* `docs:` - Documentação
* `test:` - Testes
* `refactor:` - Refatoração
* `chore:` - Manutenção

## Troubleshooting

### CI failing: "Module not found"
* Verifique `pyproject.toml` - dependências corretas
* Verifique imports nos testes

### Deploy failing: "Invalid bundle"
* Rode localmente: `databricks bundle validate`
* Verifique sintaxe YAML em `databricks.yml`

### Deploy failing: "Permission denied"
* Verifique DATABRICKS_TOKEN tem permissões
* Token não expirado

## 🎓 Entendendo GitHub Actions

### Anatomia de um Workflow

```yaml
name: Deploy to Databricks  # Nome visível na UI

on:                          # Triggers (quando rodar)
  push:
    branches: [main]         # Apenas pushes no main

jobs:                        # Jobs do workflow
  deploy-staging:            # ID do job
    runs-on: ubuntu-latest   # Máquina virtual (runner)
    environment: staging     # Ambiente (para secrets)
    
    steps:                   # Passos sequenciais
      - name: Checkout       # Nome do passo
        uses: actions/checkout@v3  # Action reutilizável
      
      - name: Deploy
        run: |               # Comandos shell
          databricks bundle deploy --target staging
        env:                 # Variáveis de ambiente
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

### Conceitos Importantes

**1. Triggers (`on:`)**
```yaml
# Trigger em push
on:
  push:
    branches: [main, develop]
    tags: ['v*']           # Tags que começam com v

# Trigger em pull request
on:
  pull_request:
    branches: [main]

# Múltiplos triggers
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:       # Manual trigger
```

**2. Jobs e Steps**
- **Job**: Unidade de execução (roda em uma VM separada)
- **Step**: Ação dentro de um job (sequencial)
- Jobs rodam em paralelo por padrão
- Steps rodam em sequência dentro do job

**3. Secrets**
- Variáveis criptografadas armazenadas no GitHub
- Acessíveis via `${{ secrets.NOME }}`
- Nunca aparecem nos logs (mascaradas)

**4. Environments**
```yaml
jobs:
  deploy-staging:
    environment: staging  # Usa secrets do ambiente staging
```

Benefícios:
- Secrets separados por ambiente (staging, prod)
- Proteção extra (reviewers, delays)
- URL do ambiente visível nos PRs

## 🔧 Workflow Avançado: Deploy com Validação

```yaml
name: CD - Deploy to Databricks

on:
  push:
    branches: [main]

jobs:
  # Job 1: Build e Validar
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build pytest
          pip install -e .
      
      - name: Run tests
        run: pytest tests/ -v
      
      - name: Build wheel
        run: python -m build
      
      - name: Upload wheel
        uses: actions/upload-artifact@v3
        with:
          name: wheel
          path: dist/*.whl
  
  # Job 2: Deploy Staging (depende de build)
  deploy-staging:
    needs: build              # Só roda se build passar
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Download wheel
        uses: actions/download-artifact@v3
        with:
          name: wheel
          path: dist/
      
      - name: Setup Databricks CLI
        run: |
          curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
      
      - name: Validate Bundle
        run: databricks bundle validate --target staging
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
      
      - name: Deploy Bundle
        run: databricks bundle deploy --target staging --force
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
      
      - name: Run Training Pipeline
        run: databricks bundle run mlops_training_pipeline --target staging
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

## 🚨 Troubleshooting Detalhado

### 1. "Cannot launch the cluster"

**Erro completo:**
```
Task process_data failed with message: 
Cannot launch the cluster. An unexpected error occurred.
```

**Causas possíveis:**
1. **Capacidade Serverless indisponível** (Free Edition)
2. **Região sem capacidade** naquele momento
3. **Job ainda com configuração antiga** (cluster clássico)

**Diagnóstico:**
```bash
# Verificar job deployado
databricks jobs get <JOB_ID> --output json

# Procurar por:
# - "environments": []     → Serverless OK✓
# - "job_clusters": [...]  → Classic cluster (problema!)
```

**Soluções:**
```bash
# 1. Forçar re-deploy
databricks bundle deploy --target staging --force

# 2. Retry em horário diferente (madrugada US East)

# 3. Adicionar retry no workflow
- name: Run Training Pipeline
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 30
    max_attempts: 3
    retry_wait_seconds: 300
    command: databricks bundle run mlops_training_pipeline --target staging
```

### 2. "Wheel not found: dist/*.whl"

**Erro completo:**
```
Dependency not found: /Workspace/.bundle/.../dist/*.whl
```

**Causa:** Path do wheel está errado no YAML.

**Solução:**
```yaml
# ERRADO (relativo ao bundle root)
dependencies:
  - "dist/*.whl"

# CORRETO (relativo ao YAML file em resources/)
dependencies:
  - "../dist/*.whl"
```

### 3. "uv: command not found"

**Causa:** Workflow não tem `uv` instalado.

**Solução 1 (Usar pip + build):**
```yaml
# Em databricks.yml
artifacts:
  default:
    build: pip install build && python -m build
```

**Solução 2 (Instalar uv):**
```yaml
# Em .github/workflows/deploy.yml
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Build wheel
  run: uv build
```

### 4. "Git dubious ownership"

**Erro completo:**
```
fatal: detected dubious ownership in repository
```

**Causa:** Databricks Repos tem problema de permissões.

**Solução:** Use GitHub Actions, não Databricks Repos para CI/CD.

### 5. Workflow não roda após push

**Checklist:**
- [ ] Arquivo em `.github/workflows/` (não `.github/workflow`)
- [ ] YAML válido (use yamllint ou validator online)
- [ ] Branch correto no trigger (`branches: [main]`)
- [ ] Workflow habilitado (GitHub Actions tab)

**Debug:**
```bash
# Verificar sintaxe YAML
yamllint .github/workflows/deploy.yml

# Testar localmente (act)
act push -j deploy-staging
```

## 📊 Monitorando Workflows

### Via GitHub UI
1. Repositório → **Actions** tab
2. Clique no workflow run
3. Expanda jobs e steps para ver logs
4. Download de artifacts (wheels, reports)

### Via CLI (gh)
```bash
# Instalar GitHub CLI
brew install gh  # ou: https://cli.github.com

# Autenticar
gh auth login

# Listar workflows
gh workflow list

# Ver runs de um workflow
gh run list --workflow=deploy.yml

# Ver logs de um run
gh run view <RUN_ID> --log

# Re-run um workflow falhado
gh run rerun <RUN_ID>
```

## 🎓 Boas Práticas

### 1. Always Build Before Deploy
```yaml
jobs:
  build:
    # ... build and test ...
  
  deploy:
    needs: build  # Garante ordem
```

### 2. Use Artifacts para Compartilhar
```yaml
# Job 1: Build
- name: Upload wheel
  uses: actions/upload-artifact@v3
  with:
    name: wheel
    path: dist/*.whl

# Job 2: Deploy
- name: Download wheel
  uses: actions/download-artifact@v3
  with:
    name: wheel
    path: dist/
```

### 3. Fail Fast
```yaml
jobs:
  test:
    strategy:
      fail-fast: true  # Para todos os jobs se um falhar
      matrix:
        python-version: ['3.9', '3.10', '3.11']
```

### 4. Timeout para Evitar Custos
```yaml
jobs:
  deploy:
    timeout-minutes: 30  # Cancela após 30min
```

### 5. Environments para Proteção
```yaml
jobs:
  deploy-prod:
    environment:
      name: production
      url: https://databricks.com/workspace  # Link visível
```

No GitHub:
- Settings → Environments → production
- Required reviewers: adicione revisores
- Wait timer: delay antes de deploy

## 📝 Checklist de Setup CI/CD

### Setup Inicial
- [ ] Databricks token gerado (90 dias)
- [ ] Secrets configurados no GitHub
  - [ ] `DATABRICKS_HOST`
  - [ ] `DATABRICKS_TOKEN`
- [ ] Environments criados (staging, prod)
- [ ] Branch protection rules (main)
- [ ] Workflows validados localmente

### Após Cada Deploy
- [ ] Workflow passou sem erros
- [ ] Jobs criados/atualizados no Databricks
- [ ] Test run manual funcionou
- [ ] Métricas/logs normais
- [ ] Notificações configuradas

### Manutenção Periódica
- [ ] Renovar token antes de expirar (a cada 60-80 dias)
- [ ] Atualizar versões de actions (@v3 → @v4)
- [ ] Revisar logs de workflows antigos
- [ ] Limpar artifacts antigos (>90 dias)

## 🔗 Recursos Úteis

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Databricks CLI Reference](https://docs.databricks.com/dev-tools/cli/index.html)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Act - Run workflows locally](https://github.com/nektos/act)
- [YAML Validator](https://www.yamllint.com/)
