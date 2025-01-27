<p align="center">
<img alt="Concord Logo" src="logo.png" width="120" height="120"/>
</p>

# Concord

## 📜 Sobre o Projeto
Este projeto é uma aplicação Python para comunicação por voz ponto a ponto (P2P) que combina o uso da tecnologia ZeroTier para criar uma rede privada virtual (VPN) e um sistema de gerenciamento de salas. A ideia central é permitir que clientes conectem-se diretamente uns aos outros de maneira segura e eficiente, utilizando um ID de sala compartilhado para organizar e facilitar as conexões.

---

## 🚀 Principais Funcionalidades
1. **Conexão com ZeroTier**:
   - Criação de uma rede VPN utilizando o ZeroTier para facilitar a comunicação direta entre os dispositivos.
   - Gerenciamento automático de conexões à rede ZeroTier, incluindo obtenção de IPs privados para comunicação.

2. **Gerenciamento de Salas**:
   - Sistema de criação e entrada em salas com base em IDs.
   - O primeiro cliente que tenta entrar em uma sala automaticamente cria a sala, permitindo que outros usuários se juntem ao grupo.
   - Lista de peers conectados na mesma sala para facilitar a troca de informações entre clientes.

3. **Base para Comunicação P2P**:
   - Estrutura pronta para implementar troca de dados (como voz) diretamente entre os clientes.

---

## 📂 Estrutura do Projeto
```plaintext
📁 Concord
├── README.md            # Documentação do projeto
├── main.py              # Arquivo principal para inicializar o programa
├── zerotier_manager.py  # Módulo de gerenciamento de ZeroTier
├── room_manager.py      # Módulo de gerenciamento de salas
└── requirements.txt     # Dependências do projeto
```

## 📦 Instalação e Configuração
Pré-requisitos
Python 3.8+: Certifique-se de ter o Python instalado em sua máquina.

ZeroTier: Instale o cliente ZeroTier em seu dispositivo.

No Linux/MacOS:
```bash
curl -s https://install.zerotier.com | sudo bash
```
No Windows: Baixe o cliente [aqui](https://www.zerotier.com/download/) e instale.

Dependências do projeto: Instale as bibliotecas Python necessárias:

```bash
pip install -r requirements.txt
```

Criação da Rede ZeroTier:

Crie uma conta no ZeroTier Central.
Crie uma nova rede e copie o Network ID.

Configuração
No arquivo main.py, substitua "your_zerotier_network_id" pelo ID da rede ZeroTier criada.

Execute o programa:
```bash
python main.py
```

---

## 🛠️ Como Funciona?
ZeroTier Manager:

Gerencia a conexão do cliente à rede ZeroTier.
Obtém o IP privado do cliente na rede.
Room Manager:

Cria ou entra em salas com IDs compartilhados.
Associa os clientes às salas utilizando seus IPs ZeroTier.
Retorna a lista de peers conectados na mesma sala.
Fluxo do Programa:

O cliente conecta-se à rede ZeroTier.
Obtém o IP fornecido pela rede.
Cria ou entra em uma sala específica.
Troca informações com outros clientes conectados à mesma sala.

---

## 🔧 Próximos Passos
Comunicação P2P:

Implementar troca de áudio e mensagens diretamente entre os clientes.
Sincronização de Salas:

Adicionar um servidor centralizado ou criar um mecanismo P2P para sincronização automática de informações das salas.
Interface Gráfica:

Desenvolver uma interface gráfica para facilitar o gerenciamento de salas e conexões.
Segurança Avançada:

Implementar autenticação e criptografia adicionais nas trocas de dados entre os clientes.

---

## 📖 Exemplos de Uso

Criar ou Entrar em uma Sala
```python
from room_manager import RoomManager
from zerotier_manager import ZeroTierManager

# Configurações iniciais
NETWORK_ID = "your_zerotier_network_id"
CLIENT_ID = "meu-cliente-123"

# Inicializar gerenciadores
zt_manager = ZeroTierManager(NETWORK_ID)
room_manager = RoomManager()

# Conectar ao ZeroTier e obter IP
zt_manager.join_network()
ip = zt_manager.get_ip()

# Entrar em uma sala
if ip:
    room_id = "sala-teste"
    room_manager.join_room(room_id, CLIENT_ID, ip)
    peers = room_manager.get_peers(room_id, CLIENT_ID)
    print(f"Peers conectados na sala '{room_id}': {peers}")
```

---

## 📜 Licença
Este projeto está licenciado sob a MIT License. Sinta-se à vontade para usá-lo, modificá-lo e compartilhá-lo!

---

## 🤝 Contribuições
Contribuições são muito bem-vindas! Se você tiver ideias ou melhorias, abra uma issue ou envie um pull request.

---

## 💬 Contato
Se tiver dúvidas ou sugestões, entre em contato:

Email: keysonfcorreia@icloud.com
GitHub: Keyditor
