Rodar migrações no banco de dados

# 1. Crie um backup no Neon

Antes da migration 0018, recomendo criar uma branch porque ela pode reagendar posts duplicados antes de aplicar a restrição de data única.

No Neon: https://console.neon.tech/app/projects/tiny-cloud-48098597?branchId=br-flat-fire-a5xn0z0d&database=neondb%20
Abra seu projeto.
Vá em Branches.
Selecione a branch de produção, normalmente main.
Clique em Create branch.
Nomeie como backup-before-migrations.

# 2. Confirme a conexão

No Neon, clique em Connect e selecione:
Branch: produção;
Database: banco usado pela Vercel;
Role: usuário da aplicação.

A string apresentada contém os valores:
NEON_DB_NAME=nome_do_banco
NEON_DB_USER=usuario
NEON_DB_PASSWORD=senha
NEON_DB_HOST=host.neon.tech
NEON_DB_PORT=5432

Esses valores precisam estar disponíveis localmente.

# 3. Ative o ambiente de produção

No PowerShell, dentro do backend, com (.venv) ativo:
```sh
$env:ENVIRONMENT = "production"
```
Isso faz o Django usar o PostgreSQL Neon em vez do SQLite local.

# 4. Veja o plano antes de aplicar

```sh
python.exe manage.py migrate --plan
```
Confira se a conexão funciona e quais migrations serão executadas.

# 5. Aplique as migrations

```sh
python.exe manage.py migrate --noinput
```
O resultado esperado termina com algo semelhante a:
Applying ai_content_agent.0018_post_brand_calendar_constraints... OK

# 6. Confirme

```sh
python.exe manage.py showmigrations ai_content_agent
```
A última migration deve aparecer marcada:
[X] 0018_post_brand_calendar_constraints

# 7. Volte o terminal para desenvolvimento

```sh
Remove-Item Env:ENVIRONMENT
```