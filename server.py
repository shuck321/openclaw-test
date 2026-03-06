#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import http.server, socketserver, json, random, time, threading
from urllib.parse import urlparse, parse_qs

games = {}
lock = threading.Lock()


class Game:
    def __init__(self):
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self.current = 'X'
        self.winner = None
        self.ai = False

    def check_win(self, r, c):
        """检查最后一步是否导致获胜"""
        player = self.board[r][c]
        dirs = [(0,1), (1,0), (1,1), (1,-1)]
        
        for dr, dc in dirs:
            count = 1  # 已经包含当前棋子
            
            # 正向检查
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < 15 and 0 <= nc < 15:
                    if self.board[nr][nc] == player:
                        count += 1
                    else:
                        break
                else:
                    break
            
            # 反向检查
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if 0 <= nr < 15 and 0 <= nc < 15:
                    if self.board[nr][nc] == player:
                        count += 1
                    else:
                        break
                else:
                    break
            
            if count >= 5:
                return True
        return False

    def move(self, r, c):
        if not (0 <= r < 15 and 0 <= c < 15):
            return False, "超出范围"
        if self.board[r][c] != ' ':
            return False, "已有棋子"
        
        self.board[r][c] = self.current
        
        # 检查获胜
        if self.check_win(r, c):
            self.winner = self.current
            return True, f"{self.current}获胜！"
        
        self.current = 'O' if self.current == 'X' else 'X'
        return True, "成功"

    def ai_move(self):
        if not self.ai or self.winner or self.current != 'O':
            return None
        
        def evaluate_position(r, c, player):
            """评估在(r,c)位置下player棋子的得分"""
            score = 0
            dirs = [(0,1), (1,0), (1,1), (1,-1)]
            
            for dr, dc in dirs:
                count = 1
                blocked = 0
                
                # 正向
                for i in range(1,5):
                    nr, nc = r + dr*i, c + dc*i
                    if 0 <= nr < 15 and 0 <= nc < 15:
                        if self.board[nr][nc] == player:
                            count += 1
                        elif self.board[nr][nc] != ' ':
                            blocked += 1
                            break
                        else:
                            break
                    else:
                        blocked += 1
                        break
                
                # 反向
                for i in range(1,5):
                    nr, nc = r - dr*i, c - dc*i
                    if 0 <= nr < 15 and 0 <= nc < 15:
                        if self.board[nr][nc] == player:
                            count += 1
                        elif self.board[nr][nc] != ' ':
                            blocked += 1
                            break
                        else:
                            break
                    else:
                        blocked += 1
                        break
                
                # 根据连子数和阻挡情况打分
                if count >= 5:
                    score += 10000  # 直接获胜
                elif count == 4 and blocked == 0:
                    score += 5000   # 活四
                elif count == 4 and blocked == 1:
                    score += 1000   # 冲四
                elif count == 3 and blocked == 0:
                    score += 500    # 活三
                elif count == 3 and blocked == 1:
                    score += 100    # 冲三
                elif count == 2:
                    score += 10
                elif count == 1:
                    score += 1
            
            return score
        
        empty = []
        for i in range(15):
            for j in range(15):
                if self.board[i][j] == ' ':
                    # 进攻得分（AI自己）
                    attack = evaluate_position(i, j, 'O')
                    # 防守得分（阻挡玩家）
                    defense = evaluate_position(i, j, 'X')
                    
                    # 总得分：防守优先，然后进攻
                    total = defense * 1.5 + attack
                    
                    # 中心优先
                    if abs(i-7) + abs(j-7) <= 2:
                        total += 50
                    
                    empty.append((i, j, total))
        
        if not empty:
            return None
            
        # 按得分排序，选择最高的
        empty.sort(key=lambda x: -x[2])
        best_move = empty[0]
        return (best_move[0], best_move[1])

    def to_dict(self):
        return {
            'board': self.board,
            'current': self.current,
            'winner': self.winner,
            'ai': self.ai
        }


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        if p.path in ['/', '/index.html']:
            self.serve_html()
        elif p.path == '/api/get':
            self.get(p)
        elif p.path == '/api/create':
            self.create()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            l = int(self.headers.get('Content-Length', 0))
            d = json.loads(self.rfile.read(l).decode('utf-8'))
            p = urlparse(self.path)
            if p.path == '/api/move':
                self.move_req(d)
            elif p.path == '/api/enable_ai':
                self.enable_ai(d)
            elif p.path == '/api/ai':
                self.ai_req(d)
            elif p.path == '/api/reset':
                self.reset(d)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(400)
            self.end_headers()

    def serve_html(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(self.html().encode('utf-8'))

    def create(self):
        rid = str(random.randint(1000,9999))
        with lock:
            games[rid] = Game()
        self.json({'id': rid})
        print(f"Created: {rid}")

    def get(self, p):
        q = parse_qs(p.query)
        rid = q.get('id', [''])[0]
        with lock:
            if rid in games:
                self.json(games[rid].to_dict())
            else:
                self.json({'error': 'not found'}, 404)

    def move_req(self, d):
        rid = d.get('id')
        r, c = d.get('r'), d.get('c')
        with lock:
            if rid in games:
                ok, msg = games[rid].move(r, c)
                self.json({'ok': ok, 'msg': msg, 'game': games[rid].to_dict()})

    def enable_ai(self, d):
        rid = d.get('id')
        with lock:
            if rid in games:
                games[rid].ai = d.get('ai', False)
                self.json({'ok': True, 'game': games[rid].to_dict()})

    def ai_req(self, d):
        rid = d.get('id')
        with lock:
            if rid in games:
                move = games[rid].ai_move()
                if move:
                    ok, msg = games[rid].move(move[0], move[1])
                    self.json({'ok': ok, 'msg': f"AI: {move}", 'game': games[rid].to_dict()})
                else:
                    self.json({'ok': False})

    def reset(self, d):
        rid = d.get('id')
        with lock:
            if rid in games:
                games[rid] = Game()
                self.json({'ok': True, 'game': games[rid].to_dict()})

    def json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def html(self):
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>五子棋 - AI对战</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei',sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
.container{background:rgba(255,255,255,0.95);border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:40px;max-width:900px;width:100%}
h1{text-align:center;color:#333;margin-bottom:10px;font-size:2.5em}
.subtitle{text-align:center;color:#666;margin-bottom:30px;font-size:1.1em}
.room-section{background:#f8f9fa;padding:25px;border-radius:10px;margin-bottom:30px}
.input-group{display:flex;gap:15px;margin-bottom:15px;flex-wrap:wrap}
input{flex:1;min-width:200px;padding:12px 20px;border:2px solid #ddd;border-radius:8px;font-size:16px}
input:focus{border-color:#667eea;outline:none}
button{padding:12px 30px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;min-width:120px}
button:hover{transform:translateY(-2px);box-shadow:0 5px 20px rgba(102,126,234,0.4)}
.game-section{display:none}
.game-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:15px;background:#f8f9fa;border-radius:8px}
.player-info{font-size:18px;font-weight:600}
.ai-badge{display:inline-block;padding:5px 15px;background:#ff6b6b;color:white;border-radius:20px;margin-left:10px;font-size:14px;font-weight:600}
.ai-badge.on{background:#4CAF50}
.board-container{display:flex;justify-content:center;margin-bottom:20px}
.board{display:grid;grid-template-columns:repeat(15,1fr);gap:1px;background:#333;padding:1px;border:2px solid #333;max-width:600px;width:100%}
.cell{background:#e8d5a3;aspect-ratio:1;cursor:pointer;position:relative;transition:all 0.2s}
.cell:hover{background:#dec49c}
.cell.x::before,.cell.o::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:70%;height:70%;border-radius:50%}
.cell.x::before{background:#333}
.cell.o::before{background:#fff;border:2px solid #333}
.message{text-align:center;padding:15px;background:#4CAF50;color:white;border-radius:8px;font-size:18px;font-weight:600;margin-bottom:20px;display:none}
.message.error{background:#f44336}
.controls{display:flex;justify-content:center;gap:15px;margin-top:20px}
</style>
</head>
<body>
<div class="container">
<h1>🎮 五子棋 - AI对战</h1>
<p class="subtitle">Web 实时对战</p>

<div class="room-section" id="rs">
<div class="input-group"><button onclick="cr()">创建房间</button><input id="rid" placeholder="房间号"><button onclick="jr()">加入房间</button></div>
<div id="msg" class="message"></div></div>

<div class="game-section" id="gs">
<div class="game-info"><div class="player-info">当前: <span id="cur">X</span></div><div class="player-info">模式: <span id="ai" class="ai-badge">双人</span></div></div>
<div class="board-container"><div class="board" id="bd"></div></div>
<div id="gm" class="message"></div>
<div class="controls"><button id="ab" onclick="ea()">🤖 启用AI</button><button id="rb" onclick="re()" style="display:none;">重新开始</button><button onclick="lv()">退出</button></div>
<div style="text-align:center;margin-top:20px;color:#666;font-size:14px">房间号: <strong id="crid"></strong></div></div>
</div>
<script>
let rid=null,cur='X',ai=false;
function cr(){fetch('/api/create').then(r=>r.json()).then(d=>{rid=d.id;gs(rid);lg();})}
function jr(){const i=document.getElementById('rid').value.trim();if(i){rid=i;gs(rid);lg();}}
function gs(){fetch('/api/get?id='+rid).then(r=>r.json()).then(d=>{if(d.error){sm(d.error,true)}else{up(d)}})}
function up(d){bd=d.board;cur=d.current;ai=d.ai;rb();cb();rm();if(ai&&cur=='O'){setTimeout(am,500)}}
function cb(){const e=document.getElementById('bd');e.innerHTML='';for(let i=0;i<bd.length;i++){for(let j=0;j<bd[i].length;j++){const c=document.createElement('div');c.className='cell';if(bd[i][j])c.classList.add(bd[i][j].toLowerCase());c.onclick=()=>mv(i,j);e.appendChild(c)}}}
function mv(r,c){if(bd[r][c]!=''){fetch('/api/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:rid,r:r,c:c})}).then(r=>r.json()).then(d=>{if(d.error){sm(d.error,true)}else{if(d.ok){up(d.game)}else{sm(d.msg,true)}}(e=>{sm('移动失败',true)}))}}
function ea(){ai=!ai;fetch('/api/enable_ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:rid,ai:ai})}).then(r=>r.json()).then(d=>{if(d.ok){up(d.game);sm(ai?'AI已启用':'AI已禁用',false);if(ai&&cur=='O')am()}else{sm('切换失败',true)}(e=>{sm('切换失败',true)}))}
function am(){fetch('/api/ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:rid})}).then(r=>r.json()).then(d=>{if(d.ok){up(d.game)}else{sm('无法落子',true)}(e=>{sm('AI失败',true)}))}
function re(){fetch('/api/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:rid})}).then(r=>r.json()).then(d=>{if(d.ok){up(d.game);document.getElementById('gm').style.display='none'}else{sm('重置失败',true)}))}
function lv(){location.reload()}
function rb(){document.getElementById('ab').textContent=ai?'👥 禁用AI':'🤖 启用AI';document.getElementById('ai').className='ai-badge'+(ai?' on':'')}
function rm(){const m=document.getElementById('gm');if(d.winner){m.textContent=d.winner==='平局'?'🤝 平局':`🎉 ${d.winner==='X'?'黑棋':'白棋'}(${d.winner})获胜`;m.style.display='block';document.getElementById('rb').style.display='block'}}
function sm(t,e){const m=document.getElementById('msg');m.textContent=t;m.style.display='block';m.classList.toggle('error',e);setTimeout(()=>{m.style.display='none'},3000)}
function lg() {
  document.getElementById('crid').textContent = rid;
}
cb();setInterval(()=>{if(rid&&!ai)gs()},2000)
</script>
</body>
</html>"""

def main():
    PORT = 5000
    print('='*60)
    print('          五子棋 - AI对战 (最终稳定版)')
    print('='*60)
    print(f'本地: http://localhost:{PORT}')
    print(f'公网: http://115.190.196.123:{PORT}')
    print()
    print('功能: AI对战 | 双人对战')
    print('启动中...')
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    main()
