# Freddy Security System (FAZBEAR-HOME-SERVICE-2050)

Sistema de segurança com Python, câmera e Arduino. A câmera detecta presença (OpenCV), o Arduino mostra o estado em dois anéis de LED NeoPixel (azul = normal, vermelho = movimento) e o sistema grava vídeos automaticamente, com login protegido por MySQL.

## Funcionalidades

- Interface gráfica em Tkinter com câmera ao vivo
- Detecção de presença por câmera (reconhecimento de rosto) e por sensor no Arduino
- Alerta visual: dois anéis NeoPixel mudam de azul para vermelho ao mesmo tempo
- Gravação automática de 5 segundos ao detectar movimento, além de gravação e foto manuais
- Registro de horário dos movimentos (`movimentos.log`)
- Login e cadastro de usuários, com senha protegida por hash (PBKDF2 + salt) e código de recuperação
- Página web para assistir e baixar as gravações pelo celular
- Tema claro e escuro

## Requisitos

- Windows (o programa usa `os.startfile`, que só existe no Windows)
- Python 3.8 ou superior
- MySQL Server 8
- Arduino com 2 anéis NeoPixel de 12 LEDs
- Webcam
- Arduino IDE (para gravar o sketch)

## Instalação

### 1. Baixar o projeto

```
git clone https://github.com/Rayza-matias2005/FAZBEAR-HOME-SERVICE-2050.git
cd FAZBEAR-HOME-SERVICE-2050
```

### 2. Instalar as bibliotecas Python

```
pip install -r requirements.txt
```

### 3. Configurar o banco de dados

1. Instale o MySQL Server e defina a senha do usuário administrador (`root`) durante a instalação.
2. Importe o arquivo `freddy_security.sql` (ele cria o banco e a tabela de usuários):
   ```
   mysql -u root -p < freddy_security.sql
   ```
3. Crie um usuário só para o projeto, com acesso apenas ao banco `freddy_security`. Entre no MySQL como administrador:
   ```
   mysql -u root -p
   ```
   e execute (troque `SUA_SENHA_AQUI` por uma senha de sua escolha):
   ```sql
   CREATE USER 'freddy_app'@'localhost' IDENTIFIED BY 'SUA_SENHA_AQUI';
   GRANT SELECT, INSERT, UPDATE, DELETE ON freddy_security.* TO 'freddy_app'@'localhost';
   FLUSH PRIVILEGES;
   ```
   Se preferir, pode usar o próprio `root` no passo seguinte, mas um usuário dedicado é mais seguro, porque só enxerga o banco do projeto.
4. Abra o arquivo `Freddy_Security_Login/mysql_config.json` e coloque os dados do seu MySQL (o arquivo `mysql_config.example.json`, na mesma pasta, mostra o formato esperado):
   ```json
   {
     "host": "localhost",
     "port": 3306,
     "user": "freddy_app",
     "password": "SUA_SENHA_AQUI",
     "database": "freddy_security"
   }
   ```
   O programa usa esses dados para conectar ao banco, então a senha precisa ser a que você definiu para o `freddy_app` no passo anterior. Se o arquivo não existir, copie o `mysql_config.example.json` e renomeie a cópia para `mysql_config.json`.

### 4. Montar e programar o Arduino

1. No Arduino IDE, instale a biblioteca **Adafruit NeoPixel** (Gerenciar Bibliotecas).
2. Ligue os dois anéis:

   | Anel | Pino de dados (DIN) | Alimentação |
   |------|---------------------|-------------|
   | Anel 1 | 6 | 5V e GND |
   | Anel 2 | 7 | 5V e GND |

   O GND do Arduino e dos anéis deve ser comum. Ligue o fio de dados no DIN (entrada) de cada anel, não no DOUT.
3. Abra o sketch da pasta `sketch_oct31a`, grave na placa e **feche o Serial Monitor** depois.

O Arduino entende dois comandos enviados pelo Python pela serial:

| Comando | Efeito |
|---------|--------|
| `MOVIMENTO` | os dois anéis ficam vermelhos |
| `NORMAL` | os dois anéis ficam azuis |

Se você usar um sensor de movimento no Arduino, ele deve enviar `SENSOR=1` (presença) e `SENSOR=0` (sem presença) pela serial.

### 5. Ajustar a porta e a câmera

No início do arquivo principal do Python, confira estas duas linhas:

```python
CAMERA_ID = 0            # troque se o PC tiver mais de uma câmera
PORTA_ARDUINO = "COM3"   # veja a porta correta no Arduino IDE (Ferramentas > Porta)
```

## Como executar

Feche o Arduino IDE e o Serial Monitor (eles ocupam a porta COM) e rode:

```
cd Freddy_Security_Login
python NOME_DO_ARQUIVO_PRINCIPAL.py
```

Na primeira vez, clique em **Cadastrar usuário**. O sistema mostra um **código de recuperação** uma única vez: guarde-o, porque ele é necessário para redefinir a senha.

## Acesso às gravações pelo celular (opcional)

O programa abre um servidor local na porta `8765`. Para acessar de fora da sua rede, use o [ngrok](https://ngrok.com/):

```
ngrok http 8765
```

Depois clique em **Acesso no celular** no programa para ver o endereço.

**Atenção:** a página de gravações não pede senha. Quem tiver o link do ngrok consegue ver e baixar os vídeos, então compartilhe o endereço com cuidado e feche o túnel quando não estiver usando.

## Estrutura do projeto

```
FAZBEAR-HOME-SERVICE-2050/
├── Freddy_Security_Login/     # programa em Python (login + monitoramento)
│   ├── mysql_config.json          # configuração de acesso ao MySQL
│   └── mysql_config.example.json  # modelo do formato da configuração
├── sketch_oct31a/             # sketch do Arduino (anéis NeoPixel)
├── freddy_security.sql        # banco de dados MySQL
├── requirements.txt           # bibliotecas Python
└── README.md
```

## Tecnologias

Python, Tkinter, OpenCV, Pillow, PySerial, MySQL, hashlib, http.server, Arduino (C++) e Adafruit NeoPixel.

## Problemas comuns

| Problema | O que verificar |
|----------|-----------------|
| "ARDUINO DESCONECTADO" | Porta COM errada, cabo USB solto, ou Arduino IDE / Serial Monitor aberto |
| Câmera "Sem sinal" | Troque o `CAMERA_ID` (0, 1, 2...) ou feche outros programas que usam a câmera |
| Erro ao entrar ou cadastrar | MySQL desligado, `mysql_config.json` ausente ou senha errada |
| Anel de LED não acende | Fio no DIN, GND em comum e pino correto (6 e 7) |