#!/usr/bin/env python3
"""
Sincroniza mapas mentais .xmind com o portal.

Uso:
    python3 tools/xmind_sync.py ~/MinhaPastaDeMapas            # mostra o que faria
    python3 tools/xmind_sync.py ~/MinhaPastaDeMapas --apply    # grava de verdade

O script varre a pasta (incluindo subpastas) atrás de arquivos .xmind,
converte cada um preservando títulos, notas, callouts, resumos e marcadores,
e grava no capítulo correspondente do mapa do portal.

O pareamento arquivo -> capítulo fica guardado em tools/xmind_map.json.
Na primeira vez o script propõe os pares por semelhança de nome; corrija o
que estiver errado nesse arquivo e rode de novo — ele respeita o que estiver
escrito lá.
"""

import argparse, base64, difflib, json, os, re, sys, unicodedata
from xml.etree import ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAREAMENTO = os.path.join(RAIZ, 'tools', 'xmind_map.json')

MARCADORES = {
    'star-red': '⭐', 'star-yellow': '⭐', 'star-blue': '⭐',
    'star-green': '⭐', 'star-orange': '⭐', 'star-purple': '⭐',
    'arrow-down': '⬇', 'arrow-up': '⬆',
    'arrow-left': '⬅', 'arrow-right': '➡',
    'symbol-exclam': '❗', 'symbol-question': '❓',
    'symbol-info': 'ℹ', 'symbol-attention': '⚠',
    'task-start': '▶', 'task-done': '✅',
    'c_symbol_like': '\U0001f44d', 'c_symbol_dislike': '\U0001f44e',
    'flag-red': '\U0001f6a9', 'flag-yellow': '\U0001f6a9', 'flag-green': '\U0001f6a9',
}

# ─────────────────────────── leitura do .xmind ───────────────────────────

def _limpa_ns(xml):
    xml = re.sub(r'<(/?)[a-zA-Z0-9]+:', r'<\1', xml)
    xml = re.sub(r'\s[a-zA-Z0-9]+:[a-zA-Z-]+="[^"]*"', '', xml)
    return re.sub(r' xmlns(?::[a-zA-Z0-9]+)?="[^"]*"', '', xml)


def _conteudo(caminho):
    """Devolve o content.xml de dentro do .xmind (que é um zip)."""
    import zipfile
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        if 'content.xml' not in nomes:
            return None
        return z.read('content.xml').decode('utf-8', 'replace')


def _titulo(t):
    e = t.find('title')
    return (e.text or '').strip() if (e is not None and e.text) else ''


def _notas(t):
    n = t.find('notes')
    if n is None:
        return None
    pl = n.find('plain')
    if pl is not None and pl.text and pl.text.strip():
        return pl.text.strip()
    h = n.find('html')
    if h is not None:
        partes = [''.join(p.itertext()).strip() for p in h.iter('p')]
        s = '\n'.join(x for x in partes if x).strip()
        if s:
            return s
    return None


def _no(t):
    no = {'title': _titulo(t)}
    nv = _notas(t)
    if nv:
        no['notes'] = nv
    vistos = []
    for m in t.findall('marker-refs/marker-ref'):
        ic = MARCADORES.get(m.get('marker-id'))
        if ic and ic not in vistos:
            vistos.append(ic)
    if vistos:
        no['mk'] = ''.join(vistos)
    filhos, callouts, resumos = [], [], []
    for ts in t.findall('children/topics'):
        tipo = ts.get('type')
        for c in ts.findall('topic'):
            p = _no(c)
            if tipo == 'attached':
                filhos.append(p)
            elif tipo == 'callout':
                callouts.append(p)
            elif tipo == 'summary':
                resumos.append(p)
    if callouts:
        no['callouts'] = callouts
    if resumos:
        no['summaries'] = resumos
    if filhos:
        no['children'] = filhos
    return no


def le_xmind(caminho):
    xml = _conteudo(caminho)
    if xml is None:
        return None
    raiz = ET.fromstring(_limpa_ns(xml))
    folha = raiz.find('sheet')
    if folha is None:
        return None
    topo = folha.find('topic')
    if topo is None:
        return None
    no = _no(topo)
    # mapa "desbalanceado": o XMind guarda quantos ramos da raiz ficam à
    # direita. Sem isso o portal dividiria pela metade e trocaria os lados.
    m = re.search(r'<right-number>(\d+)</right-number>', xml)
    if m:
        no['rn'] = int(m.group(1))
    return no


def conta(n):
    c = 1
    for k in ('children', 'callouts', 'summaries'):
        for x in n.get(k, []):
            c += conta(x)
    return c

# ───────────────────── conversão para cada formato ─────────────────────

def _para(no, campo_titulo, campo_filhos, aceita_ricos):
    """Reescreve a árvore nos nomes de campo que o mapa de destino usa."""
    saida = {campo_titulo: no.get('title', '')}
    if no.get('rn') is not None:
        saida['rn'] = no['rn']
    if no.get('notes'):
        saida['notes'] = no['notes']
    if no.get('mk') and aceita_ricos:
        saida['mk'] = no['mk']
    filhos = [_para(c, campo_titulo, campo_filhos, aceita_ricos) for c in no.get('children', [])]
    extras = no.get('callouts', []) + no.get('summaries', [])
    if aceita_ricos:
        if no.get('callouts'):
            saida['callouts'] = [_para(c, campo_titulo, campo_filhos, True) for c in no['callouts']]
        if no.get('summaries'):
            saida['summaries'] = [_para(c, campo_titulo, campo_filhos, True) for c in no['summaries']]
    else:
        # o renderizador deste mapa não conhece callouts: entram como filhos
        # comuns, para que nenhum conteúdo se perca
        filhos += [_para(c, campo_titulo, campo_filhos, False) for c in extras]
    if filhos:
        saida[campo_filhos] = filhos
    return saida

# ──────────────────── leitura/escrita do bloco de dados ────────────────────

class Mapa:
    """Um arquivo .html do portal e a forma como ele guarda os dados."""

    def __init__(self, arquivo):
        self.arquivo = arquivo
        self.caminho = os.path.join(RAIZ, arquivo)
        self.fonte = open(self.caminho, encoding='utf-8').read()
        self.formato = self._detecta()

    def _detecta(self):
        s = self.fonte
        if 'id="maps-data"' in s:        return 'maps-data'
        if 'const ALL_DATA' in s:        return 'ALL_DATA'
        if 'const MAPAS_DATA' in s:      return 'MAPAS_DATA'
        if 'const DATA_B64' in s:        return 'DATA_B64'
        if 'const RAW = `' in s:         return 'RAW-template'
        if 'const RAW = "' in s:         return 'RAW-string'
        raise ValueError('formato desconhecido: ' + self.arquivo)

    # como cada formato nomeia os campos de um nó, e se aceita callouts
    CAMPOS = {
        'maps-data':    ('title', 'children', True),
        'ALL_DATA':     ('t',     'c',        False),
        'MAPAS_DATA':   ('label', 'children', False),
        'DATA_B64':     ('text',  'children', False),
        'RAW-template': ('title', 'children', True),
        'RAW-string':   ('title', 'children', True),
    }

    _JS_ESC = {'n': '\n', 't': '\t', 'r': '\r', 'b': '\b', 'f': '\f', 'v': '\v', '0': '\0'}

    @classmethod
    def _desescapa_template(cls, s):
        """Texto de um template literal como o JavaScript o entrega.

        O arquivo guarda o JSON com as barras duplicadas justamente para que
        o JS as desfaça; ler o texto cru daria um JSON diferente do que roda
        no navegador.
        """
        saida, i, n = [], 0, len(s)
        while i < n:
            c = s[i]
            if c != '\\' or i + 1 >= n:
                saida.append(c); i += 1; continue
            d = s[i + 1]
            if d == 'u' and i + 5 < n:
                try:
                    saida.append(chr(int(s[i + 2:i + 6], 16))); i += 6; continue
                except ValueError:
                    pass
            if d == 'x' and i + 3 < n:
                try:
                    saida.append(chr(int(s[i + 2:i + 4], 16))); i += 4; continue
                except ValueError:
                    pass
            saida.append(cls._JS_ESC.get(d, d)); i += 2
        return ''.join(saida)

    @staticmethod
    def _escapa_template(s):
        return s.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

    @staticmethod
    def _fim_literal(s, i, fecha):
        """Fim de um literal JS aberto em i, respeitando as barras de escape.

        Um regex preguiçoso não serve aqui: a própria string contém \\" e \\`,
        e o trecho ";\\n de um \\"; interno encerraria a captura cedo demais.
        """
        while i < len(s):
            c = s[i]
            if c == '\\':
                i += 2
                continue
            if c == fecha:
                return i
            i += 1
        raise ValueError('literal sem fechamento')

    def _trecho(self):
        """(ini, fim) do conteúdo bruto dentro do arquivo."""
        f, s = self.formato, self.fonte
        if f == 'maps-data':
            m = re.search(r'id="maps-data">', s)
            ini = m.end()
            return ini, s.index('</script>', ini)
        if f == 'ALL_DATA':
            ini = s.index('const ALL_DATA = ') + len('const ALL_DATA = ')
            fim = s.index('\n', ini)
            while s[fim - 1] in ';\r':
                fim -= 1
            return ini, fim
        if f == 'MAPAS_DATA':
            ini = s.index('const MAPAS_DATA = ') + len('const MAPAS_DATA = ')
            fim = s.index(';\n', ini)
            return ini, fim
        if f == 'DATA_B64':
            ini = s.index('const DATA_B64 = "') + len('const DATA_B64 = "')
            return ini, s.index('"', ini)
        if f == 'RAW-template':
            ini = s.index('const RAW = `') + len('const RAW = `')
            return ini, self._fim_literal(s, ini, '`')
        ini = s.index('const RAW = "') + len('const RAW = "')
        return ini, self._fim_literal(s, ini, '"')

    def dados(self):
        f = self.formato
        ini, fim = self._trecho()
        bruto = self.fonte[ini:fim]
        if f == 'DATA_B64':
            return json.loads(base64.b64decode(bruto).decode('utf-8'))
        if f == 'RAW-string':
            return json.loads(json.loads('"' + bruto + '"'))
        if f == 'RAW-template':
            return json.loads(self._desescapa_template(bruto))
        return json.loads(bruto)

    def grava(self, dados):
        f = self.formato
        ini, fim = self._trecho()
        bruto = json.dumps(dados, ensure_ascii=False, separators=(',', ':'))
        if f == 'DATA_B64':
            corpo = base64.b64encode(bruto.encode('utf-8')).decode('ascii')
        elif f == 'RAW-string':
            corpo = json.dumps(bruto, ensure_ascii=False)[1:-1]
        elif f == 'RAW-template':
            corpo = self._escapa_template(bruto)
        else:
            corpo = bruto
        novo = self.fonte[:ini] + corpo + self.fonte[fim:]
        open(self.caminho, 'w', encoding='utf-8').write(novo)
        self.fonte = novo

    def capitulos(self):
        """[(chave, rótulo)] na ordem em que aparecem."""
        d = self.dados()
        f = self.formato
        if f == 'maps-data':
            return [(i, c.get('label', '')) for i, c in enumerate(d)]
        if f == 'DATA_B64':
            return [(i, c.get('text', '')) for i, c in enumerate(d)]
        if f == 'ALL_DATA':
            rot = {}
            m = re.search(r'const CHAPTERS_META = (\[.*?\]);', self.fonte, re.DOTALL)
            if m:
                rot = {x['key']: x.get('label', x['key']) for x in json.loads(m.group(1))}
            return [(k, rot.get(k, k)) for k in d]
        if f == 'MAPAS_DATA':
            return [(k, k) for k in d]
        m = re.search(r'LABELS *= *(\{.*?\});', self.fonte, re.DOTALL)
        rot = json.loads(m.group(1)) if m else {}
        return [(k, rot.get(k, k)) for k in d]

    def raiz_do(self, dados, chave):
        f = self.formato
        if f == 'maps-data':
            return dados[chave]['data'][0]['root']
        return dados[chave]

    def define_raiz(self, dados, chave, no):
        f = self.formato
        if f == 'maps-data':
            dados[chave]['data'][0]['root'] = no
        else:
            dados[chave] = no

# ─────────────────────────── pareamento ───────────────────────────

def normaliza(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\b(cap|capitulo|parte|geral)\b', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def arquivos_html():
    nomes = sorted(x for x in os.listdir(RAIZ)
                   if x.startswith('mapas_') and x.endswith('.html'))
    if os.path.exists(os.path.join(RAIZ, 'direito_civil_mapas_v4.html')):
        nomes.append('direito_civil_mapas_v4.html')
    return nomes


def _sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def propoe(nome_arquivo, titulo_raiz, candidatos):
    """Melhor (arquivo, chave, rótulo), nota entre todos os capítulos.

    Pontua cada sinal por si: nome do arquivo e título da raiz, cada um
    contra o rótulo do capítulo e contra o título da raiz que ele já tem.
    Misturar os dois num texto só diluía o acerto.
    """
    nome = normaliza(os.path.splitext(os.path.basename(nome_arquivo))[0])
    raiz = normaliza(titulo_raiz or '')
    melhor, nota = None, 0.0
    for arq, chave, rotulo, raiz_atual in candidatos:
        r, ra = normaliza(rotulo), normaliza(raiz_atual or '')
        n = max(_sim(nome, r), _sim(raiz, r), _sim(nome, ra), _sim(raiz, ra))
        if n > nota:
            melhor, nota = (arq, chave, rotulo), n
    return melhor, nota

# ─────────────────────────────── principal ───────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Sincroniza .xmind com os mapas do portal.')
    ap.add_argument('pasta', help='pasta com os arquivos .xmind (varre subpastas)')
    ap.add_argument('--apply', action='store_true', help='grava; sem isso, só mostra')
    ap.add_argument('--min', type=float, default=0.55,
                    help='semelhança mínima para parear automaticamente (0-1)')
    args = ap.parse_args()

    if not os.path.isdir(args.pasta):
        sys.exit('pasta não encontrada: ' + args.pasta)

    achados = []
    for base, _, arqs in os.walk(args.pasta):
        for a in sorted(arqs):
            if a.lower().endswith('.xmind') and not a.startswith('.'):
                achados.append(os.path.join(base, a))
    if not achados:
        sys.exit('nenhum .xmind encontrado em ' + args.pasta)

    mapas = {}
    candidatos = []
    for arq in arquivos_html():
        try:
            mp = Mapa(arq)
        except ValueError as e:
            print('  ignorado:', e)
            continue
        mapas[arq] = mp
        _d = mp.dados()
        _ct = Mapa.CAMPOS[mp.formato][0]
        for chave, rotulo in mp.capitulos():
            try:
                _ra = mp.raiz_do(_d, chave).get(_ct, '')
            except Exception:
                _ra = ''
            candidatos.append((arq, chave, rotulo, _ra))

    salvo = {}
    if os.path.exists(PAREAMENTO):
        salvo = json.load(open(PAREAMENTO, encoding='utf-8'))

    print(f'{len(achados)} arquivo(s) .xmind | {len(mapas)} mapas | {len(candidatos)} capítulos\n')

    planos, novos_pares, sem_par = [], {}, []
    for caminho in achados:
        nome = os.path.basename(caminho)
        try:
            arvore = le_xmind(caminho)
        except Exception as e:
            print(f'  ERRO ao ler {nome}: {e}')
            continue
        if arvore is None:
            print(f'  ERRO: {nome} não tem content.xml legível')
            continue

        if nome in salvo:
            arq, chave = salvo[nome]['arquivo'], salvo[nome]['capitulo']
            if isinstance(chave, str) and arq in mapas and mapas[arq].formato in ('maps-data', 'DATA_B64'):
                chave = int(chave)
            rotulo = dict(((a, k), r) for a, k, r, _ in candidatos).get((arq, chave), '?')
            nota = 1.0
        else:
            melhor, nota = propoe(nome, arvore.get('title', ''), candidatos)
            if not melhor or nota < args.min:
                sem_par.append((nome, arvore.get('title', '')[:40], nota))
                continue
            arq, chave, rotulo = melhor
            novos_pares[nome] = {'arquivo': arq, 'capitulo': chave}

        planos.append((caminho, nome, arq, chave, rotulo, arvore, nota))

    por_mapa = {}
    for p in planos:
        por_mapa.setdefault(p[2], []).append(p)

    for arq, itens in sorted(por_mapa.items()):
        mp = mapas[arq]
        dados = mp.dados()
        ct, cf, ricos = Mapa.CAMPOS[mp.formato]
        print(f'{arq}  [{mp.formato}]' + ('' if ricos else '  (callouts entram como filhos)'))
        for caminho, nome, _, chave, rotulo, arvore, nota in itens:
            antes = conta(mp.raiz_do(dados, chave))
            convertido = _para(arvore, ct, cf, ricos)
            depois = conta(convertido)
            marca = ' ' if nota >= 0.999 else '~'
            print(f'   {marca} {nome[:44]:<46} -> {str(rotulo)[:34]:<36} {antes:5d} -> {depois:5d} nós')
            if args.apply:
                mp.define_raiz(dados, chave, convertido)
        if args.apply:
            mp.grava(dados)
        print()

    if sem_par:
        print('sem par (semelhança baixa) — acrescente à mão em tools/xmind_map.json:')
        for nome, titulo, nota in sem_par:
            print(f'   {nome[:50]:<52} raiz="{titulo}"  melhor={nota:.2f}')
        print()

    if args.apply:
        salvo.update(novos_pares)
        os.makedirs(os.path.dirname(PAREAMENTO), exist_ok=True)
        json.dump(salvo, open(PAREAMENTO, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2, sort_keys=True)
        print(f'gravado. pareamento salvo em tools/xmind_map.json ({len(salvo)} entradas)')
        print('confira com "git diff" e publique com "git add -A && git commit && git push".')
    else:
        print('nada foi gravado. repita com --apply para valer.')
        print('"~" marca pares adivinhados por semelhança — confira antes.')


if __name__ == '__main__':
    main()
