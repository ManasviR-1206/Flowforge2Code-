import socket
import select
import sys

def forward(source, destination):
    string = ' '
    while string:
        string = source.recv(1024)
        if string:
            destination.send(string)
        else:
            source.shutdown(socket.SHUT_RD)
            destination.shutdown(socket.SHUT_WR)
            break

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 8001))
    server.listen(10)
    print("Port forwarder listening on 8001 -> 8000")
    sys.stdout.flush()
    while True:
        try:
            client, addr = server.accept()
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect(('127.0.0.1', 8000))
            import threading
            t1 = threading.Thread(target=forward, args=(client, target), daemon=True)
            t2 = threading.Thread(target=forward, args=(target, client), daemon=True)
            t1.start()
            t2.start()
        except Exception as e:
            pass

if __name__ == '__main__':
    main()
