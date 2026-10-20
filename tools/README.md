# Sincronizar os mapas com a sua pasta de .xmind

O portal guarda os mapas dentro dos próprios arquivos `.html`. Este script lê
os seus arquivos `.xmind` e regrava o capítulo correspondente, preservando
títulos, notas, callouts, resumos e marcadores — do jeito que estão no XMind.

## Uma vez só: preparar

Precisa de **Python 3** e do **git** instalados, e de uma cópia do repositório:

```bash
git clone https://github.com/rafalimaribeiro-create/portal-estudos
cd portal-estudos
```

## Sempre que quiser atualizar

```bash
cd portal-estudos
git pull

# 1. ver o que mudaria (não grava nada)
python3 tools/xmind_sync.py ~/Documentos/MapasMentais

# 2. se os pares estiverem certos, gravar
python3 tools/xmind_sync.py ~/Documentos/MapasMentais --apply

# 3. conferir e publicar
git diff --stat
git add -A && git commit -m "Atualiza mapas" && git push
```

Troque `~/Documentos/MapasMentais` pelo caminho da sua pasta. O script varre
as subpastas também.

Depois do `push`, o site leva uns 5 a 10 minutos para atualizar (cache do
GitHub Pages). `Ctrl+Shift+R` força a atualização no navegador.

## Como ele sabe qual arquivo vai em qual capítulo

Na primeira execução ele propõe os pares comparando o nome do arquivo e o
título da raiz do mapa com os capítulos que já existem no portal. Um `~` na
frente da linha significa **palpite por semelhança** — confira esses.

Os pares ficam gravados em `tools/xmind_map.json`. Se algum estiver errado,
edite o arquivo e rode de novo; o que estiver escrito lá tem prioridade sobre
o palpite:

```json
{
  "Cap. 1 - LINDB.xmind": {
    "arquivo": "direito_civil_mapas_v4.html",
    "capitulo": 0
  },
  "3. Relação de Emprego.xmind": {
    "arquivo": "mapas_dtrabalho.html",
    "capitulo": "3. Relação de Emprego"
  }
}
```

O campo `capitulo` é um **número** (posição, começando em zero) para
`direito_civil_mapas_v4.html` e `mapas_admin.html`, e a **chave do capítulo**
para os demais. O que está disponível aparece na saída do script.

Arquivos que não atingirem a semelhança mínima são listados no fim, sem serem
tocados — basta acrescentá-los ao `xmind_map.json`.

## O que é preservado

| No XMind | No portal |
|---|---|
| Tópicos e subtópicos | a árvore, na mesma ordem |
| Notas | bloco recolhível, com "ver tudo" nas longas |
| Callouts (balões) | ramo próprio, em itálico com borda tracejada |
| Resumos | ramo próprio, com o sinal ∑ |
| Marcadores | ⭐ ⬇ ⬆ ❗ ✅ 👍 👎 🚩 antes do texto |

**Ressalva:** `mapas_admin.html`, `mapas_dtrabalho.html` e `mapas_const.html`
usam renderizadores que ainda não desenham callouts como ramo separado. Nesses
três, os callouts entram como filhos comuns — o conteúdo não se perde, mas
perde o destaque visual. Os outros 12 mapas mostram tudo.

## Se algo der errado

O script só mexe no bloco de dados de cada `.html`. Para desfazer antes de
publicar:

```bash
git checkout -- .
```

Para conferir que nada quebrou depois de gravar:

```bash
git diff --stat          # quais arquivos mudaram
```

Abra o mapa no navegador antes de dar `push` — é a verificação mais rápida.
