import hashlib
from conftest import CONTRACT

SOURCES=['https://results.example/events/7','https://observer.example/archive/7']
def mocks(vm):
 vm.strict_mocks=True;vm.check_pickling=True
 vm.mock_web(r'results\.example',{'status':200,'body':'Final certified outcome: NORTH. Event 7 closed.'})
 vm.mock_web(r'observer\.example',{'status':200,'body':'Independent archive confirms NORTH for event 7.'})
 vm.mock_llm(r'.*Resolve the event.*','{"outcome":"NORTH","fact":"Both final records agree."}')
 vm.mock_llm(r'.*Independently decide.*','{"valid":true}')
def test_commit_reveal_and_permissionless_finalization(direct_vm,direct_deploy):
 direct_vm.warp('2030-01-01T00:00:00+00:00');c=direct_deploy(CONTRACT);mocks(direct_vm)
 c.create_market(' m-7 ','Which region wins?',['NORTH','SOUTH'],SOURCES,1893459600,1893463200)
 salt='exportable-secret';digest=hashlib.sha256(('NORTH|'+salt).encode()).hexdigest();c.commit_forecast('M-7',digest)
 direct_vm.warp('2030-01-01T01:30:00+00:00');c.reveal_forecast('M-7','north',salt)
 direct_vm.warp('2030-01-01T02:01:00+00:00');c.finalize('M-7');state=c.get_market('M-7')
 assert state['state']=='FINAL' and state['outcome']=='NORTH' and len(state['digests'])==2
def test_replay_bad_reveal_and_same_host_sources_rejected(direct_vm,direct_deploy):
 direct_vm.warp('2030-01-01T00:00:00+00:00');c=direct_deploy(CONTRACT)
 c.create_market('A','Question?',['YES','NO'],SOURCES,1893459600,1893463200)
 with direct_vm.expect_revert('duplicate market'):c.create_market(' a ','Question?',['YES','NO'],SOURCES,1893459600,1893463200)
 with direct_vm.expect_revert('independent hosts'):c.create_market('B','Question?',['YES','NO'],[SOURCES[0],SOURCES[0]],1893459600,1893463200)
 c.commit_forecast('A',hashlib.sha256(b'YES|right').hexdigest());direct_vm.warp('2030-01-01T01:30:00+00:00')
 with direct_vm.expect_revert('does not match'):c.reveal_forecast('A','YES','wrong')
def test_forged_digest_is_rejected(direct_vm,direct_deploy):
 direct_vm.warp('2030-01-01T00:00:00+00:00');c=direct_deploy(CONTRACT);mocks(direct_vm);c.create_market('X','Question?',['NORTH','SOUTH'],SOURCES,1893459600,1893463200);result=c._resolve(c.markets['X']);assert direct_vm.run_validator(leader_result=result) is True
 forged=dict(result);forged['digests']=list(reversed(result['digests']));assert direct_vm.run_validator(leader_result=forged) is False
