import socket
import time


# 字符串编码为字节流
def string_to_byte_stream(s:str,useSigned=False):
    utf8_bytes = s.encode('utf-8')
    length = len(utf8_bytes)
    if useSigned:
        length = -length
    length_bytes = length.to_bytes(4, 'little',signed=True)
    byte_stream = length_bytes + utf8_bytes
    return byte_stream

# 强制接收固定数目的信息
def RecvNums(sock:socket.socket,n:int):
    data = b''
    while len(data) < n:
        # 尝试接收剩余的字节数
        packet = sock.recv(n - len(data))
        if not packet:
            # 如果连接已经关闭，则抛出异常
            raise RuntimeError("socket连接崩了")
        # 将接收到的数据追加到总数据中
        data += packet
    return data

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_socket.connect(("127.0.0.1",8899))
server_socket.sendall(string_to_byte_stream("8899"))
server_socket.sendall(string_to_byte_stream("Hello"))
server_socket.sendall(string_to_byte_stream("有几个人",True))
server_socket.sendall(string_to_byte_stream("我的ID",True))

while True:
    byteMessage01 = RecvNums(server_socket,4)
    lenOfMessage = int.from_bytes(byteMessage01,'little')
    strMessage02 = RecvNums(server_socket,lenOfMessage).decode("utf-8")
    print(strMessage02)