##Instructions

###First copy ass 2 folder to pox folder
```shell
cp ass\ 2 ~/pox/pox
```


###Run Controller in one terminal

```shell
cd ~/pox/pox/ass\ 2
../../pox.py log.level --DEBUG ass\ 2.controller ##run controller on controller

```

### Open a new terminal and run 
```shell
sudo mn --custom topology.py --topo custopo --controller remote
```
