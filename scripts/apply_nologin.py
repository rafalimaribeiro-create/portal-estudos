import os, sys, re

BASE = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else './'
report = []

def sub(src, old, new, label, fname, count=1):
    """Replace old->new; record miss if absent."""
    if old not in src:
        report.append(f'  MISS [{label}] {fname}')
        return src, False
    return src.replace(old, new, count), True

# ══════════════════════════════════════════════════════════════════
# PART 1 — MAP FILES (13 standard)
# ══════════════════════════════════════════════════════════════════

LS_HELPERS = """var _u=null,_m={},_sid=null,_sel=null;
var _LK='_marks_'+_mid;
function _lsSave(){try{localStorage.setItem(_LK,JSON.stringify(_m));}catch(e){}}
function _lsLoad(){try{var v=JSON.parse(localStorage.getItem(_LK)||'{}');if(v&&typeof v==='object')_m=v;}catch(e){}}"""

AUTH_OLD = """window.addEventListener('DOMContentLoaded',function(){
  _sb.auth.getSession().then(function(r){
    if(r.data&&r.data.session&&r.data.session.user){
      _u=r.data.session.user;
      _lm().then(_aa);
    }
  });
});"""

AUTH_NEW = """window.addEventListener('DOMContentLoaded',function(){
  var go=function(){
    _lm().then(_aa);
    if(!_u){var lo=document.querySelector('button[onclick="_doLogout()"]');if(lo)lo.style.display='none';}
  };
  try{
    _sb.auth.getSession().then(function(r){
      if(r.data&&r.data.session&&r.data.session.user)_u=r.data.session.user;
      go();
    }).catch(go);
  }catch(e){go();}
});"""

HL_OLD = """async function _hl(color){
  if(!_sid)return;if(!_u){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].hl=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_sw_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var sw=document.getElementById('_sw_'+color[0]);if(sw)sw.classList.add('_on');await _sb.from('highlights').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,color:color},{onConflict:'user_id,map_id,node_id'});}
  else await _sb.from('highlights').delete().eq('user_id',_uid()).eq('map_id',_mid).eq('node_id',_sid);
}"""

HL_NEW = """async function _hl(color){
  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].hl=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_sw_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var sw=document.getElementById('_sw_'+color[0]);if(sw)sw.classList.add('_on');}
  _lsSave();
  if(!_u)return;
  if(color)await _sb.from('highlights').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,color:color},{onConflict:'user_id,map_id,node_id'});
  else await _sb.from('highlights').delete().eq('user_id',_uid()).eq('map_id',_mid).eq('node_id',_sid);
}"""

FC_OLD = """  if(!_sid)return;if(!_u){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].fc=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_fc_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var fcb=document.querySelector('._sw[onclick*="'+color+'"]');if(fcb)fcb.classList.add('_on');}
  var sz=(_m[_sid]&&_m[_sid].fs)||null;
  if(color||sz)await"""

FC_NEW = """  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].fc=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_fc_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var fcb=document.querySelector('._sw[onclick*="'+color+'"]');if(fcb)fcb.classList.add('_on');}
  var sz=(_m[_sid]&&_m[_sid].fs)||null;
  _lsSave();
  if(!_u)return;
  if(color||sz)await"""

FS_OLD = """  if(!_sid)return;if(!_u){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};
  var t=_sel?_txt(_sel):null;"""
FS_NEW = """  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};
  var t=_sel?_txt(_sel):null;"""

FS_TAIL_OLD = """  var fc=(_m[_sid]&&_m[_sid].fc)||null;
  if(nv||fc)await"""
FS_TAIL_NEW = """  var fc=(_m[_sid]&&_m[_sid].fc)||null;
  _lsSave();
  if(!_u)return;
  if(nv||fc)await"""

FL_OLD = """  if(!_sid)return;if(!_u){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].fl=flag;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('#_f0,#_f1,#_f2').forEach(function(b){b.classList.remove('_on');});
  if(flag){var fi={hard:'_f0',review:'_f1',done:'_f2'};var fb=document.getElementById(fi[flag]);if(fb)fb.classList.add('_on');await _sb.from('node_flags').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,flag:flag},{onConflict:'user_id,map_id,node_id'});}
  else await _sb.from('node_flags').delete().eq('user_id',_uid()).eq('map_id',_mid).eq('node_id',_sid);"""

FL_NEW = """  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].fl=flag;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('#_f0,#_f1,#_f2').forEach(function(b){b.classList.remove('_on');});
  if(flag){var fi={hard:'_f0',review:'_f1',done:'_f2'};var fb=document.getElementById(fi[flag]);if(fb)fb.classList.add('_on');}
  _lsSave();
  if(!_u)return;
  if(flag)await _sb.from('node_flags').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,flag:flag},{onConflict:'user_id,map_id,node_id'});
  else await _sb.from('node_flags').delete().eq('user_id',_uid()).eq('map_id',_mid).eq('node_id',_sid);"""

SN_OLD = """  if(!_sid||!_u)return _cn();
  var content=document.getElementById('_npta').value;
  if(!_m[_sid])_m[_sid]={};_m[_sid].nt=content;
  if(_sel)_am(_sel,_sid);
  if(content.trim())await"""
SN_NEW = """  if(!_sid)return _cn();
  var content=document.getElementById('_npta').value;
  if(!_m[_sid])_m[_sid]={};_m[_sid].nt=content;
  if(_sel)_am(_sel,_sid);
  _lsSave();
  if(!_u){_cn();return;}
  if(content.trim())await"""

LM_OLD = """async function _lm(){
  if(!_u)return;"""
LM_NEW = """async function _lm(){
  if(!_u){_lsLoad();return;}"""

TRK_INIT_OLD = """  _sb.auth.getSession().then(function(r){
    if(r.data&&r.data.session&&r.data.session.user){
      _TRK.user = r.data.session.user;
      _trkLoad();
    } else {
      _trkRender();
    }
  });"""
TRK_INIT_NEW = """  var go=function(){_trkLoadLS();_trkRender();};
  try{
    _sb.auth.getSession().then(function(r){
      if(r.data&&r.data.session&&r.data.session.user){
        _TRK.user = r.data.session.user;
        _trkLoad();
      } else { go(); }
    }).catch(go);
  }catch(e){go();}"""

TRK_LS_FN = """function _trkLoadLS(){
  try{Object.keys(localStorage).filter(function(k){return k.indexOf('_pgprog_'+_TRK.mapId+'_')===0;}).forEach(function(k){
    try{var v=JSON.parse(localStorage.getItem(k));if(v&&v.done)_TRK.done[k.slice(8)]=true;}catch(e){}
  });}catch(e){}
}
async function _trkLoad(){"""

TRK_TOGGLE_OLD = """async function _trkToggle(chapterId, done, chk){
  if(!_TRK.user){
    // Try to recover session
    try {
      const r = await _sb.auth.getSession();
      if(r.data && r.data.session && r.data.session.user){
        _TRK.user = r.data.session.user;
      } else {
        console.warn('No session found, cannot save tracker');
        return;
      }
    } catch(e) { console.error('getSession error:', e); return; }
  }
  var now = done ? new Date().toISOString() : null;
  if(done) _TRK.done[chapterId] = true;
  else delete _TRK.done[chapterId];
  _trkRender();
  try{
    await _sb.from('progress').upsert({"""

TRK_TOGGLE_NEW = """async function _trkToggle(chapterId, done, chk){
  var now = done ? new Date().toISOString() : null;
  if(done) _TRK.done[chapterId] = true;
  else delete _TRK.done[chapterId];
  _trkRender();
  try{ localStorage.setItem('_pgprog_'+chapterId, JSON.stringify({done:done, date:now})); }catch(_){}
  if(!_TRK.user){
    try {
      const r = await _sb.auth.getSession();
      if(r.data && r.data.session && r.data.session.user) _TRK.user = r.data.session.user;
      else return;
    } catch(e) { return; }
  }
  try{
    await _sb.from('progress').upsert({"""

STANDARD = ['mapas_ambiental.html','mapas_const.html','mapas_dcoletivo.html',
 'mapas_dconsumidor.html','mapas_deleitoral.html','mapas_dempresarial.html',
 'mapas_dfinanceiro.html','mapas_dprevidenciario.html','mapas_dtributario.html',
 'mapas_durbanistico.html','mapas_pcivil.html','mapas_ptrabalho.html',
 'direito_civil_mapas_v4.html']

PATCHES = [
 ('var _u=null,_m={},_sid=null,_sel=null;', LS_HELPERS, 'ls-helpers'),
 (AUTH_OLD, AUTH_NEW, 'auth-init'),
 (LM_OLD, LM_NEW, 'lm-guard'),
 (HL_OLD, HL_NEW, 'hl'),
 (FC_OLD, FC_NEW, 'fc'),
 (FS_OLD, FS_NEW, 'fs-head'),
 (FS_TAIL_OLD, FS_TAIL_NEW, 'fs-tail'),
 (FL_OLD, FL_NEW, 'fl'),
 (SN_OLD, SN_NEW, 'sn'),
 (TRK_INIT_OLD, TRK_INIT_NEW, 'trk-init'),
 ('async function _trkLoad(){', TRK_LS_FN, 'trk-ls-fn'),
 (TRK_TOGGLE_OLD, TRK_TOGGLE_NEW, 'trk-toggle'),
]

changed_files = []
print('-- MAP FILES --')
for fname in STANDARD:
    p = BASE + fname
    src = open(p, encoding='utf-8').read()
    if '_lsSave' in src:
        print(f'  skip (done): {fname}'); continue
    ok_all = True
    for old, new, label in PATCHES:
        src, ok = sub(src, old, new, label, fname)
        ok_all = ok_all and ok
    open(p, 'w', encoding='utf-8').write(src)
    changed_files.append(fname)
    print(f'  {"OK  " if ok_all else "PART"} {fname}')

for line in report: print(line)
print()
print('CHANGED:', len(changed_files))

# ══════════════════════════════════════════════════════════════════
# PART 2 — admin + dtrabalho variants, index.html gate, jurisprudence
# ══════════════════════════════════════════════════════════════════
import json

miss2 = []
def s2(s, o, n, lbl):
    global miss2
    if o not in s:
        miss2.append(lbl); return s
    return s.replace(o, n, 1)

# ----------------- mapas_admin.html -----------------
p = BASE + 'mapas_admin.html'; src = open(p, encoding='utf-8').read()
if '_lsSave' in src:
    print('  skip (done): mapas_admin.html')
else:
    src = s2(src, "var _mid='admin',_m={},_sid=null,_sel=null;",
"""var _mid='admin',_m={},_sid=null,_sel=null;
var _LK='_marks_'+_mid;
function _lsSave(){try{localStorage.setItem(_LK,JSON.stringify(_m));}catch(e){}}
function _lsLoad(){try{var v=JSON.parse(localStorage.getItem(_LK)||'{}');if(v&&typeof v==='object')_m=v;}catch(e){}}""", 'admin:ls')

    src = s2(src, """async function _loadAnnotations(){
  if(!_uid())return;""",
"""async function _loadAnnotations(){
  if(!_uid()){_lsLoad();document.querySelectorAll('.node-row[data-mnid]').forEach(function(row){_am(row,row.getAttribute('data-mnid'));});return;}""", 'admin:load')

    src = s2(src, """    } else {
      _trkRender();
    }
  });
});

async function _trkLoad(){""",
"""    } else {
      _trkLoadLS();_trkRender();_loadAnnotations();
      var lo=document.querySelector('button[onclick="_doLogout()"]');if(lo)lo.style.display='none';
    }
  });
});

function _trkLoadLS(){
  try{Object.keys(localStorage).filter(function(k){return k.indexOf('_pgprog_admin_')===0;}).forEach(function(k){
    try{var v=JSON.parse(localStorage.getItem(k));if(v&&v.done)_TRK.done[k.slice(8)]=true;}catch(e){}
  });}catch(e){}
}
async function _trkLoad(){""", 'admin:init')

    src = s2(src, """async function _trkToggle(chapterId, done){
  if(!_TRK.user) { alert('Faça login para usar o tracker'); return; }
  if(done) _TRK.done[chapterId] = true;
  else delete _TRK.done[chapterId];
  _trkRender();
  try{""",
"""async function _trkToggle(chapterId, done){
  if(done) _TRK.done[chapterId] = true;
  else delete _TRK.done[chapterId];
  _trkRender();
  try{ localStorage.setItem('_pgprog_'+chapterId, JSON.stringify({done:done, date:done?new Date().toISOString():null})); }catch(_){}
  if(!_TRK.user) return;
  try{""", 'admin:trk')

    src = s2(src, """  if(!_sid)return;if(!_uid()){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].hl=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_sw_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var sw=document.getElementById('_sw_'+color[0]);if(sw)sw.classList.add('_on');await _sb.from('highlights').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,color:color},{onConflict:'user_id,map_id,node_id'});}
  else await""",
"""  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].hl=color;
  if(_sel)_am(_sel,_sid);
  document.querySelectorAll('._sw[id^="_sw_"]').forEach(function(s){s.classList.remove('_on');});
  if(color){var sw=document.getElementById('_sw_'+color[0]);if(sw)sw.classList.add('_on');}
  _lsSave();
  if(!_uid())return;
  if(color)await _sb.from('highlights').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,color:color},{onConflict:'user_id,map_id,node_id'});
  else await""", 'admin:hl')

    src = s2(src, """  if(!_sid)return;if(!_uid()){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].fc=color;""",
"""  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].fc=color;""", 'admin:fc-head')
    src = s2(src, """  var sz=(_m[_sid]&&_m[_sid].fs)||null;
  if(color||sz)await""",
"""  var sz=(_m[_sid]&&_m[_sid].fs)||null;
  _lsSave();
  if(!_uid())return;
  if(color||sz)await""", 'admin:fc-tail')

    src = s2(src, """  if(!_sid)return;if(!_uid()){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};
  var t=_sel?_txt(_sel):null;""",
"""  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};
  var t=_sel?_txt(_sel):null;""", 'admin:fs-head')
    src = s2(src, """  var fc=(_m[_sid]&&_m[_sid].fc)||null;
  if(nv||fc)await""",
"""  var fc=(_m[_sid]&&_m[_sid].fc)||null;
  _lsSave();
  if(!_uid())return;
  if(nv||fc)await""", 'admin:fs-tail')

    src = s2(src, """  if(!_sid)return;if(!_uid()){alert('Faça login para usar marcações');return;}
  if(!_m[_sid])_m[_sid]={};_m[_sid].fl=flag;if(_sel)_am(_sel,_sid);
  document.querySelectorAll('#_f0,#_f1,#_f2').forEach(function(b){b.classList.remove('_on');});
  if(flag){var fi={hard:'_f0',review:'_f1',done:'_f2'};var fb=document.getElementById(fi[flag]);if(fb)fb.classList.add('_on');await _sb.from('node_flags').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,flag:flag},{onConflict:'user_id,map_id,node_id'});}
  else await""",
"""  if(!_sid)return;
  if(!_m[_sid])_m[_sid]={};_m[_sid].fl=flag;if(_sel)_am(_sel,_sid);
  document.querySelectorAll('#_f0,#_f1,#_f2').forEach(function(b){b.classList.remove('_on');});
  if(flag){var fi={hard:'_f0',review:'_f1',done:'_f2'};var fb=document.getElementById(fi[flag]);if(fb)fb.classList.add('_on');}
  _lsSave();
  if(!_uid())return;
  if(flag)await _sb.from('node_flags').upsert({user_id:_uid(),map_id:_mid,node_id:_sid,flag:flag},{onConflict:'user_id,map_id,node_id'});
  else await""", 'admin:fl')

    src = s2(src, """  if(!_sid||!_uid())return _cn();
  var content=document.getElementById('_npta').value;
  if(!_m[_sid])_m[_sid]={};_m[_sid].nt=content;
  if(_sel)_am(_sel,_sid);
  if(content.trim())await""",
"""  if(!_sid)return _cn();
  var content=document.getElementById('_npta').value;
  if(!_m[_sid])_m[_sid]={};_m[_sid].nt=content;
  if(_sel)_am(_sel,_sid);
  _lsSave();
  if(!_uid()){_cn();return;}
  if(content.trim())await""", 'admin:sn')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   mapas_admin.html')

# ----------------- mapas_dtrabalho.html -----------------
p = BASE + 'mapas_dtrabalho.html'; src = open(p, encoding='utf-8').read()
if '_hlLS' in src:
    print('  skip (done): mapas_dtrabalho.html')
else:
    src = s2(src, 'window.addEventListener("DOMContentLoaded",function(){_sb.auth.getSession().then(function(r){if(r.data&&r.data.session&&r.data.session.user){_u=r.data.session.user;_loadHL();_trkLoad();}else{_trkRender();}});});',
'function _hlLS(){try{var v=JSON.parse(localStorage.getItem("_marks_"+_mid)||"{}");if(v&&typeof v==="object")_hlData=v;}catch(e){}}\nfunction _hlLSsave(){try{localStorage.setItem("_marks_"+_mid,JSON.stringify(_hlData));}catch(e){}}\nfunction _trkLoadLS(){try{Object.keys(localStorage).filter(function(k){return k.indexOf("_pgprog_dtrabalho_")===0;}).forEach(function(k){try{var v=JSON.parse(localStorage.getItem(k));if(v&&v.done)_TRK.done[k.slice(8)]=true;}catch(e){}});}catch(e){}}\nwindow.addEventListener("DOMContentLoaded",function(){var go=function(){_hlLS();_applyAllHL();_trkLoadLS();_trkRender();};try{_sb.auth.getSession().then(function(r){if(r.data&&r.data.session&&r.data.session.user){_u=r.data.session.user;_loadHL();_trkLoad();}else{go();}}).catch(go);}catch(e){go();}});', 'dtr:init')

    src = s2(src, 'async function _saveHL(nid,color){if(!_u){var r=await _sb.auth.getSession();if(r.data&&r.data.session&&r.data.session.user)_u=r.data.session.user;else return;}try{',
'async function _saveHL(nid,color){if(color)_hlData[nid]=color;else delete _hlData[nid];_hlLSsave();if(!_u){var r=await _sb.auth.getSession();if(r.data&&r.data.session&&r.data.session.user)_u=r.data.session.user;else return;}try{', 'dtr:savehl')

    src = s2(src, 'async function _trkToggle_real(cid,done){if(!_u){await _ensureAuth();if(!_u)return;}if(done)_TRK.done[cid]=true;else delete _TRK.done[cid];_trkRender();var _dat=done?new Date().toISOString():null;try{',
'async function _trkToggle_real(cid,done){if(done)_TRK.done[cid]=true;else delete _TRK.done[cid];_trkRender();var _dat=done?new Date().toISOString():null;try{localStorage.setItem("_pgprog_"+cid,JSON.stringify({done:done,date:_dat}));}catch(_){}if(!_u){await _ensureAuth();if(!_u)return;}try{', 'dtr:trk')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   mapas_dtrabalho.html')

# ----------------- index.html — remove the login gate -----------------
p = BASE + 'index.html'; src = open(p, encoding='utf-8').read()
if '_enterLocalMode' in src:
    print('  skip (done): index.html')
else:
    src = s2(src, '''    <span class="tb-user" id="user-email-display"></span>
    <button class="tb-btn" onclick="doLogout()">Sair</button>''',
'''    <span class="tb-user" id="user-email-display"></span>
    <button class="tb-btn" id="auth-btn" onclick="doLogout()">Sair</button>''', 'idx:topbar-id')

    src = s2(src, '''    <div class="auth-msg" id="auth-msg"></div>''',
'''    <div class="auth-msg" id="auth-msg"></div>
    <div style="margin-top:18px;padding-top:16px;border-top:1px solid var(--border);text-align:center;">
      <button onclick="_skipAuth()" style="background:none;border:none;color:var(--muted);font-size:12px;font-family:'DM Mono',monospace;cursor:pointer;text-decoration:underline;padding:4px;">Continuar sem conta →</button>
      <div style="font-size:11px;color:var(--muted);margin-top:6px;opacity:.7;">seu progresso fica salvo neste navegador</div>
    </div>''', 'idx:auth-skip')

    src = s2(src, '''async function loadProgress(){
  if(!currentUser){ return; }''',
'''async function loadProgress(){
  if(!currentUser){ _loadProgressLS(); return; }''', 'idx:loadProgress')

    src = s2(src, '''window.addEventListener('focus', async ()=>{
  if(!currentUser) return;
  try{''',
'''window.addEventListener('focus', async ()=>{
  try{''', 'idx:focus')

    src = s2(src, """  if(!currentUser){ _lsSaveStatus('Faça login para salvar','err'); return; }""",
"""  if(!currentUser){ _lsSaveStatus('✓ salvo neste navegador','ok'); return; }""", 'idx:leiseca')

    src = s2(src, '''    currentUser=null;
    document.getElementById('auth-screen').style.display='flex';
    document.getElementById('topbar').style.display='none';
    document.getElementById('main').style.display='none';
  }
});''',
'''    currentUser=null;
    _enterLocalMode();
  }
});

// -- LOCAL (no-login) MODE --
function _skipAuth(){ try{localStorage.setItem('_skip_auth','1');}catch(e){} _enterLocalMode(); }
function _showAuth(){ document.getElementById('auth-screen').style.display='flex'; }
async function _enterLocalMode(){
  document.getElementById('auth-screen').style.display='none';
  document.getElementById('topbar').style.display='flex';
  document.getElementById('main').style.display='flex';
  const ud=document.getElementById('user-email-display'); if(ud) ud.textContent='Modo local';
  const ab=document.getElementById('auth-btn'); if(ab){ ab.textContent='Entrar'; ab.setAttribute('onclick','_showAuth()'); }
  if(_pendingTab){
    try{
      const _tabBtn=[...document.querySelectorAll('.tb-tab')].find(b=>(b.getAttribute('onclick')||'').includes("'"+_pendingTab+"'"));
      showView(_pendingTab,_tabBtn||null);
    }catch(_){}
    _pendingTab=null;
  }
  _loadProgressLS();
  try{ loadLeiSeca(); }catch(e){}
  try{ renderTracker(); }catch(e){}
  try{ renderLeiSeca(); }catch(e){}
  try{ renderHomeCards(); }catch(e){}
}''', 'idx:local-mode')

    src = s2(src, """    document.getElementById('user-email-display').textContent=session.user.user_metadata?.name||session.user.email;""",
"""    document.getElementById('user-email-display').textContent=session.user.user_metadata?.name||session.user.email;
    const _ab=document.getElementById('auth-btn'); if(_ab){ _ab.textContent='Sair'; _ab.setAttribute('onclick','doLogout()'); }""", 'idx:restore-logout')

    for o, n in [('<div id="auth-screen">', '<div id="auth-screen" style="display:none">'),
                 ('<div id="topbar" style="display:none">', '<div id="topbar">'),
                 ('<div id="main" style="display:none">', '<div id="main">')]:
        src = s2(src, o, n, 'idx:flip')
    open(p, 'w', encoding='utf-8').write(src); print('  OK   index.html')

# ----------------- jurisprudence: ADI 7.783/PE into mapas_const.html -----------------
p = BASE + 'mapas_const.html'; src = open(p, encoding='utf-8').read()
i = src.find('const ALL_DATA = ')
j = src.find('\n', i)
pre = src[:i + len('const ALL_DATA = ')]
body = src[i + len('const ALL_DATA = '):j]
suf = src[j:]
semi = body.rstrip().endswith(';')
data = json.loads(body.rstrip().rstrip(';'))

JURIS = {
 "t": "⚖ STF — ADI 7.783/PE (Info 1211): flexibilização do princípio do pedido",
 "c": [
  {"t": "Regra geral — efeito repristinatório tácito", "c": [
    {"t": "A lei inconstitucional é nula desde o nascimento e, portanto, nunca produziu efeitos válidos"},
    {"t": "Logo, a lei que ela havia revogado volta a produzir efeitos"}]},
  {"t": "O problema — quando o efeito é indesejado", "c": [
    {"t": "Torna-se indesejado quando a lei anterior revogada padece do mesmo vício de inconstitucionalidade"},
    {"t": "Sairia uma lei inconstitucional e voltaria outra com a mesma mácula, tornando inútil a decisão do STF"}]},
  {"t": "Posição TRADICIONAL do STF", "c": [
    {"t": "O autor da ADI deveria impugnar todo o complexo normativo: a lei atual E as leis anteriores revogadas com o mesmo vício"},
    {"t": "Sob pena de NÃO CONHECIMENTO da ação"}]},
  {"t": "Posição ATUAL — solução mais flexível", "c": [
    {"t": "Mesmo que o autor NÃO impugne as normas anteriores, a Corte pode, DE OFÍCIO, ao delimitar a eficácia de sua decisão, excluir o efeito repristinatório indesejado"},
    {"t": "O STF tem flexibilizado o princípio do pedido para permitir a exclusão do efeito repristinatório quando constatada a incompatibilidade da legislação revogada com a ordem constitucional vigente"}]},
  {"t": "Caso concreto (ADI 7.783/PE)", "c": [
    {"t": "A autora impugnou apenas a lei estadual mais recente, sem formular pedido quanto às leis anteriores revogadas"},
    {"t": "Constatando que as normas anteriores padeciam do mesmo vício, o STF declarou sua inconstitucionalidade de ofício e por arrastamento"},
    {"t": "Evitou-se, assim, a repristinação de leis igualmente incompatíveis com a Constituição"}]}],
 "k": [{"l": "STF", "n": [
   "\"Não obsta a cognição da ação direta a falta de impugnação de ato jurídico revogado pela norma tida como inconstitucional, supostamente padecente do mesmo vício, que se teria por repristinada. Cabe à Corte, ao delimitar a eficácia da sua decisão, se o caso, excluir dos efeitos da decisão declaratória eventual efeito repristinatório quando constatada incompatibilidade com a ordem constitucional.\" (ADI 7.110)",
   "STF. Plenário. ADI 7.783/PE, Rel. Min. Dias Toffoli, julgado em 09/04/2026 (Info 1211)."]}]}

def _find(n, t):
    if n.get('t', '') == t: return n
    for c in n.get('c', []):
        r = _find(c, t)
        if r: return r
    return None

tgt = _find(data['Cap__5_-_Ações_Diretas'], 'Ef. Repristinatório Indesejavel')
if tgt is None:
    print('  MISS jurisprudence target node')
elif any('7.783' in (c.get('t') or '') for c in tgt.get('c', [])):
    print('  skip (done): jurisprudence')
else:
    tgt.setdefault('c', []).append(JURIS)
    open(p, 'w', encoding='utf-8').write(
        pre + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + (';' if semi else '') + suf)
    print('  OK   jurisprudence ADI 7.783/PE -> mapas_const.html')

print('PART2 MISSES:', miss2 if miss2 else 'none')
