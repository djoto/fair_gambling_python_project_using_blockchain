import socket
import sys
import time
from node import Node
from random import randint
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
import binascii
import os
import json
import ast
import math

class GamblerNode(Node):
    
    def __init__(self, host, port, id=None, callback=None, max_connections=0):
        super(GamblerNode, self).__init__(host, port, id, callback, max_connections)
        print("GamblerNode: Started")
        self.arrNodes = []
        self.blockchain = {}
        self.tempArrOfHash = []
        self.blockchainFileName = ''
        self.sentRequest = 0
        
        
    #def outbound_node_connected(self, node):
        #print("outbound_node_connected (" + str(self.port) + "): " + str(node.port))
        
        
    #def inbound_node_connected(self, node):
        #print("inbound_node_connected: (" + str(self.port) + "): " + str(node.port))


    #def inbound_node_disconnected(self, node):
        #print("inbound_node_disconnected: (" + str(self.port) + "): " + str(node.port))


    #def outbound_node_disconnected(self, node):
        #print("outbound_node_disconnected: (" + str(self.port) + "): " + str(node.port))


    def node_message(self, node, data):
        #print("node_message (" + str(self.port) + ") from " + str(node.port) + ": " + str(data))
        if (node.host == '127.0.0.1') and (node.port == 9000):
            if 'nodes:' in data[:6]:
                #try:
                nodesArray = ast.literal_eval(data[6:])                
                #print(nodesArray)
                self.arrNodes = nodesArray
                #except:
                    #print(data[6:])
            elif 'ok:' in data[:3]:
                if data[3:] == 'False':
                    self.reconnect_with_peers()
        elif 'blckHash:' in data[:9]:
            self.tempArrOfHash.append(data)
            if (len(self.tempArrOfHash) >= 3) and (self.sentRequest == 0):
                if self.tempArrOfHash.count(data) >= 3:
                    self.send_to_node(node, 'sendBlockchain')
                    self.sentRequest = 1
                else:
                    self.tempArrOfHash = []
                    self.reconnect_with_peers()
                    for i in self.peers_validators():  
                        self.send_to_node(i, 'sendBlockchainHash')
                        time.sleep(0.3)
        elif type(ast.literal_eval(data)) == dict:
            self.download_blockchain_file(ast.literal_eval(data))
            self.sentRequest = 0
            
            
    def download_blockchain_file(self, dct):
        self.blockchain = dct
        print("\nBlockchain file will be located in directory "+os.getcwd()+".")
        currTimestamp = int(datetime.timestamp(datetime.now()))
        self.blockchainFileName = "blockchain_"+str(self.port)+"_"+str(currTimestamp)+".json"
        print("Downloaded blockchain in file with name " + self.blockchainFileName+"\n")
        f = open(self.blockchainFileName, 'w')
        json.dump(dct, f)
        f.close()
            
    
    #def node_disconnect_with_outbound_node(self, node):
        #print("node wants to disconnect with oher outbound node: (" + self.port + "): " + node.port)
    
    
    #def node_request_to_stop(self):
        #print("node is requested to stop (" + self.port + "): ")
    
    
    def init_connect_to_nodes(self):  
        nodesIndicesToConnect = []

        i = 3
        while (i > 0):
            index = randint(0, len(self.arrNodes)-1)
            if (index not in nodesIndicesToConnect):
                nodesIndicesToConnect.append(index)
                i = i - 1
            else:
                continue

        nodesToConnect = []
        for i in nodesIndicesToConnect:
            nodesToConnect.append(self.arrNodes[i])
            
        self.nodes_inbound = []
        self.nodes_outbound = []
            
        for i in nodesToConnect:
            self.connect_with_node(i[0],i[1])
        
    
    def join_p2p(self): 
        self.connect_with_node('127.0.0.1', 9000)
        sNode = None
        for i in self.nodes_outbound:
            if i.host=='127.0.0.1' and i.port==9000:
                sNode = i
                break
        self.send_to_node(sNode, 'getNodes')
        while (len(self.arrNodes)<=3):
            self.send_to_node(sNode, 'getNodes')
            time.sleep(2)

        self.disconnect_with_node(sNode)
        self.init_connect_to_nodes() 
        time.sleep(1)
        
        
    def check_connected_validators(self):
        if len(self.nodes_outbound) < 1: 
            self.reconnect_with_peers()
        arrToSend = []
        for n in self.nodes_outbound:
            arrToSend.append((str(n.host), int(n.port)))
            
        self.connect_with_node('127.0.0.1', 9000)

        sNode = None
        for i in self.nodes_outbound:
            if i.host=='127.0.0.1' and i.port==9000:
                sNode = i
                break
        self.send_to_node(sNode, 'checkValidators:'+str(arrToSend))
        time.sleep(2)
        self.disconnect_with_node(sNode)
        
        
        
    def make_bet(self, numForProbability, sequenceChoice, keyPair):
        
        pk = keyPair.publickey().exportKey().decode()
        currTimestamp = datetime.timestamp(datetime.now())

        hashOfBetData = SHA256.new((str(pk)+str(numForProbability)+str(sequenceChoice)+str(currTimestamp)).encode())

        signer = PKCS115_SigScheme(keyPair)

        betSgn = signer.sign(hashOfBetData)
        strBetSgn = binascii.hexlify(betSgn).decode()

        dictWithData = {'gamblerPK':pk, 'numForProbability': numForProbability, 'sequenceChoice': sequenceChoice, 'betTimestamp':currTimestamp, 'betSignature': strBetSgn}
        
        hashOfBet = SHA256.new((str(pk)+str(numForProbability)+str(sequenceChoice)+str(currTimestamp)+str(strBetSgn)).encode()).hexdigest()

        dictToSend = {hashOfBet:dictWithData}

        return dictToSend
    
    
    def send_bet_to_peers(self, betDict):
        
        strToSend = 'bet:'+str(betDict)
        self.send_to_validators(strToSend)
        
    
    def check_bet_in_block(self, pk, blockHash, lstBlockBets, binBlock):
        num = 0   
        betsDictionary = {}
        for bet in lstBlockBets:
            if pk == bet[list(bet.keys())[0]]['gamblerPK']:
                num = num + 1 
                betsDictionary[str(num)+"):"+str(blockHash)] = bet  
                prob = bet[list(bet.keys())[0]]['numForProbability']
                seq = bet[list(bet.keys())[0]]['sequenceChoice']
                if seq != binBlock[-int(math.log(int(prob),2)):]:
                    status = "You lost this bet!"
                else:
                    status = "Congratulations! You won x"+prob+"!"
                print("\nBlock hexadecimal: " + str(blockHash) +'\nBlock binary: '+str(binBlock) + '\nBet id: ' + str(list(bet.keys())[0]) +'\nSequence of last '+str(len(seq))+' bit(s) in binary block is: '+str(binBlock[-int(math.log(int(prob),2)):]) + "\nYour predicted sequence was: " + str(seq) + "\n"+str(status)+'\n')
        
        return betsDictionary
    
    
    def check_all_my_bets(self, pk):
        betsDict = {}
        for block in self.blockchain:
            binBlock = bin(int(block, 16))[2:].zfill(256)
            lstBlockBets = self.blockchain[block]['bets']
            dct = self.check_bet_in_block(pk, block, lstBlockBets, binBlock)
            betsDict.update(dct)
        if betsDict == {}:
            print("Nothing found")
        return betsDict
    
    
    def check_last_block(self, pk):
        betsDict = {}
        
        lastBlockHash = list(self.blockchain.keys())[-1]
        lastBlockData = self.blockchain[lastBlockHash]
        
        binBlock = bin(int(lastBlockHash, 16))[2:].zfill(256)

        betsDict = self.check_bet_in_block(pk, lastBlockHash, lastBlockData['bets'], binBlock)
        
        if betsDict == {}:
            print("Nothing found")
                
        return betsDict    


    def peers_validators(self):
        peersValidators = []
        for node in self.nodes_outbound:
            if (node.host == '127.0.0.1' and node.port == 9000):
                continue
            peersValidators.append(node)
        return peersValidators
        
        
    def send_to_validators(self, data):
        for node in self.nodes_outbound:
            if (node.host == '127.0.0.1' and node.port == 9000):
                continue
            self.send_to_node(node, data)


    def reconnect_with_peers(self):
        self.arrNodes = []
        
        for i in self.nodes_outbound:
            self.disconnect_with_node(i)
        self.join_p2p()
        
        
    def time_for_wait_connection(self):
        
        return (datetime.timestamp(datetime.now()) % 120 > 50)


    def time_for_listen_bets(self):
        
        return (datetime.timestamp(datetime.now()) % 120 < 80)
