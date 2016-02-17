cp -r src/ ~/pox/pox


cd src/
x-terminal-emulator -e sudo mn --custom topology.py --topo custopo --controller remote &

cd ~/pox/pox/ass\ 2

##run controller on terminal
../../pox.py log.level --DEBUG ass\ 2.controller 




