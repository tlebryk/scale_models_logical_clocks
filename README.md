
will make this readme prettier lol

cd into src

Setup for VM 1:
export VM_ID=1
export PORT=5001
export PEERS='{}'
python run.py


Setup for VM 2:
export VM_ID=2
export PORT=5002
export PEERS='{"1": 5001}'
python run.py

Setup for VM 3:
export VM_ID=3
export PORT=5003
export PEERS='{"1": 5001, "2": 5002}'
python run.py

