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

class ValidatorNode(Node):
    def __init__(self, host, port, id=None, callback=None, max_connections=0):
        super(ValidatorNode, self).__init__(host, port, id, callback, max_connections)
        print("ValidatorNode: Started")
        self.arrNodes = []
        self.blockchain = {}
        self.tempArrOfHash = []
        self.signalIfWaited = 0
        self.blockchainFileName = ''
        self.sentRequest = 0
        self.receivedBets = []
        self.validBlock = None
        self.allBlockchainBets = []
        self.addedBlock = 0
        self.downloadedBlockchain = 0
        
        
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
                try:
                    nodesArray = ast.literal_eval(data[6:])                
                    #print(nodesArray)
                    self.arrNodes = nodesArray
                except:
                    print("Invalid message: "+data[6:])
            elif 'ok:' in data[:3]:
                if data[3:] == 'False':
                    self.reconnect_with_peers()
        elif data == 'sendBlockchainHash':
            #if (not self.time_for_wait_connection()):
            if self.signalIfWaited:
                f = open('blockchain_initial.json', 'r')
            else:
                f = open(self.blockchainFileName, 'r')
            blockchainToSendHash = str(list(json.load(f))[-1])
            f.close()
            self.send_to_node(node, "blckHash:"+str(blockchainToSendHash))
        elif 'blckHash:' in data[:9]:
            self.tempArrOfHash.append(data)
            if (len(self.tempArrOfHash) >= 3) and (self.sentRequest == 0):
                if self.tempArrOfHash.count(data) >= 3:
                    self.send_to_node(node, 'sendBlockchain')
                    time.sleep(1)
                    self.send_to_node(node, 'sendBets')
                    self.sentRequest = 1
                else:
                    self.tempArrOfHash = []
                    self.reconnect_with_peers()
                    for i in self.peers_validators(): 
                        self.send_to_node(i, 'sendBlockchainHash')
                        time.sleep(0.3)
        elif data == 'sendBlockchain':
            if (datetime.timestamp(datetime.now()) % 120 < 55):
                if self.signalIfWaited:
                    f = open('blockchain_initial.json', 'r')
                else:
                    f = open(self.blockchainFileName, 'r')
                blockchainToSend = json.load(f)
                f.close()
                self.send_to_node(node, str(blockchainToSend))
        elif data == 'sendBets':
            listBetsWithoutDups = [i for n, i in enumerate(self.receivedBets) if i not in self.receivedBets[:n]]
            self.send_to_node(node, 'bets:'+str(listBetsWithoutDups))
        elif 'bets:' in data[:5]:
            try:
                self.receivedBets = ast.literal_eval(data[5:])
                dBets = self.receivedBets
                for i in dBets:
                    if (not self.valid_bet(i)):
                        self.receivedBets.remove(i)
                    else:
                        print('Received valid bet: ' + str(list(i.keys())[0]))
            except:
                print("Invalid bets message: " + str(data))
        elif 'bet:' in data[:4]:
            if (self.time_for_listen_bets() and self.downloadedBlockchain):
                try:
                    receivedBet = ast.literal_eval(data[4:])
                    if (receivedBet not in self.receivedBets) and (self.valid_bet(receivedBet)):
                        print('Received bet: '+str(list(receivedBet.keys())[0]))
                        self.receivedBets.append(receivedBet)
                        self.send_to_validators(data)
                    #else:
                        #print('\n\n\nBet is invalid or already in list\n\n\n')
                except: 
                    print("Invalid bet message: " + str(data))
        elif 'block:' in data[:6]:
            if (not self.addedBlock) and (self.time_for_listen_blocks()):
                try:
                    receivedBlock = ast.literal_eval(data[6:])
                    if self.valid_block(receivedBlock):
                        print('Received block: '+str(list(receivedBlock.keys())[0]))
                        if self.validBlock == None:
                            self.validBlock = receivedBlock
                            #print('\n\n\n'+str(self.validBlock)+'\n\n\n')
                            time.sleep(1)
                            self.send_to_validators('block:'+str(receivedBlock))
                        elif list(receivedBlock.keys())[0] < list(self.validBlock.keys())[0]:
                            self.validBlock = receivedBlock
                            #print('\n\n\n'+str(self.validBlock)+'\n\n\n')
                            time.sleep(1)
                            self.send_to_validators('block:'+str(receivedBlock))
                    #else:
                        #print('\n\n\nReceived invalid block\n\n\n')
                except:
                    print("Invalid block message: " + str(data))
        elif type(ast.literal_eval(data)) == dict:
            self.download_blockchain_file(ast.literal_eval(data))
            self.sentRequest = 0
            self.signalIfWaited = 0
            
            
    def download_blockchain_file(self, dct):
        self.blockchain = dct
        print("\nBlockchain file will be located in directory "+os.getcwd()+".\nDON'T replace or remove it!")
        currTimestamp = int(datetime.timestamp(datetime.now()))
        self.blockchainFileName = "blockchain_"+str(self.port)+"_"+str(currTimestamp)+".json"
        print("Downloaded blockchain in file with name " + self.blockchainFileName+"\n")
        f = open(self.blockchainFileName, 'w')
        json.dump(dct, f)
        f.close()
        self.allBlockchainBets = self.list_of_bets_in_blockchain()
        self.downloadedBlockchain = 1
         
         
    def add_block_to_blockchain(self):
        print('\n\nStarted adding block')
        print('\nHash of valid block for adding in blockchain is:\n'+str(list(self.validBlock.keys())[0])+'\n\n')
        blockHash = list(self.validBlock.keys())[0]
        blockData = self.validBlock[blockHash]
        self.blockchain[blockHash] = blockData
        f = open(self.blockchainFileName, "w")
        json.dump(self.blockchain, f)
        f.close()
        self.allBlockchainBets = self.list_of_bets_in_blockchain()
        self.validBlock = None
        #print('\n\n\n'+str(self.validBlock)+'\n\n\n')
        self.receivedBets = []
        self.addedBlock = 1
    
    
    #def node_disconnect_with_outbound_node(self, node):
        #print("node wants to disconnect with oher outbound node: (" + self.id + "): " + node.id)
    
    
    #def node_request_to_stop(self):
        #print("node is requested to stop (" + self.id + "): ")
    
    
    def init_connect_to_nodes(self, host, port):

        nodesIndicesToConnect = []

        i = 3
        while (i > 0):
            index = randint(0, len(self.arrNodes)-1)
            if (index not in nodesIndicesToConnect) and (index != self.arrNodes.index((host, port))):
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
        self.send_to_node(sNode, 'connect')
        self.send_to_node(sNode, 'getNodes')
        while (len(self.arrNodes)<=3):
            self.signalIfWaited = 1
            self.send_to_node(sNode, 'getNodes')
            time.sleep(2)

        self.disconnect_with_node(sNode)
        self.init_connect_to_nodes(self.host, self.port)
        time.sleep(2)
        
        
    def check_connected_validators(self):
        if len(self.nodes_inbound) + len(self.nodes_outbound) < 3:
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
        time.sleep(1)
        self.send_to_node(sNode, 'hi') #say hi to main node every 2 min
        self.disconnect_with_node(sNode)
        
        
    def valid_bet(self, bet):
        betHashStr = list(bet.keys())[0]
    
        currTimestamp = datetime.timestamp(datetime.now())
        
        strBetPK = bet[betHashStr]['gamblerPK']
        betPK = RSA.importKey(strBetPK.encode())
        
        numForProbability = bet[betHashStr]['numForProbability']
        sequenceChoice = bet[betHashStr]['sequenceChoice']
        
        betTimestamp = bet[betHashStr]['betTimestamp']

        betSignature = bet[betHashStr]['betSignature']
        betSgn = binascii.unhexlify(betSignature.encode())

        hashOfBet = SHA256.new((str(strBetPK)+str(numForProbability)+str(sequenceChoice)+str(betTimestamp)+str(betSignature)).encode()).hexdigest()

        hashOfBetData = SHA256.new((str(strBetPK)+str(numForProbability)+str(sequenceChoice)+str(betTimestamp)).encode())
        
        betVerifier = PKCS115_SigScheme(betPK)
        
        prevBlockTimestamp = float(self.blockchain[list(self.blockchain.keys())[-1]]['blockTimestamp'])
        
        if (float(betTimestamp) < prevBlockTimestamp):
            return 0
        
        if currTimestamp <= float(betTimestamp):
            return 0
        
        if (betHashStr != hashOfBet):
            return 0
        
        for b in self.allBlockchainBets:
            if b == betHashStr:
                return 0
        try:
            betVerifier.verify(hashOfBetData, betSgn)
            return 1
        except:
            return 0
    
        
        
    def make_block(self, keyPair):
        
        pk = keyPair.publickey().exportKey().decode()
        
        currTimestamp = datetime.timestamp(datetime.now())
        
        prevBlockHash = list(self.blockchain.keys())[-1]
        
        bets = [i for n, i in enumerate(self.receivedBets) if i not in self.receivedBets[:n]]
        
        myBlockValue = {}
        myBlockValue['validatorPK'] = pk
        myBlockValue['blockTimestamp'] = currTimestamp
        myBlockValue['prevBlockHash'] = prevBlockHash
        myBlockValue['bets'] = bets
        
        hashToSign = SHA256.new((str(pk)+str(currTimestamp)+str(prevBlockHash)+str(bets)).encode())
        
        signer = PKCS115_SigScheme(keyPair)
        
        blockSignature = signer.sign(hashToSign)
        strBlockSgn = binascii.hexlify(blockSignature).decode()
        
        myBlockValue['blockSignature'] = strBlockSgn
        
        hashOfMyBlock = SHA256.new((str(pk)+str(currTimestamp)+str(prevBlockHash)+str(bets)+str(strBlockSgn)).encode()).hexdigest()
        
        myBlock = {hashOfMyBlock:myBlockValue}

        return myBlock
        
        
    def send_block_to_peers(self, blockDict):
        
        strToSend = 'block:'+str(blockDict)
        self.send_to_validators(strToSend)
        
    
    def valid_block(self, block):
        
        prevBlockHash = list(self.blockchain.keys())[-1]
        
        currTimestamp = datetime.timestamp(datetime.now())
        
        prevBlockTimestamp = float(self.blockchain[list(self.blockchain.keys())[-1]]['blockTimestamp'])
        
        blockHashStr = list(block.keys())[0]

        pk = block[blockHashStr]['validatorPK']        
        blockOwnerPK = RSA.importKey(pk.encode())
        
        blockTimestamp = block[blockHashStr]['blockTimestamp']
        
        blockPrevHash = block[blockHashStr]['prevBlockHash']
    
        blockBets = block[blockHashStr]['bets']
        
        blockSignature = block[blockHashStr]['blockSignature']
        blockSgn = binascii.unhexlify(blockSignature.encode())
        
        hashToValidateBlock = SHA256.new((str(pk)+str(blockTimestamp)+str(blockPrevHash)+str(blockBets)+str(blockSignature)).encode()).hexdigest()
        
        hashToValidateSignature = SHA256.new((str(pk)+str(blockTimestamp)+str(blockPrevHash)+str(blockBets)).encode())
        
        blockVerifier = PKCS115_SigScheme(blockOwnerPK)
        
        if (currTimestamp <= float(blockTimestamp)) or (float(blockTimestamp) <= float(prevBlockTimestamp)):
            return 0

        if (hashToValidateBlock != blockHashStr):
            return 0
        
        listOfBets = blockBets
        
        for i in listOfBets:
            betTs = float(i[list(i.keys())[0]]['betTimestamp'])
            if (not self.valid_bet(i)) or (betTs > float(blockTimestamp)) or (betTs > currTimestamp):
                return 0
            
        hashBetsRecv = []
        hashBetsFromBlock = []
        listOfBetsWithoutDups = [i for n, i in enumerate(self.receivedBets) if i not in self.receivedBets[:n]]
        for i in listOfBetsWithoutDups:
            hashBetsRecv.append(list(i.keys())[0])
        for j in listOfBets:
            hashBetsFromBlock.append(list(j.keys())[0])
            
        if sorted(hashBetsRecv) != sorted(hashBetsFromBlock):
            return 0
        
        try:
            blockVerifier.verify(hashToValidateSignature, blockSgn)
            return 1
        except:
            return 0
        

    def list_of_bets_in_blockchain(self):
        lst = []
        for block in self.blockchain:
            bData = self.blockchain[block]
            lstBlockBets = bData['bets']
            for bt in lstBlockBets:
                lst.append(list(bt.keys())[0])
        return lst
    
        
    def leave_p2p(self):
        self.connect_with_node('127.0.0.1', 9000)
        sNode = None
        for i in self.nodes_outbound:
            if i.host=='127.0.0.1' and i.port==9000:
                sNode = i
                break
        self.send_to_node(sNode, 'disconnect')
        self.disconnect_with_node(sNode)
        for i in self.nodes_outbound:
            self.disconnect_with_node(i)
            
            
    def peers_validators(self):
        peersValidators = []
        for n in self.nodes_inbound:
            if (n not in peersValidators) and ('validator:' in str(n.id)[:10]):
                peersValidators.append(n)
        for n in self.nodes_outbound:
            if (n not in peersValidators) and ('validator:' in str(n.id)[:10]):
                peersValidators.append(n)
                        
        arr = []
        for i in peersValidators:
            arr.append((i.host, i.port, i.id))

        arrWithoutDups = [j for k, j in enumerate(arr) if j not in arr[:k]]
        
        listWithoutDups = []
        for n in arrWithoutDups:
            for m in peersValidators:
                if m.host == n[0] and m.port == n[1] and m.id == n[2]:
                    listWithoutDups.append(m)
                    break
        
        return listWithoutDups
        
        
    def send_to_validators(self, data):
        
        for node in self.peers_validators():
            self.send_to_node(node, data)


    def reconnect_with_peers(self):
        self.signalIfWaited = 0
        self.arrNodes = []
        
        for i in self.nodes_outbound:
            self.disconnect_with_node(i)
        
        self.connect_with_node('127.0.0.1', 9000)

        sNode = None
        for i in self.nodes_outbound:
            if i.host=='127.0.0.1' and i.port==9000:
                sNode = i
                break
        self.send_to_node(sNode, 'getNodes')
        while (len(self.arrNodes)<=3):
            self.signalIfWaited = 1
            self.send_to_node(sNode, 'getNodes')
            time.sleep(2)

        self.disconnect_with_node(sNode)
        self.init_connect_to_nodes(host, port)
        
        
    
    def time_for_wait_connection(self):
    
        return (datetime.timestamp(datetime.now()) % 120 > 50)


    def time_for_listen_bets(self):
        
        return (datetime.timestamp(datetime.now()) % 120 < 80)


    def time_for_listen_blocks(self):
        
        return ((datetime.timestamp(datetime.now()) % 120 < 120) and (datetime.timestamp(datetime.now()) % 120 > 80))
        
