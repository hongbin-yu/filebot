#!/usr/bin/env python3
"""HTTPS-to-HTTP reverse proxy for FileBot API (solves mixed-content)"""
import http.server
import ssl
import urllib.request

TARGET = "http://localhost:8001"
PORT = 8443

class Proxy(http.server.BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        """Handle CORS preflight locally — no forwarding to backend"""
        origin = self.headers.get("Origin", "*")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        req_headers = self.headers.get("Access-Control-Request-Headers", "")
        self.send_header("Access-Control-Allow-Headers", req_headers or "*")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()
    
    def do_GET(self):    self._proxy("GET")
    def do_POST(self):   self._proxy("POST")
    def do_PUT(self):    self._proxy("PUT")
    def do_DELETE(self): self._proxy("DELETE")
    def do_PATCH(self):  self._proxy("PATCH")
    
    def _proxy(self, method):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len else None
        
        req = urllib.request.Request(TARGET + self.path, data=body, method=method)
        
        # Copy relevant headers from the browser
        for h in ["authorization", "content-type", "accept", "origin", "referer",
                  "x-requested-with", "user-agent"]:
            v = self.headers.get(h)
            if v:
                req.add_header(h, v)
        
        # If no content-type but has body, default to JSON
        if body and not self.headers.get("content-type"):
            req.add_header("content-type", "application/json")
        
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            self.send_response(resp.status)
            
            # Copy backend response headers (skip hop-by-hop)
            for k, v in resp.getheaders():
                kl = k.lower()
                if kl not in ("transfer-encoding", "connection", "keep-alive",
                              "access-control-allow-origin", "access-control-allow-credentials",
                              "access-control-allow-methods", "access-control-allow-headers"):
                    self.send_header(k, v)
            
            # Always add CORS headers (overriding backend if needed)
            origin = self.headers.get("Origin", "*")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            
            self.end_headers()
            self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            # Forward HTTP errors from backend (including 422 etc)
            body_bytes = e.read() if hasattr(e, 'read') else b''
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            origin = self.headers.get("Origin", "*")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            self.wfile.write(body_bytes)
        except Exception as e:
            self.send_response(502)
            origin = self.headers.get("Origin", "*")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error":"proxy: {e}"}}'.encode())
    
    def log_message(self, format, *args):
        pass  # quiet

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Proxy)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("/tmp/filebot-cert.pem", "/tmp/filebot-key.pem")
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print(f"HTTPS proxy listening on :{PORT} -> {TARGET}")
    server.serve_forever()
