from routerNode import RouterNode
from datetime import datetime
import socket
import sys
import time
from random import randint
import ast

print("Access http://localhost:9000")
routerNode = RouterNode('127.0.0.1', 9000, 'RouterNode: '+str(100))
routerNode.start()
while True:
    if len(routerNode.arrayOfConnected) == 0:
        time.sleep(1)
        continue
    else:
        print('\nValidators in the network:')
        for i in routerNode.arrayOfConnected:
            print(i)
        time.sleep(5)
        routerNode.check_timestamps()
