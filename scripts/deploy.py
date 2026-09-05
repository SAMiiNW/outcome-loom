import json,re,subprocess
from pathlib import Path
from genlayer_py import create_client,create_account
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionStatus
ROOT=Path(__file__).parents[1]
ENV=(ROOT.parents[3]/'accounts.env').read_text()
def secret():return re.search(r'^ACCOUNT_1_GENLAYER_PRIVATE_KEY\s*=\s*"?([^"\r\n]+)',ENV,re.M).group(1).strip()
def address(value):
 if isinstance(value,dict):
  for k in ('contract_address','contractAddress'):
   if value.get(k):return value[k]
  if value.get('recipient') and str(value.get('tx_execution_result','')) in ('1','6'):return value['recipient']
  for nested in value.values():
   found=address(nested)
   if found:return found
 if isinstance(value,list):
  for nested in value:
   found=address(nested)
   if found:return found
def main():
 account=create_account(account_private_key=secret())
 client=create_client(chain=studionet,account=account)
 code=(ROOT/"contract/outcome_loom.py").read_text()
 tx=client.deploy_contract(code=code,args=[])
 print('deploy',tx,flush=True)
 receipt=client.wait_for_transaction_receipt(transaction_hash=tx,status=TransactionStatus.ACCEPTED,retries=120,interval=10000)
 info=client.get_transaction(transaction_hash=tx)
 contract=address(receipt)
 if not contract or info.get('status_name')!='ACCEPTED' or not any(r.get('execution_result')=='SUCCESS' for r in info.get('consensus_data',{}).get('leader_receipt',[])):
  raise RuntimeError({'address':contract,'status':info.get('status_name'),'execution':info.get('tx_execution_result_name')})
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 out={'contract':contract,'deploymentTx':tx,'network':'StudioNet','deployer':account.address,'sourceCommit':commit,'evidenceCommit':commit,'evidenceBase':f'https://raw.githubusercontent.com/SAMiiNW/outcome-loom/{commit}/evidence/','mirrorBase':f'https://cdn.jsdelivr.net/gh/SAMiiNW/outcome-loom@{commit}/evidence/','receiptStatus':info.get('status_name'),'execution':info.get('tx_execution_result_name') or 'CONTRACT_ADDRESS_RETURNED'}
 (ROOT/"evidence/deployment.json").parent.mkdir(parents=True,exist_ok=True)
 (ROOT/"evidence/deployment.json").write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
