import sys, glob, os

BASE = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else './'
miss = []

def s(src, old, new, lbl):
    global miss
    if old not in src:
        miss.append(lbl); return src
    return src.replace(old, new, 1)

# -- shared CSS --
CSS = """.qblock{margin:4px 0 3px 20px;border-left:2px solid rgba(128,128,128,.3);padding:2px 0 2px 11px;}
.qline{font-size:12px;font-style:italic;opacity:.75;padding:1.5px 0;display:flex;gap:7px;align-items:baseline;line-height:1.5;}
.qline .qm{font-style:normal;font-size:10px;opacity:.7;flex-shrink:0;color:var(--accent,#7aa2f7);}
"""

# -- shared JS helper --
HELPER = """var _QQ=/\\?\\s*$/;
function _qSplit(t){
  if(!t)return null;
  var L=String(t).replace(/\\r\\n/g,'\\n').replace(/\\r/g,'\\n').split('\\n')
        .map(function(x){return x.trim();}).filter(function(x){return x;});
  if(L.length<3)return null;
  var h=L[0];
  if(h.length>60||_QQ.test(h))return null;
  for(var i=1;i<L.length;i++){if(!_QQ.test(L[i]))return null;}
  return {head:h,qs:L.slice(1)};
}
"""

ALL = sorted(glob.glob(BASE + 'mapas_*.html')) + [BASE + 'direito_civil_mapas_v4.html']

SIGS = {
    'mapas_const.html':            'function renderNode(node, depth) {',
    'direito_civil_mapas_v4.html': '  function renderNode(node, container, depth, path) {',
    'mapas_admin.html':            '  function buildNode(node, depth, path) {',
    'mapas_dtrabalho.html':        'function buildTree(node, depth) {',
}
DEFAULT_SIG = 'function renderNode(n,depth,path){'

for p in ALL:
    name = os.path.basename(p)
    src = open(p, encoding='utf-8').read()
    if '_qSplit' in src:
        print(f'  skip (done): {name}'); continue
    src = s(src, '</style>', CSS + '</style>', f'{name}:css')
    sig = SIGS.get(name, DEFAULT_SIG)
    src = s(src, sig, HELPER + sig, f'{name}:helper')
    open(p, 'w', encoding='utf-8').write(src)

# -- Variant 1: standard renderNode --
STD_OLD = """  const _ie=_inlineExams(n.title||'');
  let titleHtml;
  if(_ie){"""
STD_NEW = """  const _q=_qSplit(n.title||'');
  const _ie=_q?null:_inlineExams(n.title||'');
  let titleHtml;
  if(_q){
    titleHtml=`<span class="txt ${dc}">${hilite(_q.head,term)}</span>`;
  } else if(_ie){"""

STD_RET_OLD = """  return `<div class="node" id="n${id}"><div class="${rowCls}" onclick="toggle('${id}')"><span class="tog">${tog}</span>${titleHtml}</div>${childHtml}</div>`;"""
STD_RET_NEW = """  const _qh=_q?`<div class="qblock">${_q.qs.map(function(x){return `<div class="qline"><span class="qm">?</span><span>${hilite(x,term)}</span></div>`;}).join('')}</div>`:"";
  return `<div class="node" id="n${id}"><div class="${rowCls}" onclick="toggle('${id}')"><span class="tog">${tog}</span>${titleHtml}</div>${_qh}${childHtml}</div>`;"""

for p in ALL:
    name = os.path.basename(p)
    if name in SIGS: continue
    src = open(p, encoding='utf-8').read()
    if '_qh' in src:
        print(f'  skip (done): {name}'); continue
    src = s(src, STD_OLD, STD_NEW, f'{name}:title')
    src = s(src, STD_RET_OLD, STD_RET_NEW, f'{name}:return')
    open(p, 'w', encoding='utf-8').write(src)
    print(f'  OK   {name}')

# -- Variant 2: mapas_const.html --
p = BASE + 'mapas_const.html'; src = open(p, encoding='utf-8').read()
if '_qh' in src:
    print('  skip (done): mapas_const.html')
else:
    src = s(src, '  const title = node.t || \'\';',
                 '  const title = node.t || \'\';\n  const _q = _qSplit(title);', 'const:q')
    src = s(src, '<span class="node-text">${hl(title,q)}</span>',
                 '<span class="node-text">${hl(_q?_q.head:title,q)}</span>', 'const:text')
    src = s(src, """    </div>
    <div id="${id}" style="display:${isOpen?'block':'none'}">`;""",
"""    </div>
    ${_q?`<div class="qblock">${_q.qs.map(function(x){return `<div class="qline"><span class="qm">?</span><span>${hl(x,q)}</span></div>`;}).join('')}</div>`:''}
    <div id="${id}" style="display:${isOpen?'block':'none'}">`;""", 'const:block')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   mapas_const.html')

# -- Variant 3: direito_civil_mapas_v4.html (DOM) --
DOM_APPEND = """    var _q=_qSplit(RAWVAR);
    if(_q){
      var _tx=content.querySelector('.node-text');
      if(_tx)_tx.textContent=_q.head;
      var _qb=document.createElement('div');
      _qb.className='qblock';
      _q.qs.forEach(function(x){
        var l=document.createElement('div'); l.className='qline';
        var m=document.createElement('span'); m.className='qm'; m.textContent='?';
        var t=document.createElement('span'); t.textContent=x;
        l.appendChild(m); l.appendChild(t); _qb.appendChild(l);
      });
      wrapper.appendChild(_qb);
    }
"""

p = BASE + 'direito_civil_mapas_v4.html'; src = open(p, encoding='utf-8').read()
if '_qb' in src:
    print('  skip (done): direito_civil_mapas_v4.html')
else:
    src = s(src, """    row.appendChild(toggle);
    row.appendChild(content);
    wrapper.appendChild(row);""",
"""    row.appendChild(toggle);
    row.appendChild(content);
    wrapper.appendChild(row);
""" + DOM_APPEND.replace('RAWVAR', 'rawTitle'), 'civil:block')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   direito_civil_mapas_v4.html')

# -- Variant 4: mapas_admin.html (DOM) --
p = BASE + 'mapas_admin.html'; src = open(p, encoding='utf-8').read()
if '_qb' in src:
    print('  skip (done): mapas_admin.html')
else:
    src = s(src, """    row.appendChild(indent);
    row.appendChild(toggle);
    row.appendChild(textEl);
    wrapper.appendChild(row);""",
"""    row.appendChild(indent);
    row.appendChild(toggle);
    row.appendChild(textEl);
    wrapper.appendChild(row);
""" + DOM_APPEND.replace('RAWVAR', 'node.text').replace("content.querySelector('.node-text')", 'textEl'), 'admin:block')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   mapas_admin.html')

# -- Variant 5: mapas_dtrabalho.html (string buildTree) --
p = BASE + 'mapas_dtrabalho.html'; src = open(p, encoding='utf-8').read()
if '_qh' in src:
    print('  skip (done): mapas_dtrabalho.html')
else:
    src = s(src, """  let inner = hasChildren ? `<span class="toggle">&#9654;</span>` : `<span class="no-toggle">&#8226;</span>`;
  inner += tags + `<span class="node-label">${esc}</span>`;""",
"""  const _q = _qSplit(label);
  const _qh = _q ? `<div class="qblock">${_q.qs.map(function(x){return `<div class="qline"><span class="qm">?</span><span>${escapeHtml(x)}</span></div>`;}).join('')}</div>` : '';
  let inner = hasChildren ? `<span class="toggle">&#9654;</span>` : `<span class="no-toggle">&#8226;</span>`;
  inner += tags + `<span class="node-label">${_q?escapeHtml(_q.head):esc}</span>`;""", 'dtr:title')
    src = s(src, """    <div class="node-header">${inner}</div>
    ${childrenHtml}""",
"""    <div class="node-header">${inner}</div>
    ${_qh}
    ${childrenHtml}""", 'dtr:block')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   mapas_dtrabalho.html')

print('MISSES:', miss if miss else 'none')
