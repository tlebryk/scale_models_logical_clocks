Setup for VM 1:
export VM_ID=1
export PORT=5001
export PEERS='{"2":5002,"3":5003}'
python run.py


Setup for VM 2:
export VM_ID=2
export PORT=5002
export PEERS='{"1":5001,"3":5003}'
python run.py


Setup for VM 3:
export VM_ID=3
export PORT=5003
export PEERS='{"1":5001,"2":5002}'
python run.py
