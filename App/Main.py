### Corpo do programa.
### Concord - Voice Chat

import json
import Voip
import Cliente
import os


#Configuração da rede ZeroTier
ztMananger = Cliente.ZeroTierManager("8056c2e21ca948e3")
ztMananger.join_network()
clientIP = ztMananger.get_ip()
ztMananger.leave_network()

room = Voip.VoipRoom(LOCAL_IP=clientIP,REMOTE_IP="x.x.x.x")
room.start()

