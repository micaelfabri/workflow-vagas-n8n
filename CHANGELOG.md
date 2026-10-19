# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões do repositório seguem `MAJOR.MINOR.PATCH`:

- **MAJOR**: mudou a estrutura e quem já usa precisa reimportar e reconfigurar (nós novos, credenciais, etiquetas).
- **MINOR**: recurso novo ou regra nova que não quebra o que já funciona.
- **PATCH**: correção de bug, ajuste de texto ou de prompt.

Cada workflow também tem a sua versão própria, anotada abaixo.

## [Não lançado]

## [1.0.0] - 2026-10-17

Primeira versão pública.

### 01 · LinkedIn Automatic Find a Job (v2)
- Base: tutorial de Rafa Ballerini (veja os créditos no README).
- Busca vagas pelo Apify, filtra por título e avalia com a IA (Groq).
- Memória entre execuções: vaga já avaliada não volta a ser enviada.
- Nota calculada por regra no código (a IA só classifica), com tetos para descrição curta, nível pleno/sênior, fora de TI e fora da região.
- Modelo reserva no Groq para o score e para a carta (os limites do Groq são por modelo).
- Carta de apresentação: a IA escreve só o miolo; saudação, apresentação e assinatura são fixas.
- Mensagem do Telegram em HTML, com link limpo (sem parâmetros de rastreio).

### 02 · Vagas por Email (v2)
- Lê os alertas de vagas do Gmail (LinkedIn, Glassdoor, Indeed) e manda as compatíveis ao Telegram.
- Nota que parte de 100, com descontos e bônus; avisos de salário abaixo do mínimo.
- Marca os e-mails processados com etiquetas e como lidos.
- Backfill manual por webhook (`?dias=60` ou `?inicio=AAAA/MM/DD&fim=AAAA/MM/DD`).
- Modelo reserva no Groq.

### 03 · Candidaturas (v1)
- Acompanha as respostas de candidaturas pelo Gmail e mantém um painel (webhook).
- Classificação por regras (confirmação, etapa, entrevista, recusa, oferta); a IA só extrai empresa, vaga e prazo.
- Alerta no Telegram apenas quando precisa de ação (etapa, entrevista) ou quando o status muda.
- Etiqueta e marca como lidos os e-mails processados; backfill histórico por webhook.
- Roda 3 vezes ao dia.
