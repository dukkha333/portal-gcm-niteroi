# Portal GCM Niterói — Flet + SQLite

Aplicação web em Flet 1.x, preparada para execução local e publicação por GitHub + Render.

## O que foi corrigido

- Migração completa para a API do Flet 1.x: `ft.run`, `ft.Button`, `ft.Alignment.CENTER`, `ft.Icons`, `ft.Padding` etc.
- Exportação ASGI com `app = ft.run(main, export_asgi_app=True)`.
- Inicialização do SQLite mais resistente a concorrência: `timeout`, `busy_timeout`, WAL opcional e tentativas de recuperação.
- Remoção de credenciais administrativas fixas do código.
- Senha inicial de novos servidores pode ser definida por variável de ambiente ou gerada aleatoriamente.
- Banco configurável por `GCM_DB_PATH`. Em ambientes com `/var/data`, esse diretório é usado automaticamente.
- `.gitignore` impede o banco local e segredos de serem enviados ao GitHub.

## Rodar no Windows

No PowerShell:

```powershell
cd C:\caminho\para\gcm_portal_fixed

py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

$env:GCM_BOOTSTRAP_ADMIN_MATRICULA="9001"
$env:GCM_BOOTSTRAP_ADMIN_NOME="Administrador"
$env:GCM_BOOTSTRAP_ADMIN_PASSWORD="TROQUE-ESTA-SENHA"

python main.py
```

O navegador local abrirá o app. Para desenvolvimento web, também pode usar:

```powershell
flet run --web --port 8550 main.py
```

## Publicar no GitHub + Render

1. Crie um repositório no GitHub e envie `main.py`, `requirements.txt`, `render.yaml`, `.gitignore` e `.env.example`.
2. No Render, crie um **New Web Service** a partir do repositório ou faça o deploy pelo `render.yaml`.
3. O comando de inicialização é:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

4. Nas variáveis de ambiente do Render, informe:
   - `GCM_BOOTSTRAP_ADMIN_PASSWORD`: uma senha forte para o primeiro administrador.
   - `GCM_BOOTSTRAP_ADMIN_MATRICULA`: por exemplo, `9001`.
   - `GCM_BOOTSTRAP_ADMIN_NOME`: nome do administrador.
   - `GCM_DEMO_MODE=false`.
   - `GCM_DB_PATH=/var/data/gcm_database.db` **somente se você tiver montado um Persistent Disk em `/var/data`**. Sem disco, deixe essa variável ausente.

Depois do deploy, o Render fornecerá uma URL pública `https://...onrender.com`. Essa é a URL para abrir no celular, de qualquer rede.

## Persistência dos dados

O Render usa sistema de arquivos efêmero por padrão. Para manter o SQLite após reinícios/deploys, monte um **Persistent Disk** em `/var/data`. Em Render, Persistent Disks são recurso de serviços pagos e ficam vinculados a uma única instância. Para uma aplicação com muitos usuários ou múltiplas instâncias, prefira um banco gerenciado, como PostgreSQL.

## Sobre o erro `database is locked`

Se o erro aparecer apenas no Windows durante desenvolvimento, normalmente existe outra instância antiga do `python.exe` usando o mesmo `gcm_database.db`.

Você pode encerrar as instâncias antigas:

```powershell
taskkill /F /IM python.exe
```

Depois rode novamente. Não apague `gcm_database.db` se houver dados que você queira preservar.

## Segurança

Não publique senhas reais no GitHub. O modo de demonstração fica desligado por padrão. As credenciais iniciais devem ser fornecidas por variáveis de ambiente no servidor.
