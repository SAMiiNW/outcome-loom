# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import hashlib, json
from datetime import datetime, timezone

def text(v,n=900): return str(v).strip()[:n]
def ident(v):
 k=text(v,72).upper()
 if not k: raise gl.vm.UserError('[EXPECTED] market id required')
 return k
def source(v):
 s=text(v,500); rest=s[8:] if s.startswith('https://') else ''; host=rest.split('/')[0].lower(); path=rest[len(host):]
 if not host or '.' not in host or '@' in host or not path.startswith('/'): raise gl.vm.UserError('[EXPECTED] valid HTTPS source')
 return s,host
def obj(v):
 if isinstance(v,dict): return v
 s=str(v); a=s.find('{'); b=s.rfind('}')
 if a<0 or b<=a: raise gl.vm.UserError('[LLM_ERROR] invalid JSON')
 return json.loads(s[a:b+1])
def now(): return int(datetime.now(timezone.utc).timestamp())

@allow_storage
@dataclass
class Market:
 owner:Address; question:str; options:str; sources:str; commit_end:u256; reveal_end:u256; state:str; outcome:str; digests:str

class OutcomeLoom(gl.Contract):
 markets:TreeMap[str,Market]; commitments:TreeMap[str,str]; reveals:TreeMap[str,str]; participants:DynArray[str]
 def __init__(self): pass
 def _market(self,i):
  k=ident(i)
  if k not in self.markets: raise gl.vm.UserError('[EXPECTED] market not found')
  return k,self.markets[k]
 def _key(self,k): return k+'|'+gl.message.sender_address.as_hex.lower()
 @gl.public.write
 def create_market(self,i:str,question:str,options:list[str],sources:list[str],commit_end:u256,reveal_end:u256)->None:
  k=ident(i)
  if k in self.markets: raise gl.vm.UserError('[EXPECTED] duplicate market id')
  opts=sorted(set(text(x,60).upper() for x in options if text(x,60)))
  parsed=[source(x) for x in sources]
  if len(opts)<2 or len(opts)>8 or len(parsed)!=2 or parsed[0][1]==parsed[1][1]: raise gl.vm.UserError('[EXPECTED] options and two independent hosts required')
  if int(commit_end)<=now() or int(reveal_end)<=int(commit_end): raise gl.vm.UserError('[EXPECTED] invalid market clock')
  self.markets[k]=Market(gl.message.sender_address,text(question),json.dumps(opts),json.dumps([x[0] for x in parsed]),commit_end,reveal_end,'COMMIT','','[]')
 @gl.public.write
 def commit_forecast(self,i:str,commitment:str)->None:
  k,m=self._market(i); key=self._key(k); digest=text(commitment,64).lower()
  if m.state!='COMMIT' or now()>int(m.commit_end): raise gl.vm.UserError('[EXPECTED] commit phase closed')
  if len(digest)!=64 or key in self.commitments: raise gl.vm.UserError('[EXPECTED] valid unique commitment required')
  self.commitments[key]=digest; self.participants.append(key)
 @gl.public.write
 def reveal_forecast(self,i:str,choice:str,salt:str)->None:
  k,m=self._market(i); key=self._key(k); pick=text(choice,60).upper()
  if now()<=int(m.commit_end) or now()>int(m.reveal_end): raise gl.vm.UserError('[EXPECTED] reveal window closed')
  if key not in self.commitments or key in self.reveals or pick not in json.loads(m.options): raise gl.vm.UserError('[EXPECTED] reveal unavailable')
  digest=hashlib.sha256((pick+'|'+text(salt,160)).encode()).hexdigest()
  if digest!=self.commitments[key]: raise gl.vm.UserError('[EXPECTED] reveal does not match commitment')
  self.reveals[key]=pick; m.state='REVEAL'
 def _resolve(self,m):
  urls=json.loads(m.sources); options=json.loads(m.options)
  def leader():
   bodies=[]; digests=[]
   for ix,url in enumerate(urls):
    raw=gl.nondet.web.get(url).body[:14000]; data=raw if isinstance(raw,bytes) else str(raw).encode(); digests.append(hashlib.sha256(data).hexdigest()); bodies.append({'index':ix,'body':data.decode(errors='replace')})
   q='Resolve the event using only the records. JSON only {"outcome":"one listed option or INSUFFICIENT","fact":"under 240 chars"}. QUESTION:'+m.question+' OPTIONS:'+json.dumps(options)+' RECORDS:'+json.dumps(bodies)
   x=obj(gl.nondet.exec_prompt(q,response_format='json')); outcome=text(x.get('outcome'),60).upper()
   if outcome not in options: outcome='INSUFFICIENT'
   return {'outcome':outcome,'fact':text(x.get('fact'),240),'digests':digests}
  def validator(result):
   if not isinstance(result,gl.vm.Return): return False
   try:
    given=result.calldata; bodies=[]; digests=[]
    for ix,url in enumerate(urls):
     raw=gl.nondet.web.get(url).body[:14000]; data=raw if isinstance(raw,bytes) else str(raw).encode(); digests.append(hashlib.sha256(data).hexdigest()); bodies.append({'index':ix,'body':data.decode(errors='replace')})
    if given['digests']!=digests or given['outcome'] not in options+['INSUFFICIENT']: return False
    q='Independently decide whether the proposed outcome is fully supported by both records. JSON only {"valid":true}. QUESTION:'+m.question+' PROPOSED:'+given['outcome']+' RECORDS:'+json.dumps(bodies)
    return bool(obj(gl.nondet.exec_prompt(q,response_format='json')).get('valid',False))
   except: return False
  return gl.vm.run_nondet_unsafe(leader,validator)
 @gl.public.write
 def finalize(self,i:str)->None:
  k,m=self._market(i)
  if now()<=int(m.reveal_end) or m.state not in ('COMMIT','REVEAL'): raise gl.vm.UserError('[EXPECTED] resolution unavailable')
  result=self._resolve(m); m.outcome=result['outcome']; m.digests=json.dumps(result['digests']); m.state='FINAL'
 @gl.public.view
 def get_market(self,i:str)->dict:
  k,m=self._market(i); return {'id':k,'owner':m.owner.as_hex,'question':m.question,'options':json.loads(m.options),'sources':json.loads(m.sources),'commitEnd':int(m.commit_end),'revealEnd':int(m.reveal_end),'state':m.state,'outcome':m.outcome,'digests':json.loads(m.digests)}
 @gl.public.view
 def get_my_forecast(self,i:str,participant:Address)->dict:
  k,_=self._market(i); key=k+'|'+participant.as_hex.lower(); return {'committed':key in self.commitments,'revealed':self.reveals[key] if key in self.reveals else ''}
