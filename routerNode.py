from datetime import datetime
import socket
import sys
import time
from node import Node
from random import randint
import ast

class RouterNode(Node):
    def __init__(self, host, port, id=None, callback=None, max_connections=0):
        
        self.arrayOfConnected = []
        self.dictOfConnected = {}
        
        super(RouterNode, self).__init__(host, port, id, callback, max_connections)
        print("RouterNode: Started")
        
        
    def inbound_node_connected(self, node):
        print("inbound_node_connected: (" + str(self.port) + "): " + str(node.port))

    def inbound_node_disconnected(self, node):
        print("inbound_node_disconnected: (" + str(self.port) + "): " + str(node.port))


    def node_message(self, node, data):
        print("node_message (" + str(self.port) + ") from " + str(node.port) + ": " + str(data))
        
        message = str(data)
        address = (node.host, int(node.port))
        
        if message == 'connect':
            if address not in self.arrayOfConnected:
                self.arrayOfConnected.append(address)
                self.dictOfConnected[address] = int(datetime.timestamp(datetime.now()))
                print("Address: "+str(address)+" connected")
        elif message == 'connectGambler':
            print("Address gambler: "+str(address)+" connected")
        elif message == 'disconnect':
            self.arrayOfConnected.remove(address)
            del self.dictOfConnected[address]
            print("Address: "+str(address)+" disconnected")
        elif message == 'getNodes':
            if len(self.arrayOfConnected)==0:
                strToSend = 'nodes:nothing'
            else:
                strToSend = 'nodes:'+str(self.arrayOfConnected)
            self.send_to_node(node, strToSend)
        elif 'checkValidators:' in message[:16]:
            arrToCheck = ast.literal_eval(message[16:])
            ok = True
            for i in arrToCheck:
                if i not in self.arrayOfConnected:
                    ok = False
                    break
            self.send_to_node(node, 'ok:'+str(ok))
        elif message == 'hi':
            self.dictOfConnected[address] = int(datetime.timestamp(datetime.now()))
            print("Address: "+str(address)+" said hi")
            
            
    def check_timestamps(self):
        for i in self.dictOfConnected.copy():
            if (int(datetime.timestamp(datetime.now())) - self.dictOfConnected[i]) > 300:
                self.arrayOfConnected.remove(i)
                del self.dictOfConnected[i]
                print("Address: "+str(i)+" disconnected because of timestamp")
