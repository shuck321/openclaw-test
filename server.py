#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五子棋 Web 服务器 (修复版)
"""

import http.server
import socketserver
import json
import threading
import random
from urllib.parse import urlparse, parse_qs

games = {}
game_lock = threading.Lock()


class GobangGame:
    def __init__(self, size=15):
        self.size = size
        self.board = [[' ' for _ in range(size)] for _ in range(size)]
        self.current_player = 'X'
        self.winner = None
        self.moves = 0
        self.max_moves = size * size
        self.last_move = None

    def make_move(self, row, col):
        if not (0 <= row < self.size and 0 <= col < self.size):
            return False, "位置超出棋盘范围"
        if self.board[row][col] != ' ':
            return False, "该位置已有棋子"

        self.board[row][col] = self.current_player
        self.last_move = (row, col)
        self.moves += 1

        if self.check_win(row, col):
            self.winner = self.current_player
            return True, f"{self.current_player} 获胜！"

        if self.moves >= self.max_moves:
            self.winner = '平局'
            return True, "平局！"

        self.current_player = 'O' if self.current_player == 'X' else 'X'
        return True, "落子成功"

    def check_win(self, row, col):
        player = self.board[row][col]
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                r, c = row + dr * i, col + dc * i
                if not (0 <= r < self.size and 0 <= c < self.size):
                    break
                if self.board[r][c] != player:
                    break
                count += 1
            for i in range(1, 5):
                r, c = row - dr * i, col - dc * i
                if not (0 <= r < self.size and 0 <= c < self.size):
                    break
                if self.board[r][c] != player:
                    break
                count += 1
            if count >= 5:
                return True
        return False

    def to_dict(self):
        return {
            'board': self.board,
            'current_player': self.current_player,
            'winner': self.winner,
            'moves': self.moves,
            'last_move': self.last_move
        }


class GobangHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self.serve_html()
        elif parsed_path.path == '/api/create_room':
            self.create_room()
        elif parsed_path.path == '/api/get_game':
            self.get_game(parsed_path)
        elif parsed_path.path == '/api/list_rooms':
            self.list_rooms()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            parsed_path = urlparse(self.path)

            if parsed_path.path == '/api/make_move':
                self.make_move(data)
            elif parsed_path.path == '/api/reset_game':
                self.reset_game(data)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"POST error: {e}")
            self.send_response(400)
            self.end_headers()

    def serve_html(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html_content = self.get_html_content()
        self.wfile.write(html_content.encode('utf-8'))

    def create_room(self):
        room_id = str(random.randint(1000, 9999))
        with game_lock:
            games[room_id] = GobangGame()
        response = {'room_id': room_id}
        self.send_json_response(response)
        print(f"Created room: {room_id}")

    def get_game(self, parsed_path):
        try:
            query = parse_qs(parsed_path.query)
            room_id = query.get('room_id', [''])[0]

            with game_lock:
                if room_id in games:
                    game = games[room_id]
                    self.send_json_response(game.to_dict())
                    print(f"Get game: {room_id}")
                else:
                    self.send_json_response({'error': '房间不存在'}, 404)
        except Exception as e:
            print(f"Get game error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def make_move(self, data):
        try:
            room_id = data.get('room_id')
            row = data.get('row')
            col = data.get('col')

            with game_lock:
                if room_id in games:
                    game = games[room_id]
                    success, message = game.make_move(row, col)
                    self.send_json_response({
                        'success': success,
                        'message': message,
                        'game': game.to_dict()
                    })
                    print(f"Move: room={room_id}, row={row}, col={col}, success={success}")
                else:
                    self.send_json_response({'error': '房间不存在'}, 404)
        except Exception as e:
            print(f"Make move error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def reset_game(self, data):
        try:
            room_id = data.get('room_id')

            with game_lock:
                if room_id in games:
                    games[room_id] = GobangGame()
                    self.send_json_response({'success': True, 'game': games[room_id].to_dict()})
                    print(f"Reset game: {room_id}")
                else:
                    self.send_json_response({'error': '房间不存在'}, 404)
        except Exception as e:
            print(f"Reset game error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def list_rooms(self):
        with game_lock:
            rooms = list(games.keys())
            self.send_json_response({'rooms': rooms})

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def get_html_content(self):
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>五子棋在线对战</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 900px;
            width: 100%;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .room-section {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .input-group {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        input {
            flex: 1;
            min-width: 200px;
            padding: 12px 20px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        input:focus {
            border-color: #667eea;
            outline: none;
        }
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            min-width: 120px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102,126,234,0.4);
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .game-section {
            display: none;
        }
        .game-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .player-info {
            font-size: 18px;
            font-weight: 600;
        }
        .board-container {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }
        .board {
            display: grid;
            grid-template-columns: repeat(15, 1fr);
            gap: 1px;
            background: #333;
            padding: 1px;
            border: 2px solid #333;
            max-width: 600px;
            width: 100%;
        }
        .cell {
            background: #e8d5a3;
            aspect-ratio: 1;
            cursor: pointer;
            position: relative;
            transition: all 0.2s;
        }
        .cell:hover {
            background: #dec49c;
        }
        .cell.x::before, .cell.o::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 70%;
            height: 70%;
            border-radius: 50%;
        }
        .cell.x::before {
            background: #333;
        }
        .cell.o::before {
            background: #fff;
            border: 2px solid #333;
        }
        .message {
            text-align: center;
            padding: 15px;
            background: #4CAF50;
            color: white;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            display: none;
        }
        .message.error {
            background: #f44336;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
        }
        .status {
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 五棋在线对战</h1>
        <p class="subtitle">Web 实时对战 (修复版)</p>

        <div class="room-section" id="roomSection">
            <div class="input-group">
                <button onclick="createRoom()">创建房间</button>
                <input type="text" id="roomId" placeholder="房间号 (如: 1234)" maxlength="4">
                <button onclick="joinRoom()">加入房间</button>
            </div>
            <div id="message" class="message"></div>
        </div>

        <div class="game-section" id="gameSection">
            <div class="game-info">
                <div class="player-info">当前: <span id="currentPlayer">X</span></div>
            </div>

            <div class="board-container">
                <div class="board" id="board"></div>
            </div>

            <div id="gameMessage" class="message"></div>

            <div class="controls">
                <button onclick="resetGame()" id="resetBtn" style="display: none;">重新开始</button>
                <button onclick="leaveRoom()">退出房间</button>
                <button onclick="autoPlay()">自动对战</button>
            </div>

            <div class="status">
                房间号: <strong id="currentRoomId"></strong>
            </div>
        </div>
    </div>

    <script>
        let currentRoom = null;
        let gameBoard = [];
        let currentPlayer = 'X';
        let autoPlayEnabled = false;

        function createRoom() {
            fetch('/api/create_room')
                .then(response => response.json())
                .then(data => {
                    currentRoom = data.room_id;
                    showGameSection(currentRoom);
                    loadGameState();
                })
                .catch(error => {
                    showMessage('创建房间失败', true);
                });
        }

        function joinRoom() {
            const roomId = document.getElementById('roomId').value.trim();
            if (!roomId) {
                showMessage('请输入房间号', true);
                return;
            }
            currentRoom = roomId;
            showGameSection(roomId);
            loadGameState();
        }

        function showGameSection(roomId) {
            document.getElementById('roomSection').style.display = 'none';
            document.getElementById('gameSection').style.display = 'block';
            document.getElementById('currentRoomId').textContent = roomId;
        }

        function loadGameState() {
            fetch(`/api/get_game?room_id=${currentRoom}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showMessage(data.error, true);
                        return;
                    }
                    updateGameState(data);
                })
                .catch(error => {
                    showMessage('加载游戏状态失败', true);
                });
        }

        function updateGameState(data) {
            gameBoard = data.board;
            currentPlayer = data.current_player;
            document.getElementById('currentPlayer').textContent = currentPlayer;
            renderBoard();

            if (data.winner) {
                const gameMessage = document.getElementById('gameMessage');
                if (data.winner === '平局') {
                    gameMessage.textContent = '🤝 平局！';
                } else {
                    const winnerName = data.winner === 'X' ? '黑棋' : '白棋';
                    gameMessage.textContent = `🎉 ${winnerName} (${data.winner}) 获胜！`;
                }
                gameMessage.style.display = 'block';
                document.getElementById('resetBtn').style.display = 'block';
            }
        }

        function initBoard(size = 15) {
            gameBoard = Array(size).fill(null).map(() => Array(size).fill(''));
            renderBoard();
        }

        function renderBoard() {
            const boardElement = document.getElementById('board');
            boardElement.innerHTML = '';

            for (let i = 0; i < gameBoard.length; i++) {
                for (let j = 0; j < gameBoard[i].length; j++) {
                    const cell = document.createElement('div');
                    cell.className = 'cell';
                    cell.dataset.row = i;
                    cell.dataset.col = j;

                    if (gameBoard[i][j]) {
                        cell.classList.add(gameBoard[i][j].toLowerCase());
                    }

                    cell.addEventListener('click', () => makeMove(i, j));
                    boardElement.appendChild(cell);
                }
            }
        }

        function makeMove(row, col) {
            if (gameBoard[row][col] !== '') {
                return;
            }

            fetch('/api/make_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_id: currentRoom,
                    row: row,
                    col: col
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessage(data.error, true);
                    return;
                }

                if (data.success) {
                    updateGameState(data.game);

                    if (autoPlayEnabled && !data.game.winner) {
                        setTimeout(autoPlayMove, 500);
                    }
                } else {
                    showMessage(data.message, false);
                }
            })
            .catch(error => {
                showMessage('落子失败', true);
            });
        }

        function resetGame() {
            fetch('/api/reset_game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_id: currentRoom
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateGameState(data.game);
                    document.getElementById('gameMessage').style.display = 'none';
                    document.getElementById('resetBtn').style.display = 'none';
                }
            })
            .catch(error => {
                showMessage('重置游戏失败', true);
            });
        }

        function leaveRoom() {
            window.location.reload();
        }

        function autoPlay() {
            autoPlayEnabled = !autoPlayEnabled;
            showMessage(autoPlayEnabled ? '自动对战已开启' : '自动对战已关闭', false);
        }

        function autoPlayMove() {
            if (!autoPlayEnabled) return;

            let emptyCells = [];
            for (let i = 0; i < gameBoard.length; i++) {
                for (let j = 0; j < gameBoard[i].length; j++) {
                    if (gameBoard[i][j] === '') {
                        emptyCells.push({row: i, col: j});
                    }
                }
            }

            if (emptyCells.length > 0) {
                const randomMove = emptyCells[Math.floor(Math.random() * emptyCells.length)];
                makeMove(randomMove.row, randomMove.col);
            }
        }

        function showMessage(text, isError = false) {
            const messageElement = document.getElementById('message');
            messageElement.textContent = text;
            messageElement.style.display = 'block';
            messageElement.classList.toggle('error', isError);

            setTimeout(() => {
                messageElement.style.display = 'none';
            }, 3000);
        }

        initBoard(15);

        setInterval(() => {
            if (currentRoom && !autoPlayEnabled) {
                loadGameState();
            }
        }, 2000);
    </script>
</body>
</html>
"""


def main() -> None:
    PORT = 5000

    print('=' * 60)
    print('           五子棋 Web 服务器 (修复版)')
    print('=' * 60)
    print(f'访问地址: http://0.0.0.0:{PORT}')
    print(f'公网访问: http://115.190.196.123:{PORT}')
    print()
    print('功能:')
    print('  ✨ 创建/加入房间')
    print('  🎮 落子对战')
    print('  🔄 自动刷新')
    print('  🤖 自动对战模式')
    print()
    print('按 Ctrl+C 停止服务器\n')

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), GobangHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n\n服务器已停止')
        print('再见！👋')


if __name__ == '__main__':
    main()
