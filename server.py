import queue
import socket
import threading

# 所有消息的格式：4bit小头int作为头 + 消息
# 客户端连接  ->  客户端utf-8输入房间名  ->  服务器utf-8回复结果 ->  转发所有消息到同房间所有人

serverIP = "0.0.0.0"
serverPort = 8899

# 创建一个聊天室字典，键为聊天室名称，值为该聊天室内所有客户端的连接列表
chat_rooms = {}

# 创建一个线程安全的聊天室管理锁
chat_room_lock = threading.Lock()


# 字符串编码为字节流
def string_to_byte_stream(s:str):
    utf8_bytes = s.encode('utf-8')
    length = len(utf8_bytes)
    length_bytes = length.to_bytes(4, 'little')
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



class SingleClient():

    def __init__(self, thisSocket:socket.socket,client_address):
        self.isAlive = True
        self.socket = thisSocket
        self.thisAddr = client_address
        self.block_queue = queue.Queue()

        self.threadRecv = threading.Thread(target=self.handle_Recv)
        self.threadRecv.start()  # 启动线程

    def handle_Recv(self): 
        try:
            # 设置超时
            self.socket.settimeout(3.0)
            # 接收连接
            lenOfRoom = int.from_bytes(RecvNums(self.socket,4),'little')
            self.strOfRoomName = RecvNums(self.socket,lenOfRoom).decode('utf-8')

            # 构造第一条消息
            self.MySendMessage(string_to_byte_stream("OK;Version 20240509;"))
            # 分配聊天室
            with chat_room_lock:
                # 如果聊天室不存在，则创建一个新的聊天室
                if self.strOfRoomName not in chat_rooms:
                    chat_rooms[self.strOfRoomName] = []
                    print(f"建立聊天室:{self.strOfRoomName}")
                # 将客户端连接添加到聊天室
                chat_rooms[self.strOfRoomName].append(self)
                print(f"聊天室{self.strOfRoomName}:{self.thisAddr}加入")
            # 循环读取消息
            try:
                # 取消超时
                self.socket.settimeout(None)
                # 开启发送线程
                self.threadSend = threading.Thread(target=self.handle_Send)
                self.threadSend.start()  # 启动线程
                while self.isAlive:
                    # 阻塞读取消息
                    byteMessage01 = RecvNums(self.socket,4)
                    lenOfMessage = int.from_bytes(byteMessage01,'little')
                    byteMessage02 = RecvNums(self.socket,lenOfMessage)
                    # 分配给发送队列
                    with chat_room_lock:
                        for perClient in chat_rooms[self.strOfRoomName]:
                            if perClient != self:
                                perClient.MySendMessage(byteMessage01 + byteMessage02)

            except Exception as e:
                print(f"聊天室{self.strOfRoomName}:{self.thisAddr}聊天室内错误:{type(e)}")
                self.isAlive = False
                self.socket.close()
            finally:
                with chat_room_lock:
                    # 从聊天室中移除客户端连接
                    chat_rooms[self.strOfRoomName].remove(self)
                    print(f"聊天室{self.strOfRoomName}:{self.thisAddr}退出")
                    # 如果聊天室为空，则删除该聊天室
                    if not chat_rooms[self.strOfRoomName]:
                        del chat_rooms[self.strOfRoomName]
                        print(f"聊天室{self.strOfRoomName}:解散")
        except TimeoutError as e:
            print(f"聊天室未建立:{self.thisAddr}超时")
        except Exception as e:
            print(f"聊天室未建立:{self.thisAddr}接收初始消息错误:{type(e)}")
            self.isAlive = False
        finally:
            self.socket.close()


    def handle_Send(self):
        try:
            while self.isAlive:# 只要活着
                try:
                    item = self.block_queue.get(timeout=0.5)  # 使用get方法，设置超时
                    self.socket.sendall(item)
                except queue.Empty:
                    pass
        except Exception as e:
            print(f"聊天室{self.strOfRoomName}:{self.thisAddr}发送线程错误")    
            self.isAlive = False
            self.socket.close()
        finally:
            self.socket.close()
        
    def MySendMessage(self,byteMessages):
        self.block_queue.put(byteMessages)



# 创建服务器套接字
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((serverIP, serverPort))
server_socket.listen()

print(f"TCP服务器开启于{serverIP}:{serverPort}")

try:
    while True:
        # 接受客户端连接
        client_sock, client_addr = server_socket.accept()
        print(f"新的连接来自 {client_addr}")
        SingleClient(client_sock,client_addr)
finally:
    # 关闭服务器套接字
    server_socket.close()
