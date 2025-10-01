<p align="center">
<img alt="Spea-K Logo" src="App/logo.png" width="240" height="240"/>
</p>

# Spea-K (Concord)

## 📜 Sobre o Projeto
Este projeto é uma aplicação de chat por voz (VoIP) ponto a ponto (P2P) para redes locais. Ele foi projetado para ser simples e não depender de servidores centrais para a comunicação. A descoberta de outros usuários na rede é feita automaticamente, e a interface é uma aplicação web moderna renderizada em uma janela de desktop.

---

## 🚀 Principais Funcionalidades
1. **Comunicação por Voz P2P**:
   - Chamadas de áudio diretas entre dois usuários na mesma rede, sem passar por um servidor.

2. **Descoberta Automática de Peers**:
   - Utiliza pacotes de broadcast UDP para encontrar outros usuários na rede local automaticamente. Não é necessário inserir IPs manualmente.

3. **Interface Web Moderna**:
   - A interface do usuário é construída com React e renderizada dentro de uma janela nativa usando `pywebview`, combinando a flexibilidade da web com a experiência de um aplicativo de desktop.

4. **Atualizações em Tempo Real**:
   - A lista de peers e o status das chamadas são atualizados instantaneamente através de Server-Sent Events (SSE), proporcionando uma experiência fluida.

5. **Gerenciamento de Áudio**:
   - Permite selecionar dispositivos de entrada e saída, testar o microfone e o áudio, e ajustar os volumes.

6. **Integração com Firewall do Windows**:
   - Na primeira execução, o aplicativo solicita permissão de administrador para criar uma regra no Firewall do Windows, garantindo que a descoberta de peers funcione corretamente.

---

## 📂 Estrutura do Projeto
```plaintext
📁 Concord
└── 📁 App
    ├── Main.py              # Ponto de entrada, orquestra todos os componentes
    ├── Discovery.py         # Lógica de descoberta de peers e sinalização de chamadas
    ├── Voip.py              # Gerencia o stream de áudio P2P durante uma chamada
    ├── Api.py               # API Flask que serve como ponte entre o backend e o frontend
    ├── Settings.py          # Gerencia as configurações do usuário em um banco de dados SQLite
    ├── front.tsx            # Componente React para a tela principal
    ├── settings.tsx         # Componente React para a tela de configurações
    └── ...                  # Outros arquivos de frontend e recursos
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
