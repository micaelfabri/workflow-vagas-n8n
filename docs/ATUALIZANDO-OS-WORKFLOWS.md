# Como atualizar os workflows publicados

Os workflows que rodam no meu n8n têm credenciais, chat ID, IDs de etiquetas do Gmail e dados pessoais.
O que vai para o GitHub é sempre a cópia **limpa**, gerada por `scripts/sanitize.py`.

## Onde ficam os arquivos

Os originais e a configuração com dados pessoais ficam em uma pasta **fora** deste repositório,
ao lado dele:

```
Documentos/
├── workflow-vagas-n8n/             # este repositório (vai para o GitHub)
│   ├── workflows/                  # cópias limpas
│   ├── scripts/sanitize.py
│   ├── docs/
│   ├── CHANGELOG.md
│   └── README.md
└── workflow-vagas-n8n-privado/     # NÃO vai para o GitHub
    ├── linkedin.json               # exports originais do n8n
    ├── vagas.json
    ├── candidaturas.json
    └── sanitize.config.json        # dados pessoais e as trocas a fazer
```

O script procura a pasta `<nome-do-repositório>-privado` ao lado do repositório.
Para usar outro lugar, defina a variável de ambiente `N8N_PRIVADO` com o caminho.

## `sanitize.config.json`

```json
{
  "timezone": "America/Sao_Paulo",
  "workflows": [
    {"entrada": "linkedin.json", "saida": "01-linkedin-find-a-job.json", "nome": "LinkedIn Automatic Find a Job", "creditos": true},
    {"entrada": "vagas.json", "saida": "02-vagas-por-email.json", "nome": "Vagas por Email"},
    {"entrada": "candidaturas.json", "saida": "03-candidaturas.json", "nome": "Candidaturas"}
  ],
  "substituir": [["texto pessoal", "texto genérico"]],
  "remover_itens": ["dominio-de-empresa.com.br"],
  "proibidos": ["palavras que nunca podem aparecer no arquivo público"]
}
```

- `substituir`: pares `[original, genérico]` aplicados em ordem (do mais específico para o mais geral).
- `remover_itens`: itens de listas do código (`'dominio.com',`) que identificam empresas.
- `proibidos`: o script **não grava** o arquivo se qualquer um destes termos sobrar.
  Credenciais, IDs e chat IDs são detectados sozinhos, sem precisar listar.

## Passo a passo a cada alteração

1. Edite e teste o workflow no n8n.
2. No n8n: menu **⋯ → Download**. Salve por cima do arquivo correspondente na pasta privada.
3. Dentro do repositório, rode `python scripts/sanitize.py`.
   - Se aparecer `[ERRO] ... NÃO foi gravado`, sobrou algum dado pessoal (veja abaixo).
4. Confira o que mudou: `git diff workflows/`.
5. Anote no `CHANGELOG.md`, em **[Não lançado]**.
6. Commit e envio:
   ```
   git add workflows CHANGELOG.md
   git commit -m "linkedin: descreva a mudança"
   git push
   ```
7. Quando fechar uma versão, mova as linhas de **[Não lançado]** para a nova versão, faça o commit e crie a tag:
   ```
   git tag -a v1.1.0 -m "v1.1.0"
   git push --tags
   ```

## Se o script acusar erro

- **termo proibido**: apareceu um texto pessoal (nome, empresa, etc.) que ainda não tem troca. Adicione um par em `substituir` no config e rode de novo.
- **e-mail com domínio não permitido**: um e-mail entrou em algum nó. Troque ou remova no config.
- **sobrou número longo**: provavelmente um chat ID novo em outro lugar além dos nós de Telegram. Adicione em `substituir`.

## Antes de dar `git add`

Evite `git add .` sem olhar o `git status`. Só `workflows/`, `scripts/`, `docs/`, `CHANGELOG.md`, `README.md` e `.gitignore` devem ir.
