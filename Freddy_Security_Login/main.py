import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import cv2
from PIL import Image, ImageTk
import os
import serial
import time
import sqlite3
import hashlib
import secrets
import json
import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

FUNDO = "#050609"
PAINEL = "#0c0e13"
VERMELHO = "#e31837"
BRANCO = "#eeeeee"
CINZA = "#858b98"
VERDE = "#24cf54"
BORDA = "#282b35"

CAMERA_ID = 0
PORTA_ARDUINO = "COM3"
BAUD_RATE = 9600

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PASTA_PROJETO, "freddy.db")
ARQUIVO_TEMA = os.path.join(PASTA_PROJETO, "freddy_config.json")
ARQUIVO_MOVIMENTOS = os.path.join(PASTA_PROJETO, "movimentos.log")
PORTA_WEB = 8765


class ServidorGravacoes(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class ManipuladorGravacoes(BaseHTTPRequestHandler):
    def do_GET(self):
        caminho_url = urlparse(self.path).path
        if caminho_url == "/":
            self.enviar_pagina()
        elif caminho_url.startswith("/video/"):
            self.enviar_video(unquote(caminho_url[len("/video/"):]))
        elif caminho_url.startswith("/stream/"):
            self.transmitir_video(unquote(caminho_url[len("/stream/"):]))
        else:
            self.send_error(404)

    def enviar_pagina(self):
        arquivos = []
        try:
            for nome in os.listdir(PASTA_PROJETO):
                caminho = os.path.join(PASTA_PROJETO, nome)
                if (nome.lower().startswith("freddy_") and nome.lower().endswith(".avi")
                        and os.path.isfile(caminho)):
                    arquivos.append((nome, os.path.getmtime(caminho)))
        except OSError:
            arquivos = []
        arquivos.sort(key=lambda item: item[1], reverse=True)
        if arquivos:
            cartoes = []
            for nome, alterado_em in arquivos:
                seguro = html.escape(nome)
                url_stream = html.escape("/stream/" + quote(nome, safe=""))
                url_download = html.escape("/video/" + quote(nome, safe=""))
                tamanho = os.path.getsize(os.path.join(PASTA_PROJETO, nome))
                tamanho_mb = tamanho / (1024 * 1024)
                data = datetime.fromtimestamp(alterado_em).strftime("%d/%m/%Y às %H:%M")
                cartoes.append(
                    f"<article class='card'><div class='player'><img class='tela' "
                    f"alt='Reprodução de {seguro}'></div><div class='detalhes'>"
                    f"<h2>{seguro}</h2><p>{data} · {tamanho_mb:.1f} MB</p>"
                    f"<div class='acoes'><button onclick=\"assistir(this,'{url_stream}')\">▶ Assistir</button>"
                    f"<a class='baixar' href='{url_download}'>⇩ Baixar</a></div></div></article>"
                )
            conteudo = "".join(cartoes)
        else:
            conteudo = "<div class='vazio'>Ainda não há gravações salvas.</div>"
        pagina = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gravações | Freddy Security</title>
<style>
:root{{--fundo:#0b0d12;--painel:#151922;--borda:#252b36;--texto:#f2f3f5;--muted:#9299a6;--red:#e31837}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at top,#231019 0,#0b0d12 48%);color:var(--texto);font:16px 'Segoe UI',Arial,sans-serif;min-height:100vh}}
header{{max-width:980px;margin:auto;padding:30px 20px 20px;display:flex;align-items:center;gap:15px}}
.logo{{width:52px;height:52px;border-radius:16px;background:var(--red);display:grid;place-items:center;font-weight:800;font-size:25px;box-shadow:0 8px 30px #e3183740}}
h1{{font-size:clamp(24px,5vw,34px);margin:0}}header p{{margin:5px 0 0;color:var(--muted)}}
main{{max-width:980px;margin:auto;padding:0 20px 36px}}.resumo{{color:var(--muted);margin:4px 0 18px}}
.lista{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:16px}}
.card{{overflow:hidden;border:1px solid var(--borda);border-radius:18px;background:linear-gradient(145deg,#191e28,#11141b);box-shadow:0 14px 35px #0005}}
.player{{background:#050608;aspect-ratio:16/9;display:grid;place-items:center}}.tela{{display:none;width:100%;height:100%;object-fit:contain}}
.detalhes{{padding:16px}}h2{{font-size:16px;overflow-wrap:anywhere;margin:0 0 7px}}.detalhes p{{font-size:13px;color:var(--muted);margin:0 0 15px}}
.acoes{{display:flex;gap:10px}}button,.baixar{{border:0;border-radius:10px;padding:11px 15px;font:600 14px 'Segoe UI',Arial;cursor:pointer;text-decoration:none;text-align:center}}
button{{background:var(--red);color:white;flex:1}}button:active{{transform:scale(.98)}}.baixar{{background:#282e39;color:var(--texto);min-width:112px}}
.vazio{{background:var(--painel);border:1px solid var(--borda);border-radius:16px;color:var(--muted);padding:28px;text-align:center}}
footer{{max-width:980px;margin:auto;padding:0 20px 24px;color:#747b88;font-size:12px}}
</style></head><body>
<header><div class="logo">F</div><div style="flex:1"><h1>Suas gravações</h1><p>Freddy Security · </p></div><a class="baixar" href="/">↻ Atualizar</a></header>
<main><p class="resumo">{len(arquivos)} vídeo(s) · toque em Assistir para ver sem baixar</p><section class="lista">{conteudo}</section></main>
<footer>Os vídeos são enviados pelo computador enquanto o Freddy Security está aberto.</footer>
<script>
function assistir(botao,url){{const tela=botao.closest('.card').querySelector('.tela');
if(botao.dataset.tocando==='1'){{tela.src='';tela.style.display='none';botao.dataset.tocando='0';botao.textContent='▶ Assistir';return;}}
tela.src=url+'?t='+Date.now();tela.style.display='block';botao.dataset.tocando='1';botao.textContent='■ Parar';}}
</script></body></html>""".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(pagina)))
        self.end_headers()
        self.wfile.write(pagina)

    def enviar_video(self, nome):
        caminho = self.caminho_gravacao(nome)
        if not caminho:
            self.send_error(404)
            return
        try:
            tamanho = os.path.getsize(caminho)
            nome_download = quote(nome)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(tamanho))
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{nome_download}")
            self.end_headers()
            with open(caminho, "rb") as arquivo:
                while bloco := arquivo.read(64 * 1024):
                    self.wfile.write(bloco)
        except (OSError, BrokenPipeError):
            pass

    def transmitir_video(self, nome):
        caminho = self.caminho_gravacao(nome)
        if not caminho:
            self.send_error(404)
            return
        captura = cv2.VideoCapture(caminho)
        if not captura.isOpened():
            captura.release()
            self.send_error(500, "Não foi possível abrir esta gravação")
            return
        fps = captura.get(cv2.CAP_PROP_FPS)
        intervalo = 1.0 / fps if fps and fps > 0 else 1.0 / 20.0
        try:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            while True:
                inicio = time.monotonic()
                ok, quadro = captura.read()
                if not ok:
                    break
                ok, imagem = cv2.imencode(".jpg", quadro)
                if not ok:
                    continue
                dados = imagem.tobytes()
                self.wfile.write(
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(dados)).encode("ascii") + b"\r\n\r\n" + dados + b"\r\n"
                )
                atraso = intervalo - (time.monotonic() - inicio)
                if atraso > 0:
                    time.sleep(atraso)
        except (OSError, BrokenPipeError):
            pass
        finally:
            captura.release()

    @staticmethod
    def caminho_gravacao(nome):
        if (not nome or os.path.basename(nome) != nome or not nome.lower().startswith("freddy_")
                or not nome.lower().endswith(".avi")):
            return None
        caminho = os.path.join(PASTA_PROJETO, nome)
        return caminho if os.path.isfile(caminho) else None

    def log_message(self, formato, *args):
        pass

def conectar_banco():
    conexao = sqlite3.connect(DB_PATH)
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
            salt TEXT NOT NULL,
            senha TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            recovery_salt TEXT,
            recovery_hash TEXT
        )
    """)
    colunas = {
        linha[1] for linha in conexao.execute("PRAGMA table_info(usuarios)").fetchall()
    }
    if "recovery_salt" not in colunas:
        conexao.execute("ALTER TABLE usuarios ADD COLUMN recovery_salt TEXT")
    if "recovery_hash" not in colunas:
        conexao.execute("ALTER TABLE usuarios ADD COLUMN recovery_hash TEXT")
    conexao.commit()
    return conexao

def gerar_senha(senha, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    )
    return salt, resultado.hex()

def cadastrar_usuario(usuario, senha):
    usuario = usuario.strip()
    if not usuario or not senha:
        return False, "Preencha o usuário e a senha."
    if len(usuario) < 3:
        return False, "O usuário precisa ter pelo menos 3 caracteres."
    if len(senha) < 8:
        return False, "A senha precisa ter pelo menos 8 caracteres."

    salt, senha_hash = gerar_senha(senha)
    codigo_recuperacao = secrets.token_hex(4).upper()
    recovery_salt, recovery_hash = gerar_senha(codigo_recuperacao)
    try:
        with conectar_banco() as conexao:
            conexao.execute(
                """INSERT INTO usuarios
                   (usuario, salt, senha, criado_em, recovery_salt, recovery_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    usuario, salt, senha_hash,
                    datetime.now().isoformat(timespec="seconds"),
                    recovery_salt, recovery_hash
                )
            )
        return True, (
            "Usuário cadastrado com sucesso!\n\n"
            f"SEU CÓDIGO DE RECUPERAÇÃO: {codigo_recuperacao}\n\n"
            "Guarde este código em um local seguro. Ele será necessário "
            "se você esquecer sua senha. Ele não será exibido novamente."
        )
    except sqlite3.IntegrityError:
        return False, "Esse nome de usuário já está cadastrado."
    except sqlite3.Error as erro:
        return False, f"Erro ao salvar no banco de dados: {erro}"

def validar_login(usuario, senha):
    try:
        with conectar_banco() as conexao:
            registro = conexao.execute(
                "SELECT salt, senha FROM usuarios WHERE usuario = ?",
                (usuario.strip(),)
            ).fetchone()
    except sqlite3.Error:
        return False

    if registro is None:
        return False

    salt, hash_salvo = registro
    _, hash_digitado = gerar_senha(senha, salt)
    return secrets.compare_digest(hash_digitado, hash_salvo)

class TelaLogin:
    def __init__(self, janela, ao_entrar):
        self.janela = janela
        self.ao_entrar = ao_entrar
        self.janela.title("FREDDY SECURITY SYSTEM | LOGIN")
        self.janela.geometry("1050x680")
        self.janela.minsize(850, 600)
        self.janela.configure(bg="#050609")
        self.mostrar_senha = False
        self.criar_interface()

    def criar_interface(self):
        fundo = tk.Frame(self.janela, bg="#050609")
        fundo.pack(fill="both", expand=True)

        
        topo = tk.Frame(fundo, bg="#0a0c12", height=48)
        topo.pack(fill="x", padx=18, pady=(18, 0))
        topo.pack_propagate(False)

        tk.Label(
            topo, text="● SISTEMA DE SEGURANÇA / ACESSO RESTRITO",
            font=("Consolas", 10, "bold"), fg=VERMELHO, bg="#0a0c12"
        ).pack(side="left", padx=18, pady=14)

        tk.Label(
            topo, text="CAM 01  ● ONLINE",
            font=("Consolas", 9), fg="#8292aa", bg="#0a0c12"
        ).pack(side="right", padx=18)

        conteudo = tk.Frame(fundo, bg="#050609")
        conteudo.pack(fill="both", expand=True, padx=48, pady=32)
        conteudo.grid_columnconfigure(0, weight=1)
        conteudo.grid_columnconfigure(1, weight=1)
        conteudo.grid_rowconfigure(0, weight=1)


        esquerda = tk.Frame(
            conteudo, bg="#07090e",
            highlightbackground="#242a35", highlightthickness=1
        )
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 18))

        tk.Label(
            esquerda, text="F", font=("Consolas", 78, "bold"),
            fg=VERMELHO, bg="#07090e"
        ).pack(pady=(55, 0))

        tk.Label(
            esquerda, text="FREDDY",
            font=("Consolas", 30, "bold"), fg=BRANCO, bg="#07090e"
        ).pack()

        tk.Label(
            esquerda, text="SECURITY SYSTEM",
            font=("Consolas", 13, "bold"), fg=VERMELHO, bg="#07090e"
        ).pack(pady=(4, 8))

        tk.Label(
            esquerda, text="MONITORAMENTO EM TEMPO REAL",
            font=("Consolas", 9), fg="#8292aa", bg="#07090e"
        ).pack(pady=(0, 38))

        tk.Frame(esquerda, bg="#242a35", height=1).pack(fill="x", padx=38)

        for simbolo, titulo, detalhe in (
            ("◉", "CÂMERA AO VIVO", "MONITORAMENTO CONTÍNUO"),
            ("◇", "SEGURANÇA 24 HORAS", "ACESSO PROTEGIDO"),
            ("⚙", "TECNOLOGIA E CONTROLE", "SISTEMA INTEGRADO"),
        ):
            linha = tk.Frame(esquerda, bg="#07090e")
            linha.pack(fill="x", padx=38, pady=14)
            tk.Label(
                linha, text=simbolo, font=("Segoe UI Symbol", 22),
                fg=VERMELHO, bg="#07090e", width=3
            ).pack(side="left")
            textos = tk.Frame(linha, bg="#07090e")
            textos.pack(side="left", padx=8)
            tk.Label(
                textos, text=titulo, font=("Consolas", 9, "bold"),
                fg=BRANCO, bg="#07090e", anchor="w"
            ).pack(anchor="w")
            tk.Label(
                textos, text=detalhe, font=("Consolas", 7),
                fg="#8292aa", bg="#07090e", anchor="w"
            ).pack(anchor="w", pady=(3, 0))

        direita = tk.Frame(
            conteudo, bg="#090c12",
            highlightbackground=VERMELHO, highlightthickness=1
        )
        direita.grid(row=0, column=1, sticky="nsew", padx=(18, 0))

        tk.Label(
            direita, text="▣", font=("Segoe UI Symbol", 38),
            fg=VERMELHO, bg="#090c12"
        ).pack(pady=(45, 0))

        titulo = tk.Frame(direita, bg="#090c12")
        titulo.pack(pady=(8, 0))
        tk.Label(
            titulo, text="ACESSO AO ", font=("Consolas", 20),
            fg=BRANCO, bg="#090c12"
        ).pack(side="left")
        tk.Label(
            titulo, text="SISTEMA", font=("Consolas", 20),
            fg=VERMELHO, bg="#090c12"
        ).pack(side="left")

        tk.Label(
            direita, text="Informe suas credenciais para continuar.",
            font=("Segoe UI", 10), fg="#8292aa", bg="#090c12"
        ).pack(pady=(10, 30))

        formulario = tk.Frame(direita, bg="#090c12")
        formulario.pack(fill="x", padx=34)

        tk.Label(
            formulario, text="USUÁRIO", font=("Consolas", 9, "bold"),
            fg="#cbd2df", bg="#090c12"
        ).pack(anchor="w", pady=(0, 6))

        usuario_box = tk.Frame(
            formulario, bg="#0c111a",
            highlightbackground="#39475b", highlightthickness=1
        )
        usuario_box.pack(fill="x", pady=(0, 18))
        tk.Label(
            usuario_box, text="♙", font=("Segoe UI Symbol", 18),
            fg="#cbd2df", bg="#0c111a"
        ).pack(side="left", padx=(12, 8), pady=5)

        self.entrada_usuario = tk.Entry(
            usuario_box, font=("Segoe UI", 12), bg="#0c111a",
            fg=BRANCO, insertbackground=BRANCO, relief="flat",
            bd=0
        )
        self.entrada_usuario.pack(
            side="left", fill="x", expand=True, ipady=11, padx=(0, 10)
        )

        tk.Label(
            formulario, text="SENHA", font=("Consolas", 9, "bold"),
            fg="#cbd2df", bg="#090c12"
        ).pack(anchor="w", pady=(0, 6))

        senha_box = tk.Frame(
            formulario, bg="#0c111a",
            highlightbackground="#39475b", highlightthickness=1
        )
        senha_box.pack(fill="x", pady=(0, 24))
        tk.Label(
            senha_box, text="♙", font=("Segoe UI Symbol", 18),
            fg="#cbd2df", bg="#0c111a"
        ).pack(side="left", padx=(12, 8), pady=5)

        self.entrada_senha = tk.Entry(
            senha_box, font=("Segoe UI", 12), show="*",
            bg="#0c111a", fg=BRANCO, insertbackground=BRANCO,
            relief="flat", bd=0
        )
        self.entrada_senha.pack(
            side="left", fill="x", expand=True, ipady=11
        )
        self.botao_olho = tk.Button(
            senha_box, text="◉", command=self.alternar_senha,
            font=("Segoe UI Symbol", 14), fg="#8292aa", bg="#0c111a",
            activebackground="#0c111a", activeforeground=BRANCO,
            relief="flat", bd=0, cursor="hand2"
        )
        self.botao_olho.pack(side="right", padx=10)

        tk.Button(
            formulario, text="⇥   E N T R A R",
            command=self.entrar, font=("Consolas", 12, "bold"),
            fg=BRANCO, bg="#d90024", activebackground="#a9001b",
            activeforeground=BRANCO, relief="flat", cursor="hand2",
            pady=14, bd=0
        ).pack(fill="x", pady=(0, 8))

        tk.Button(
            formulario, text="Esqueci minha senha",
            command=self.abrir_recuperacao, font=("Segoe UI", 9, "underline"),
            fg="#9aa8bd", bg="#090c12", activebackground="#090c12",
            activeforeground=BRANCO, relief="flat", bd=0, cursor="hand2"
        ).pack(anchor="e", pady=(0, 12))

        separador = tk.Frame(direita, bg="#090c12")
        separador.pack(fill="x", padx=34, pady=(0, 18))
        tk.Frame(separador, bg="#39475b", height=1).pack(
            side="left", fill="x", expand=True, pady=7
        )
        tk.Label(
            separador, text=" OU ", font=("Consolas", 9),
            fg="#8292aa", bg="#090c12"
        ).pack(side="left")
        tk.Frame(separador, bg="#39475b", height=1).pack(
            side="left", fill="x", expand=True, pady=7
        )

        tk.Button(
            direita, text="♙+   CADASTRAR USUÁRIO",
            command=self.abrir_cadastro, font=("Consolas", 10),
            fg=BRANCO, bg="#090c12", activebackground="#151a24",
            activeforeground=BRANCO, relief="flat",
            highlightbackground=VERMELHO, highlightthickness=1,
            cursor="hand2", pady=12
        ).pack(fill="x", padx=34)

        tk.Label(
            direita,
            text="◇  FREDDY SECURITY SYSTEM  ◇\n       PROTEGENDO O QUE IMPORTA",
            font=("Consolas", 8), fg="#65758d", bg="#090c12",
            justify="center"
        ).pack(pady=(28, 0))

        self.entrada_usuario.focus_set()

    def alternar_senha(self):
        self.mostrar_senha = not self.mostrar_senha
        self.entrada_senha.config(show="" if self.mostrar_senha else "*")

    def entrar(self):
        usuario = self.entrada_usuario.get().strip()
        senha = self.entrada_senha.get()

        if validar_login(usuario, senha):
            self.ao_entrar(usuario)
        else:
            messagebox.showerror(
                "Acesso negado",
                "Usuário ou senha incorretos.",
                parent=self.janela
            )
            self.entrada_senha.delete(0, tk.END)
            self.entrada_senha.focus_set()

    def abrir_recuperacao(self):
        janela_recuperacao = tk.Toplevel(self.janela)
        janela_recuperacao.title("RECUPERAR SENHA")
        janela_recuperacao.geometry("460x560")
        janela_recuperacao.resizable(False, False)
        janela_recuperacao.configure(bg=FUNDO)
        janela_recuperacao.transient(self.janela)
        janela_recuperacao.grab_set()

        painel = tk.Frame(
            janela_recuperacao, bg=PAINEL,
            highlightbackground=VERMELHO, highlightthickness=1
        )
        painel.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(
            painel, text="RECUPERAR SENHA",
            font=("Consolas", 17, "bold"), fg=VERMELHO, bg=PAINEL
        ).pack(pady=(20, 8))

        tk.Label(
            painel,
            text="Informe seu usuário, código de recuperação\ne escolha uma nova senha.",
            font=("Segoe UI", 9), fg="#9aa8bd", bg=PAINEL,
            justify="center"
        ).pack(pady=(0, 16))

        def campo(rotulo, esconder=False):
            tk.Label(
                painel, text=rotulo, fg=BRANCO, bg=PAINEL,
                font=("Consolas", 9)
            ).pack(anchor="w", padx=25)
            entrada = tk.Entry(
                painel, font=("Consolas", 11), bg="#151820",
                fg=BRANCO, insertbackground=BRANCO, relief="flat",
                show="*" if esconder else ""
            )
            entrada.pack(fill="x", padx=25, ipady=6, pady=(4, 10))
            return entrada

        entrada_usuario = campo("USUÁRIO")
        entrada_codigo = campo("CÓDIGO DE RECUPERAÇÃO")
        entrada_nova_senha = campo("NOVA SENHA (MÍNIMO 8 CARACTERES)", True)
        entrada_confirmacao = campo("CONFIRMAR NOVA SENHA", True)

        def redefinir():
            usuario = entrada_usuario.get().strip()
            codigo = entrada_codigo.get().strip().upper()
            nova_senha = entrada_nova_senha.get()
            confirmacao = entrada_confirmacao.get()

            if not usuario or not codigo or not nova_senha or not confirmacao:
                messagebox.showerror(
                    "Recuperar senha", "Preencha todos os campos.",
                    parent=janela_recuperacao
                )
                return
            if len(nova_senha) < 8:
                messagebox.showerror(
                    "Recuperar senha", "A nova senha precisa ter pelo menos 8 caracteres.",
                    parent=janela_recuperacao
                )
                return
            if nova_senha != confirmacao:
                messagebox.showerror(
                    "Recuperar senha", "As senhas não são iguais.",
                    parent=janela_recuperacao
                )
                return

            try:
                with conectar_banco() as conexao:
                    registro = conexao.execute(
                        """SELECT id, recovery_salt, recovery_hash
                           FROM usuarios WHERE usuario = ?""",
                        (usuario,)
                    ).fetchone()

                    if not registro or not registro[1] or not registro[2]:
                        valido = False
                    else:
                        _, codigo_hash = gerar_senha(codigo, registro[1])
                        valido = secrets.compare_digest(codigo_hash, registro[2])

                    if not valido:
                        messagebox.showerror(
                            "Recuperar senha",
                            "Usuário ou código de recuperação inválido. "
                            "Confira os dados e tente novamente.",
                            parent=janela_recuperacao
                        )
                        return

                    novo_salt, novo_hash = gerar_senha(nova_senha)
                    conexao.execute(
                        "UPDATE usuarios SET salt = ?, senha = ?, recovery_salt = NULL, recovery_hash = NULL WHERE id = ?",
                        (novo_salt, novo_hash, registro[0])
                    )

                messagebox.showinfo(
                    "Recuperar senha",
                    "Senha redefinida com sucesso! Você já pode entrar com a nova senha.",
                    parent=janela_recuperacao
                )
                janela_recuperacao.destroy()
                self.entrada_usuario.delete(0, tk.END)
                self.entrada_usuario.insert(0, usuario)
                self.entrada_senha.delete(0, tk.END)
                self.entrada_senha.focus_set()
            except sqlite3.Error as erro:
                messagebox.showerror(
                    "Erro", f"Não foi possível redefinir a senha: {erro}",
                    parent=janela_recuperacao
                )

        tk.Button(
            painel, text="REDEFINIR SENHA", command=redefinir,
            font=("Consolas", 10, "bold"), fg=BRANCO, bg=VERMELHO,
            activebackground="#aa0000", activeforeground=BRANCO,
            relief="flat", cursor="hand2", pady=9
        ).pack(fill="x", padx=25, pady=(2, 12))

    def abrir_cadastro(self):
        janela_cadastro = tk.Toplevel(self.janela)
        janela_cadastro.title("CADASTRAR USUÁRIO")
        janela_cadastro.geometry("420x410")
        janela_cadastro.resizable(False, False)
        janela_cadastro.configure(bg=FUNDO)
        janela_cadastro.transient(self.janela)
        janela_cadastro.grab_set()

        painel = tk.Frame(
            janela_cadastro, bg=PAINEL,
            highlightbackground=VERMELHO, highlightthickness=1
        )
        painel.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            painel, text="NOVO USUÁRIO", font=("Consolas", 17, "bold"),
            fg=VERMELHO, bg=PAINEL
        ).pack(pady=(22, 18))

        tk.Label(
            painel, text="Usuário", fg=BRANCO, bg=PAINEL,
            font=("Consolas", 9)
        ).pack(anchor="w", padx=28)
        entrada_usuario = tk.Entry(
            painel, font=("Consolas", 11), bg="#151820",
            fg=BRANCO, insertbackground=BRANCO, relief="flat"
        )
        entrada_usuario.pack(fill="x", padx=28, ipady=7, pady=(4, 12))

        tk.Label(
            painel, text="Senha (mínimo 8 caracteres)", fg=BRANCO,
            bg=PAINEL, font=("Consolas", 9)
        ).pack(anchor="w", padx=28)
        entrada_senha = tk.Entry(
            painel, font=("Consolas", 11), show="*", bg="#151820",
            fg=BRANCO, insertbackground=BRANCO, relief="flat"
        )
        entrada_senha.pack(fill="x", padx=28, ipady=7, pady=(4, 12))

        tk.Label(
            painel, text="Confirmar senha", fg=BRANCO, bg=PAINEL,
            font=("Consolas", 9)
        ).pack(anchor="w", padx=28)
        entrada_confirmacao = tk.Entry(
            painel, font=("Consolas", 11), show="*", bg="#151820",
            fg=BRANCO, insertbackground=BRANCO, relief="flat"
        )
        entrada_confirmacao.pack(fill="x", padx=28, ipady=7, pady=(4, 16))

        def salvar():
            usuario = entrada_usuario.get().strip()
            senha = entrada_senha.get()
            confirmacao = entrada_confirmacao.get()

            if senha != confirmacao:
                messagebox.showerror(
                    "Cadastro", "As senhas não são iguais.",
                    parent=janela_cadastro
                )
                return

            sucesso, mensagem = cadastrar_usuario(usuario, senha)
            if sucesso:
                messagebox.showinfo("Cadastro", mensagem, parent=janela_cadastro)
                self.entrada_usuario.delete(0, tk.END)
                self.entrada_usuario.insert(0, usuario)
                self.entrada_senha.delete(0, tk.END)
                self.entrada_senha.focus_set()
                janela_cadastro.destroy()
            else:
                messagebox.showerror("Cadastro", mensagem, parent=janela_cadastro)

        tk.Button(
            painel, text="SALVAR USUÁRIO", command=salvar,
            font=("Consolas", 10, "bold"), fg=BRANCO, bg=VERMELHO,
            activebackground="#aa0000", activeforeground=BRANCO,
            relief="flat", cursor="hand2", pady=10
        ).pack(fill="x", padx=28)


class FreddySecurity:

    def __init__(self, janela):
        self.janela = janela
        self.tema_claro = self.carregar_tema()
        self.janelas_auxiliares = []
        self.movimento_ativo = False
        self.inicio_movimento_candidato = None
        self.ultimo_movimento_detectado = 0.0
        self.arquivos_gravacoes = []
        self.janela.title('FREDDY SECURITY SYSTEM')
        self.janela.geometry('1250x760')
        self.janela.minsize(900, 600)
        self.janela.configure(bg=FUNDO)
        self.camera = None
        self.frame = None
        self.imagem_tk = None
        self.gravando = False
        self.gravacao_automatica = False
        self.fim_gravacao_automatica = None
        self.video = None
        self.nome_video = None
        self.logo_tk = None
        self.arduino = None
        self.servidor_web = None
        self.sensor_arduino = False
        self.presenca_camera = False
        self.detector_rosto = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.estado_enviado = None
        self.criar_interface()
        self.iniciar_servidor_web()
        if self.tema_claro:
            self.aplicar_tema(self.janela)
        self.conectar_arduino()
        self.conectar_camera()
        self.janela.protocol('WM_DELETE_WINDOW', self.fechar)
        self.atualizar_imagem()
        self.atualizar_horario()

    def criar_interface(self):
        topo = tk.Frame(self.janela, bg=PAINEL, highlightbackground=BORDA, highlightthickness=1)
        topo.pack(fill='x', padx=14, pady=12)
        tk.Label(topo, text='F', font=('Consolas', 28, 'bold'), fg=VERMELHO, bg='#210810', width=3, pady=7).pack(side='left', padx=8, pady=8)
        titulo = tk.Frame(topo, bg=PAINEL)
        titulo.pack(side='left', padx=8)
        tk.Label(titulo, text='FREDDY ', font=('Consolas', 22, 'bold'), fg=BRANCO, bg=PAINEL).pack(side='left')
        tk.Label(titulo, text='SECURITY SYSTEM', font=('Consolas', 22, 'bold'), fg=VERMELHO, bg=PAINEL).pack(side='left')
        tk.Label(titulo, text='MONITORAMENTO EM TEMPO REAL', font=('Consolas', 9), fg=CINZA, bg=PAINEL).pack(anchor='w')
        corpo = tk.Frame(self.janela, bg=FUNDO)
        corpo.pack(fill='both', expand=True, padx=14, pady=4)
        corpo.grid_columnconfigure(0, weight=0, minsize=180)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_columnconfigure(2, weight=0, minsize=205)
        corpo.grid_rowconfigure(0, weight=1)
        menu = tk.Frame(corpo, bg=PAINEL, highlightbackground=BORDA, highlightthickness=1)
        menu.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        tk.Label(menu, text='FREDDY', font=('Consolas', 22, 'bold'), fg=VERMELHO, bg=PAINEL).pack(pady=(28, 3))
        tk.Label(menu, text='HOME SERVICE 2050', font=('Consolas', 8), fg=CINZA, bg=PAINEL).pack(pady=(0, 35))
        self.carregar_logo(menu)
        self.botao(menu, '▷  GRAVAÇÕES', self.gravacoes)
        self.botao(menu, '▣  ACESSO NO CELULAR', self.mostrar_acesso_celular)
        self.botao(menu, '⚙  CONFIGURAÇÕES', self.configuracoes)
        self.botao(menu, 'ⓘ  SOBRE', self.sobre)
        centro = tk.Frame(corpo, bg=FUNDO)
        centro.grid(row=0, column=1, sticky='nsew', padx=(0, 10))
        centro.grid_rowconfigure(0, weight=1)
        centro.grid_columnconfigure(0, weight=1)
        monitor = tk.Frame(centro, bg='#000000', highlightbackground=VERMELHO, highlightthickness=2)
        monitor.grid(row=0, column=0, sticky='nsew')
        monitor.grid_rowconfigure(1, weight=1)
        monitor.grid_columnconfigure(0, weight=1)
        barra = tk.Frame(monitor, bg='#000000')
        barra.grid(row=0, column=0, sticky='ew', padx=12, pady=10)
        tk.Label(barra, text='● CÂMERA AO VIVO', font=('Consolas', 10, 'bold'), fg=BRANCO, bg='#000000').pack(side='left')
        tk.Label(barra, text='LIVE', font=('Consolas', 10, 'bold'), fg=VERMELHO, bg='#000000').pack(side='right')
        self.tela = tk.Label(monitor, text='', bg='#030407', fg=CINZA, font=('Consolas', 15), compound='center')
        self.tela.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 10))
        inferior = tk.Frame(centro, bg=PAINEL)
        inferior.grid(row=1, column=0, sticky='ew', pady=(10, 0))
        self.status_gravacao = tk.Label(inferior, text='● GRAVAÇÃO INATIVA', font=('Consolas', 9), fg=CINZA, bg=PAINEL)
        self.status_gravacao.pack(side='left', padx=12, pady=15)
        self.relogio = tk.Label(inferior, text='00:00:00', font=('Consolas', 13, 'bold'), fg=BRANCO, bg=PAINEL)
        self.relogio.pack(side='right', padx=12)
        lateral = tk.Frame(corpo, bg=PAINEL, highlightbackground=BORDA, highlightthickness=1)
        lateral.grid(row=0, column=2, sticky='nsew')
        tk.Label(lateral, text='STATUS DO SISTEMA', font=('Consolas', 10, 'bold'), fg=BRANCO, bg=PAINEL).pack(anchor='w', padx=12, pady=(18, 15))
        self.status_camera = self.linha(lateral, 'Câmera:', 'Aguardando')
        self.linha(lateral, 'Rede:', 'Local')
        self.linha(lateral, 'Modo:', 'Monitoramento')
        tk.Frame(lateral, bg=BORDA, height=1).pack(fill='x', padx=10, pady=15)
        tk.Label(lateral, text='POSIÇÃO DA CÂMERA', font=('Consolas', 10), fg=BRANCO, bg=PAINEL).pack(anchor='w', padx=12)
        tk.Label(lateral, text='◎', font=('Consolas', 75), fg=VERMELHO, bg=PAINEL).pack(pady=10)
        tk.Label(lateral, text='OLHO DIREITO', font=('Consolas', 10), fg=BRANCO, bg=PAINEL).pack(pady=(0, 20))
        tk.Button(lateral, text='SALVAR FOTO', command=self.capturar, font=('Consolas', 10, 'bold'), fg=BRANCO, bg='#4a0b15', activebackground=VERMELHO, relief='flat', cursor='hand2', pady=12).pack(fill='x', padx=12, pady=5)
        tk.Button(lateral, text='INICIAR GRAVAÇÃO', command=self.iniciar_gravacao, font=('Consolas', 9), fg=BRANCO, bg='#20232b', activebackground='#20232b', relief='flat', cursor='hand2', pady=12).pack(fill='x', padx=12, pady=5)
        tk.Button(lateral, text='PARAR GRAVAÇÃO', command=self.parar_gravacao, font=('Consolas', 9), fg=BRANCO, bg=VERMELHO, activebackground='#aa0000', relief='flat', cursor='hand2', pady=12).pack(fill='x', padx=12, pady=5)
        self.rodape = tk.Label(self.janela, text='SISTEMA INICIADO', font=('Consolas', 9), fg=CINZA, bg=PAINEL, anchor='w', padx=15, pady=8)
        self.rodape.pack(fill='x', padx=14, pady=10)

    def carregar_logo(self, pai):
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freddy.logo.png.jpeg')
        if not os.path.exists(caminho):
            print(f'Logo não encontrada: {caminho}')
            return
        try:
            imagem = Image.open(caminho).convert('RGBA')
            imagem.thumbnail((145, 145))
            self.logo_tk = ImageTk.PhotoImage(imagem)
            tk.Label(pai, image=self.logo_tk, bg=PAINEL).pack(pady=15)
        except Exception as erro:
            print(f'Erro ao carregar a logo: {erro}')

    def botao(self, pai, texto, comando):
        tk.Button(pai, text=texto, command=comando, anchor='w', padx=12, pady=14, font=('Consolas', 9), fg=BRANCO, bg=PAINEL, activebackground=VERMELHO, activeforeground=BRANCO, relief='flat', cursor='hand2').pack(fill='x', padx=7, pady=3)

    def iniciar_servidor_web(self):
        try:
            self.servidor_web = ServidorGravacoes(("0.0.0.0", PORTA_WEB), ManipuladorGravacoes)
            threading.Thread(target=self.servidor_web.serve_forever, daemon=True).start()
        except OSError as erro:
            self.servidor_web = None
            print(f"Não foi possível iniciar o acesso pelo celular: {erro}")

    def mostrar_acesso_celular(self):
        if self.servidor_web is None:
            messagebox.showerror(
                "Acesso pelo celular",
                f"Não foi possível iniciar a página. Talvez a porta {PORTA_WEB} já esteja sendo usada."
            )
            return
        endereco = ""
        try:
            with urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as resposta:
                tunel = json.loads(resposta.read().decode("utf-8"))
            endereco = next(
                (item.get("public_url", "") for item in tunel.get("tunnels", [])
                 if item.get("public_url", "").startswith("https://")),
                ""
            )
        except (OSError, ValueError, KeyError):
            pass
        if not endereco:
            messagebox.showinfo(
                "Acesso pelo ngrok",
                "O túnel ngrok ainda não está ativo. Com o Freddy Security aberto, abra outra janela "
                "do PowerShell e execute:\n\n"
                "ngrok http 8765\n\n"
                "Troque usuário e senha por valores seus, mantenha essa janela aberta e clique "
                "novamente em 'Acesso no celular'."
            )
            return
        messagebox.showinfo(
            "Acesso pelo ngrok",
            "Abra este endereço no navegador do celular e informe o usuário e a senha do ngrok:\n\n"
            f"{endereco}\n\n"
            "Na página, toque em 'Assistir' para ver sem baixar ou em 'Baixar' para salvar o vídeo. "
            "Deixe o computador, o Freddy Security "
            "e a janela do ngrok ligados."
        )

    def linha(self, pai, nome, valor):
        linha = tk.Frame(pai, bg=PAINEL)
        linha.pack(fill='x', padx=12, pady=6)
        tk.Label(linha, text=nome, font=('Consolas', 8), fg=CINZA, bg=PAINEL).pack(side='left')
        resultado = tk.Label(linha, text=valor, font=('Consolas', 8), fg=VERDE, bg=PAINEL)
        resultado.pack(side='right')
        return resultado

    def conectar_arduino(self):
        try:
            self.arduino = serial.Serial(PORTA_ARDUINO, BAUD_RATE, timeout=0.01)
            time.sleep(2)
            self.arduino.reset_input_buffer()
            self.rodape.config(text=f'ARDUINO CONECTADO EM {PORTA_ARDUINO}')
        except (serial.SerialException, OSError) as erro:
            self.arduino = None
            self.rodape.config(text=f'ARDUINO DESCONECTADO | Confira {PORTA_ARDUINO}')
            print(f'Não foi possível conectar ao Arduino: {erro}')

    def ler_arduino(self):
        if self.arduino is None or not self.arduino.is_open:
            return
        try:
            while self.arduino.in_waiting:
                mensagem = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                if mensagem == 'SENSOR=1':
                    self.sensor_arduino = True
                elif mensagem == 'SENSOR=0':
                    self.sensor_arduino = False
        except (serial.SerialException, OSError) as erro:
            print(f'Erro lendo o Arduino: {erro}')
            self.sensor_arduino = False

    def enviar_comando_arduino(self, movimento):
        if self.arduino is None or not self.arduino.is_open:
            return
        comando = 'MOVIMENTO' if movimento else 'NORMAL'
        if comando == self.estado_enviado:
            return
        try:
            self.arduino.write((comando + '\n').encode('utf-8'))
            self.estado_enviado = comando
        except (serial.SerialException, OSError) as erro:
            print(f'Erro enviando comando ao Arduino: {erro}')

    def detectar_presenca_camera(self, frame):
        if self.detector_rosto.empty():
            self.presenca_camera = False
            return False
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cinza = cv2.resize(cinza, None, fx=0.5, fy=0.5)
        rostos = self.detector_rosto.detectMultiScale(
            cinza,
            scaleFactor=1.1,
            minNeighbors=6,
            minSize=(40, 40)
        )
        self.presenca_camera = len(rostos) > 0
        return self.presenca_camera

    def conectar_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        self.camera = cv2.VideoCapture(CAMERA_ID, cv2.CAP_DSHOW)
        if self.camera.isOpened():
            self.status_camera.config(text='Conectada', fg=VERDE)
            self.rodape.config(text='WEBCAM CONECTADA | SISTEMA ATIVO')
        else:
            self.camera.release()
            self.camera = None
            self.status_camera.config(text='Sem sinal', fg=VERMELHO)
            self.tela.config(image='', text='\n\nSEM SINAL\n\nAGUARDANDO WEBCAM...\n\nCÂMERA 01 | OFFLINE')
            self.rodape.config(text='MODO DE TESTE | CONECTE A WEBCAM')

    def atualizar_imagem(self):
        self.ler_arduino()
        if self.camera is not None and self.camera.isOpened():
            ok, frame = self.camera.read()
            if ok:
                self.frame = frame.copy()
                self.detectar_presenca_camera(frame)
                if self.gravando and self.video is not None:
                    self.video.write(frame)
                frame_exibido = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame_exibido, cv2.COLOR_BGR2RGB)
                imagem = Image.fromarray(rgb)
                largura = max(self.tela.winfo_width(), 320)
                altura = max(self.tela.winfo_height(), 240)
                imagem.thumbnail((largura, altura))
                self.imagem_tk = ImageTk.PhotoImage(imagem)
                self.tela.config(image=self.imagem_tk, text='')
            else:
                self.presenca_camera = False
        else:
            self.presenca_camera = False
        if (self.gravacao_automatica and self.fim_gravacao_automatica is not None
                and time.monotonic() >= self.fim_gravacao_automatica):
            self.finalizar_gravacao()
        sinal_movimento = self.sensor_arduino or self.presenca_camera
        agora = time.monotonic()
        estado_anterior = self.movimento_ativo

        if sinal_movimento:
            if self.inicio_movimento_candidato is None:
                self.inicio_movimento_candidato = agora
            self.ultimo_movimento_detectado = agora
            if agora - self.inicio_movimento_candidato >= 0.35:
                self.movimento_ativo = True
        else:
            self.inicio_movimento_candidato = None
            if self.movimento_ativo and agora - self.ultimo_movimento_detectado >= 0.5:
                self.movimento_ativo = False

        if self.movimento_ativo and not estado_anterior:
            self.registrar_movimento()
            self.iniciar_gravacao(automatica=True)
        self.enviar_comando_arduino(self.movimento_ativo)
        self.janela.after(30, self.atualizar_imagem)

    def atualizar_horario(self):
        self.relogio.config(text=datetime.now().strftime('%H:%M:%S'))
        self.janela.after(1000, self.atualizar_horario)

    def capturar(self):
        if self.frame is None:
            messagebox.showinfo('Freddy Security', 'Aguardando a webcam para capturar uma foto.')
            return
        nome = os.path.join(PASTA_PROJETO, datetime.now().strftime('freddy_%Y%m%d_%H%M%S.jpg'))
        if cv2.imwrite(nome, self.frame):
            self.rodape.config(text=f'FOTO SALVA: {nome}')
        else:
            messagebox.showerror('Erro', 'Não foi possível salvar a foto.')

    def iniciar_gravacao(self, automatica=False):
        if self.gravando:
            return
        if self.camera is None or self.frame is None:
            if not automatica:
                messagebox.showinfo('Freddy Security', 'Conecte a webcam antes de iniciar a gravação.')
            return
        altura, largura = self.frame.shape[:2]
        self.nome_video = os.path.join(PASTA_PROJETO, datetime.now().strftime('freddy_%Y%m%d_%H%M%S.avi'))
        codec = cv2.VideoWriter_fourcc(*'MJPG')
        self.video = cv2.VideoWriter(self.nome_video, codec, 20.0, (largura, altura))
        if not self.video.isOpened():
            self.video.release()
            self.video = None
            if not automatica:
                messagebox.showerror('Erro', 'Não foi possível iniciar a gravação.')
            else:
                print('Não foi possível iniciar a gravação automática.')
            return
        self.gravando = True
        self.gravacao_automatica = automatica
        self.fim_gravacao_automatica = time.monotonic() + 5 if automatica else None
        self.status_gravacao.config(text='● GRAVAÇÃO ATIVA', fg=VERMELHO)
        self.rodape.config(text=f'GRAVANDO: {self.nome_video}')

    def parar_gravacao(self):
        if not self.gravando:
            messagebox.showinfo('Freddy Security', 'Não existe uma gravação em andamento.')
            return
        nome_video = self.nome_video
        automatica = self.gravacao_automatica
        self.finalizar_gravacao()
        if not automatica:
            messagebox.showinfo('Freddy Security', f'Gravação encerrada e salva!\n\n{nome_video}')

    def finalizar_gravacao(self):
        if not self.gravando:
            return
        self.gravando = False
        if self.video is not None:
            self.video.release()
            self.video = None
        self.gravacao_automatica = False
        self.fim_gravacao_automatica = None
        self.status_gravacao.config(text='● GRAVAÇÃO INATIVA', fg=CINZA)
        self.rodape.config(text=f'GRAVAÇÃO SALVA: {self.nome_video}')
        if hasattr(self, 'lista_gravacoes') and self.lista_gravacoes.winfo_exists():
            self.atualizar_lista_gravacoes()

    def abrir_camera(self):
        if self.camera is None or not self.camera.isOpened():
            self.conectar_camera()
        else:
            self.rodape.config(text='MONITORAMENTO EM TEMPO REAL')

    def carregar_tema(self):
        try:
            with open(ARQUIVO_TEMA, "r", encoding="utf-8") as arquivo:
                return json.load(arquivo).get("tema") == "claro"
        except (OSError, ValueError, AttributeError):
            return False

    def salvar_tema(self):
        try:
            with open(ARQUIVO_TEMA, "w", encoding="utf-8") as arquivo:
                json.dump({"tema": "claro" if self.tema_claro else "escuro"}, arquivo)
        except OSError as erro:
            print(f"N\u00e3o foi poss\u00edvel salvar o tema: {erro}")

    def registrar_movimento(self):
        origens = []
        if self.presenca_camera:
            origens.append("c\u00e2mera")
        if self.sensor_arduino:
            origens.append("sensor")
        horario = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        try:
            with open(ARQUIVO_MOVIMENTOS, "a", encoding="utf-8") as arquivo:
                arquivo.write(f"{horario} - Presen\u00e7a detectada ({' + '.join(origens)})\n")
            self.rodape.config(text=f"PRESEN\u00c7A DETECTADA | {horario}")
        except OSError as erro:
            print(f"N\u00e3o foi poss\u00edvel registrar o movimento: {erro}")

    def atualizar_lista_gravacoes(self):
        self.lista_gravacoes.delete(0, tk.END)
        extensoes = (".jpg", ".jpeg", ".png", ".avi", ".mp4", ".mov")
        arquivos = []
        try:
            for nome in os.listdir(PASTA_PROJETO):
                caminho = os.path.join(PASTA_PROJETO, nome)
                if nome.lower().startswith("freddy_") and nome.lower().endswith(extensoes) and os.path.isfile(caminho):
                    arquivos.append(caminho)
        except OSError as erro:
            messagebox.showerror("Grava\u00e7\u00f5es", f"N\u00e3o foi poss\u00edvel listar os arquivos: {erro}", parent=self.janela_gravacoes)
            return
        self.arquivos_gravacoes = sorted(arquivos, key=os.path.getmtime, reverse=True)
        for caminho in self.arquivos_gravacoes:
            self.lista_gravacoes.insert(tk.END, os.path.basename(caminho))
        if not self.arquivos_gravacoes:
            self.lista_gravacoes.insert(tk.END, "Nenhuma foto ou grava\u00e7\u00e3o encontrada.")

    def abrir_gravacao_selecionada(self, evento=None):
        selecao = self.lista_gravacoes.curselection()
        if not selecao or selecao[0] >= len(self.arquivos_gravacoes):
            return
        caminho = self.arquivos_gravacoes[selecao[0]]
        try:
            os.startfile(caminho)
        except (OSError, AttributeError) as erro:
            messagebox.showerror("Grava\u00e7\u00f5es", f"N\u00e3o foi poss\u00edvel abrir o arquivo: {erro}", parent=self.janela_gravacoes)

    def abrir_pasta_gravacoes(self):
        try:
            os.startfile(PASTA_PROJETO)
        except (OSError, AttributeError) as erro:
            messagebox.showerror("Grava\u00e7\u00f5es", f"N\u00e3o foi poss\u00edvel abrir a pasta: {erro}", parent=self.janela_gravacoes)

    def movimentos(self):
        try:
            with open(ARQUIVO_MOVIMENTOS, "r", encoding="utf-8") as arquivo:
                linhas = arquivo.readlines()
        except FileNotFoundError:
            linhas = []
        except OSError as erro:
            messagebox.showerror("Movimentos", f"N\u00e3o foi poss\u00edvel ler o registro: {erro}", parent=self.janela_gravacoes)
            return
        if not linhas:
            texto = "Ainda n\u00e3o h\u00e1 presen\u00e7as registradas."
        else:
            texto = "\n".join(linha.rstrip() for linha in linhas[-20:])
        messagebox.showinfo("Presen\u00e7as recentes", texto, parent=self.janela_gravacoes)

    def gravacoes(self):
        if hasattr(self, "janela_gravacoes") and self.janela_gravacoes.winfo_exists():
            self.janela_gravacoes.lift()
            self.atualizar_lista_gravacoes()
            return
        self.janela_gravacoes = tk.Toplevel(self.janela)
        self.janelas_auxiliares.append(self.janela_gravacoes)
        self.janela_gravacoes.title("Grava\u00e7\u00f5es e fotos")
        self.janela_gravacoes.geometry("520x410")
        self.janela_gravacoes.minsize(420, 300)
        fundo = "#ffffff" if self.tema_claro else FUNDO
        painel = "#f0f2f5" if self.tema_claro else PAINEL
        texto = "#20242c" if self.tema_claro else BRANCO
        self.janela_gravacoes.configure(bg=fundo)
        tk.Label(self.janela_gravacoes, text="FOTOS E GRAVA\u00c7\u00d5ES", font=("Consolas", 14, "bold"),
                 fg=VERMELHO, bg=fundo).pack(pady=(16, 10))
        area = tk.Frame(self.janela_gravacoes, bg=fundo)
        area.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        rolagem = tk.Scrollbar(area)
        rolagem.pack(side="right", fill="y")
        self.lista_gravacoes = tk.Listbox(area, font=("Consolas", 10), bg=painel, fg=texto,
                                          selectbackground=VERMELHO, selectforeground=BRANCO,
                                          yscrollcommand=rolagem.set, relief="flat", activestyle="none")
        self.lista_gravacoes.pack(side="left", fill="both", expand=True)
        rolagem.config(command=self.lista_gravacoes.yview)
        self.lista_gravacoes.bind("<Double-Button-1>", self.abrir_gravacao_selecionada)
        botoes = tk.Frame(self.janela_gravacoes, bg=fundo)
        botoes.pack(fill="x", padx=16, pady=(0, 16))
        for rotulo, comando in (("Abrir", self.abrir_gravacao_selecionada),
                                ("Atualizar", self.atualizar_lista_gravacoes),
                                ("Presen\u00e7as", self.movimentos),
                                ("Abrir pasta", self.abrir_pasta_gravacoes)):
            tk.Button(botoes, text=rotulo, command=comando, font=("Segoe UI", 9),
                      fg=texto, bg=painel, activebackground=VERMELHO,
                      activeforeground=BRANCO, relief="flat", cursor="hand2",
                      padx=8, pady=7).pack(side="left", expand=True, padx=3)
        self.atualizar_lista_gravacoes()

    def aplicar_tema(self, widget):
        escuro_para_claro = {
            "#050609": "#f4f5f7", "#0a0c12": "#f0f2f5",
            "#07090e": "#ffffff", "#090c12": "#ffffff",
            "#0c0e13": "#f0f2f5", "#0c111a": "#f5f6f8",
            "#151820": "#f5f6f8", "#151a24": "#e8ebf0",
            "#20232b": "#e2e5ea", "#210810": "#f9e8eb",
            "#242a35": "#d6dae1", "#282b35": "#d6dae1",
            "#39475b": "#c5cbd5", "#4a0b15": "#f4dfe3",
            "#000000": "#e9ebef", "#030407": "#e9ebef",
            "#eeeeee": "#20242c", "#cbd2df": "#343b48",
            "#9aa8bd": "#566174", "#858b98": "#626b78",
            "#8292aa": "#536176", "#65758d": "#5c687a",
            "#a9001b": "#8f0018", "#d90024": "#c90022",
        }
        claro_para_escuro = {claro: escuro for escuro, claro in escuro_para_claro.items()}
        mapa = escuro_para_claro if self.tema_claro else claro_para_escuro
        for opcao in ("bg", "fg", "highlightbackground", "activebackground",
                      "activeforeground", "insertbackground", "highlightcolor"):
            try:
                atual = widget.cget(opcao)
                novo = mapa.get(str(atual).lower())
                if novo:
                    widget.configure(**{opcao: novo})
            except (tk.TclError, TypeError):
                pass
        for filho in widget.winfo_children():
            self.aplicar_tema(filho)

    def alternar_tema(self):
        self.tema_claro = not self.tema_claro
        self.salvar_tema()
        self.aplicar_tema(self.janela)
        for auxiliar in self.janelas_auxiliares:
            try:
                if auxiliar.winfo_exists():
                    self.aplicar_tema(auxiliar)
            except tk.TclError:
                pass
        if hasattr(self, "janela_config") and self.janela_config.winfo_exists():
            self.aplicar_tema(self.janela_config)
        if hasattr(self, "botao_tema"):
            texto = "Ativar tema escuro" if self.tema_claro else "Ativar tema claro"
            self.botao_tema.config(text=texto)

    def configuracoes(self):
        if hasattr(self, "janela_config") and self.janela_config.winfo_exists():
            self.janela_config.lift()
            return

        self.janela_config = tk.Toplevel(self.janela)
        self.janela_config.title("Configura\u00e7\u00f5es")
        self.janela_config.geometry("390x260")
        self.janela_config.resizable(False, False)
        self.janela_config.transient(self.janela)
        fundo = "#ffffff" if self.tema_claro else FUNDO
        painel = "#f0f2f5" if self.tema_claro else PAINEL
        texto = "#20242c" if self.tema_claro else BRANCO
        secundario = "#536176" if self.tema_claro else CINZA
        self.janela_config.configure(bg=fundo)

        tk.Label(self.janela_config, text="CONFIGURA\u00c7\u00d5ES", font=("Consolas", 16, "bold"),
                 fg=VERMELHO, bg=fundo).pack(pady=(22, 14))
        tk.Label(self.janela_config, text="Apar\u00eancia", font=("Consolas", 10, "bold"),
                 fg=secundario, bg=fundo).pack(pady=(0, 8))
        texto_botao = "Ativar tema escuro" if self.tema_claro else "Ativar tema claro"
        self.botao_tema = tk.Button(self.janela_config, text=texto_botao,
                                    command=self.alternar_tema, font=("Segoe UI", 10),
                                    fg=texto, bg=painel, activebackground="#e2e5ea" if self.tema_claro else "#20232b",
                                    activeforeground=texto, relief="flat", cursor="hand2", padx=18, pady=9)
        self.botao_tema.pack()

    def sobre(self):
        messagebox.showinfo('Sobre', 'FREDDY SECURITY SYSTEM\nSistema de monitoramento com câmera e detecção de movimento, integrado ao Arduino para ajudar a manter o ambiente protegido..')

    def fechar(self):
        if self.servidor_web is not None:
            self.servidor_web.shutdown()
            self.servidor_web.server_close()
            self.servidor_web = None
        if self.video is not None:
            self.video.release()
            self.video = None
            self.gravando = False
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        if self.arduino is not None:
            try:
                if self.arduino.is_open:
                    self.arduino.write(b'NORMAL\n')
                    self.arduino.close()
            except (serial.SerialException, OSError):
                pass
        self.janela.destroy()
if __name__ == '__main__':
    conectar_banco()
    janela = tk.Tk()

    def abrir_monitoramento(usuario):
        for componente in janela.winfo_children():
            componente.destroy()
        janela.title('FREDDY SECURITY SYSTEM')
        janela.geometry('1250x760')
        janela.minsize(900, 600)
        FreddySecurity(janela)
    TelaLogin(janela, abrir_monitoramento)
    janela.mainloop()
