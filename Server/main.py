# main.py 예시
import threading
import tcp.main  # TCP 서버
import http.main  # HTTP 서버

def start_tcp_server():
    tcp.main.run_server()

def start_http_server():
    http.main.run_server()

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=start_tcp_server)
    http_thread = threading.Thread(target=start_http_server)
    
    tcp_thread.start()
    http_thread.start()
    
    tcp_thread.join()
    http_thread.join()
