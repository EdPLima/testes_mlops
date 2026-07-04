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
