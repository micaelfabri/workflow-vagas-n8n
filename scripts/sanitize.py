#!/usr/bin/env python3
"""
Gera as cópias PÚBLICAS dos workflows a partir dos exports PRIVADOS do n8n.

Fluxo de atualização (versionamento):
  1. No n8n: ⋯ > Download, e salve o JSON na pasta PRIVADA (fora deste repositório, veja abaixo).
  2. python scripts/sanitize.py
  3. git diff workflows/   -> confira o que mudou
  4. Atualize o CHANGELOG.md, faça o commit e (se for uma versão nova) a tag.

O que o script faz sozinho (genérico):
  - remove credenciais, ids da instância/workflow, versionId, tags, pinData e dados de execução;
  - troca chat IDs do Telegram e IDs de etiquetas do Gmail por marcadores;
  - troca o perfil do candidato dentro dos prompts por um modelo para preencher;
  - zera o salário mínimo e a previsão de formatura usados na nota;
  - marca o workflow como inativo e fixa o fuso America/Sao_Paulo;
  - adiciona uma nota de créditos no workflow do LinkedIn;
  - confere se sobrou algum dado pessoal e ABORTA se sobrou.

Os exports originais e os dados pessoais (nome, empregadores, etc.) ficam numa pasta
PRIVADA FORA do repositório, por padrão a pasta irmã "<nome-do-repo>-privado"
(ex.: workflow-vagas-n8n-privado/), com o arquivo sanitize.config.json.
Para usar outro lugar: variável de ambiente N8N_PRIVADO.
Nenhum dado pessoal está neste arquivo.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = Path(os.environ.get("N8N_PRIVADO") or (ROOT.parent / (ROOT.name + "-privado")))
OUT = ROOT / "workflows"
CONFIG = PRIV / "sanitize.config.json"

# Domínios de e-mail aceitos nos workflows públicos (plataformas de vagas, não pessoas/empresas)
EMAILS_PERMITIDOS = ("linkedin.com", "glassdoor.com", "indeed.com", "google.com")

PERFIL_SIMPLES = """PERFIL DO CANDIDATO (única fonte de verdade) — <<PREENCHA COM OS SEUS DADOS>>:
- Busca: <<tipo de vaga: estágio, júnior...>>. Prioridade 1: <<área principal>>. Prioridade 2: <<áreas secundárias>>.
- Formação: <<curso, nível e ano de conclusão ou previsão>>.
- Habilidades comprovadas: <<só o que você realmente sabe usar>>.
- Em andamento (NÃO conta como habilidade atendida): <<o que está estudando>>.
- O candidato NÃO tem: <<ferramentas que as vagas costumam pedir e você não tem>>.
- Projeto: <<seu projeto principal, com as tecnologias usadas>>.
- Experiência: <<suas experiências reais, sem inventar cargo>>.
- Local: <<cidade/região e se aceita remoto>>."""

PERFIL_POR_NIVEL = """PERFIL DO CANDIDATO — <<PREENCHA COM OS SEUS DADOS>>:
- Busca: <<tipo de vaga e áreas de interesse>>.
- Formação: <<curso, nível e ano de conclusão ou previsão>>.
- Habilidades por nível:
  * Intermediário: <<...>>
  * Básico/iniciante: <<...>>
  * Em estudo: <<...>>
  * Não tem: <<ferramentas que as vagas costumam pedir e você não tem>>.
- Projeto: <<seu projeto principal, com as tecnologias usadas>>.
- Experiência real: <<suas experiências reais, sem inventar cargo>>.
- Local: <<cidade/região e se aceita remoto>>."""

CARTA_COM_NOME = """DADOS DO CANDIDATO (use somente estas informações) — <<PREENCHA>>:
- Nome: <<SEU NOME>>
- GitHub: <<github.com/SEU-USUARIO>>
- Formação: <<curso, nível e ano>>
- Técnicas: <<suas habilidades reais>>
- Projeto: <<seu projeto principal>>
- Experiência: <<suas experiências reais>>"""

CARTA_SEM_NOME = """DADOS DO CANDIDATO (use somente estas informações) — <<PREENCHA>>:
- Habilidades comprovadas: <<suas habilidades reais>>
- Projeto: <<seu projeto principal>>
- Experiência: <<suas experiências reais>>
- Em andamento: <<o que está estudando; só pode ser citado como "estudando ...">>"""

CREDITOS = (
    "## Créditos\n\n"
    "Este workflow parte do tutorial de **Rafa Ballerini** (@rafaellaballerini):\n"
    "- Vídeo: https://www.youtube.com/watch?v=sq8ThaXkp7k\n"
    "- Códigos e textos: https://github.com/rafaballerini/CodigosBuscaDeEmpregoN8N\n"
    "- Como adicionar as credenciais: https://github.com/rafaballerini/CredenciaisVagasDeEmprego\n\n"
    "Adaptações: nota calculada por regra, memória entre execuções (sem vaga repetida), "
    "modelos reserva no Groq e carta com dados fixos.\n\n"
    "**Antes de usar:** preencha o PERFIL nos prompts, o NOME/GitHub no nó 'Montar mensagem', "
    "o chat ID do Telegram e selecione as suas credenciais."
)


def carregar_config():
    if not CONFIG.exists():
        sys.exit(f"Falta {CONFIG}.\nCrie a pasta privada fora do repositório e coloque nela o sanitize.config.json "
                 f"e os exports do n8n (veja docs/ATUALIZANDO-OS-WORKFLOWS.md).")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def conferir_gitignore():
    """Se a pasta privada estiver DENTRO do repositório, ela precisa estar no .gitignore."""
    try:
        rel = PRIV.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return  # fora do repositório: nada a fazer
    gi = ROOT / ".gitignore"
    if not gi.exists() or (rel.as_posix() + "/") not in gi.read_text(encoding="utf-8"):
        sys.exit(f"A pasta privada está dentro do repositório e '{rel.as_posix()}/' não está no .gitignore. Abortei.")


def percorrer(x, fn):
    """Aplica fn a todas as strings do JSON (valores e itens de listas)."""
    if isinstance(x, dict):
        return {k: percorrer(v, fn) for k, v in x.items()}
    if isinstance(x, list):
        return [percorrer(v, fn) for v in x]
    if isinstance(x, str):
        return fn(x)
    return x


def coletar_segredos(wf):
    """Tudo que identifica a conta/instância do dono do arquivo original."""
    achados = set()
    for k in ("id", "versionId"):
        if isinstance(wf.get(k), str):
            achados.add(wf[k])
    iid = (wf.get("meta") or {}).get("instanceId")
    if iid:
        achados.add(iid)
    for n in wf.get("nodes", []):
        for cred in (n.get("credentials") or {}).values():
            for k in ("id", "name"):
                if cred.get(k):
                    achados.add(cred[k])
        cid = str((n.get("parameters") or {}).get("chatId", ""))
        if re.fullmatch(r"-?\d{5,}", cid):
            achados.add(cid)
    return {a for a in achados if len(a) >= 4}


def limpar(wf, item, cfg, relatorio):
    segredos = coletar_segredos(wf)
    wf = json.loads(json.dumps(wf))  # cópia

    # --- metadados da instância
    wf["name"] = item["nome"]
    for k in ("id", "versionId", "tags", "staticData"):
        wf.pop(k, None)
    wf["tags"] = []
    wf["pinData"] = {}
    wf["meta"] = {}
    wf["active"] = False
    wf.setdefault("settings", {})["timezone"] = cfg.get("timezone", "America/Sao_Paulo")

    # --- por nó
    for n in wf["nodes"]:
        n.pop("credentials", None)
        p = n.get("parameters", {})
        if n["type"].endswith(".telegram") and "chatId" in p:
            p["chatId"] = "SEU_CHAT_ID_DO_TELEGRAM"

    # --- substituições exatas definidas no config privado (em ordem)
    def aplicar_config(s):
        for velho, novo in cfg.get("substituir", []):
            if velho in s:
                relatorio["substituir"][velho] = relatorio["substituir"].get(velho, 0) + s.count(velho)
                s = s.replace(velho, novo)
        # itens de lista que identificam empresas ('dominio.com',)
        for termo in cfg.get("remover_itens", []):
            t = re.escape(termo)
            novo = re.sub(r"\s*'" + t + r"'\s*,", "", s)
            novo = re.sub(r",\s*'" + t + r"'", "", novo)
            if novo != s:
                relatorio["remover"][termo] = relatorio["remover"].get(termo, 0) + 1
                s = novo
        return s

    wf = percorrer(wf, aplicar_config)

    # --- regras genéricas
    def generico(s):
        # IDs de etiquetas do Gmail
        s = re.sub(r"^Label_\w+$", "ID_DA_SUA_ETIQUETA", s)
        # perfil do candidato nos prompts de nota
        def perfil(m):
            return PERFIL_POR_NIVEL if "Habilidades por nível" in m.group(0) else PERFIL_SIMPLES
        s = re.sub(r"PERFIL DO CANDIDATO[^\n]*\n.*?(?=\n\nDADOS DA VAGA:)", perfil, s, flags=re.S)
        # dados do candidato nos prompts de carta
        def carta(m):
            return CARTA_COM_NOME if "- Nome:" in m.group(0) else CARTA_SEM_NOME
        s = re.sub(r"DADOS DO CANDIDATO \(use somente estas informações\):.*?(?=\s*REGRAS:)", carta, s, flags=re.S)
        # preferências financeiras / de formatura usadas na nota
        s = re.sub(
            r"const SALARIO_MINIMO = \d+;[^\n]*",
            "const SALARIO_MINIMO = 0;        // AJUSTE: abaixo disso aparece aviso e desconto (0 desliga)\n"
            "    const ANO_FORMATURA = 2030;      // AJUSTE: ano da sua formatura (vagas que exigem formatura antes são penalizadas)",
            s,
        )
        return s

    wf = percorrer(wf, generico)

    # --- créditos no LinkedIn
    if item.get("creditos"):
        wf["nodes"].append({
            "parameters": {"content": CREDITOS, "height": 400, "width": 460},
            "id": "9a7c1e52-3d4b-4f60-8a11-6c2e5b7d9f03",
            "name": "Créditos",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [4416, 96],
        })
    return wf, segredos


def verificar(wf, segredos, cfg, arquivo):
    """Aborta se sobrou qualquer dado pessoal."""
    texto = json.dumps(wf, ensure_ascii=False)
    proibidos = set(segredos) | set(cfg.get("proibidos", []))
    problemas = []
    for termo in sorted(proibidos):
        if termo and re.search(r"(?<![A-Za-z0-9])" + re.escape(termo) + r"(?![A-Za-z0-9])", texto, re.I):
            problemas.append(f"termo proibido: {termo!r}")
    for m in set(re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", texto)):
        if not m.endswith(EMAILS_PERMITIDOS):
            problemas.append(f"e-mail com domínio não permitido: @{m}")
    if re.search(r"\bLabel_\w+", texto):
        problemas.append("sobrou ID de etiqueta do Gmail")
    if '"credentials"' in texto:
        problemas.append("sobrou bloco de credenciais")
    if re.search(r"\b\d{9,}\b", texto):
        problemas.append("sobrou número longo (chat ID?): " + ", ".join(sorted(set(re.findall(r'\b\d{9,}\b', texto)))))
    if problemas:
        print(f"\n[ERRO] {arquivo} NÃO foi gravado:")
        for p in problemas:
            print("  -", p)
        return False
    return True


def main():
    conferir_gitignore()
    cfg = carregar_config()
    OUT.mkdir(exist_ok=True)
    falhou = False
    for item in cfg["workflows"]:
        origem = PRIV / item["entrada"]
        if not origem.exists():
            print(f"[pulado] {origem.name} não encontrado em privado/")
            continue
        wf = json.loads(origem.read_text(encoding="utf-8"))
        relatorio = {"substituir": {}, "remover": {}}
        limpo, segredos = limpar(wf, item, cfg, relatorio)
        if not verificar(limpo, segredos, cfg, item["saida"]):
            falhou = True
            continue
        (OUT / item["saida"]).write_text(json.dumps(limpo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {item['saida']}  ({len(limpo['nodes'])} nós)")
        paradas = [t for t, _ in cfg.get("substituir", []) if t not in relatorio["substituir"]]
        if paradas and item.get("avisar_substituicoes_sem_uso", False):
            print("     (substituições sem uso neste arquivo:", len(paradas), ")")
    if falhou:
        sys.exit(1)


if __name__ == "__main__":
    main()
