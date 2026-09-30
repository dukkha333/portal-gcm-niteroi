# Portal GCM Niterói — máscara institucional

Esta versão é uma **máscara visual para apresentação** do Portal da Guarda Civil Municipal de Niterói. Ela não depende de SQLite, login ou backend.

A navegação principal foi organizada na faixa superior, seguindo a lógica do protótipo apresentado: **PORTAL, PERFIL, DP, INAS, INSTITUCIONAL e PROJETOS**. Ao clicar em uma aba, suas opções aparecem logo abaixo como um menu expandido.

## Identidade visual

A composição prioriza **laranja + branco**, com cinza quente para o fundo e azul-marinho apenas como cor de apoio para textos e elementos institucionais.

A Prefeitura de Niterói mantém um Manual da Marca oficial e a CGCOM informa ser responsável pela gestão da marca da Prefeitura e de suas subordinadas. A implementação desta máscara é uma interpretação visual para apresentação, não uma reprodução certificada do manual. 

## Rodar no Windows

```powershell
cd C:\Users\breno\Desktop\here
python -m pip install -r requirements.txt
python main.py
```

Também é possível executar em modo web pelo Flet:

```powershell
flet run --web --port 8550 main.py
```

## Publicar

O projeto continua compatível com hospedagem ASGI:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

O `render.yaml` mantém a configuração para Render.

## Observação

A versão anterior, com SQLite e funcionalidades administrativas, foi preservada localmente durante a criação desta máscara. O arquivo entregue como `main.py` é intencionalmente demonstrativo.
