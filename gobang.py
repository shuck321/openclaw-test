#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五子棋游戏 (Gobang / Five in a Row)
简单命令行版
"""

import sys


class Gobang:
    """五子棋游戏类"""

    def __init__(self, size=15):
        self.size = size
        self.board = [[' ' for _ in range(size)] for _ in range(size)]
        self.current_player = 'X'  # X 为黑棋，O 为白棋
        self.winner = None
        self.moves = 0
        self.max_moves = size * size

    def display(self):
        """显示棋盘"""
        print("\n  ", end="")
        for i in range(self.size):
            print(f"{i:2}", end="")
        print()

        for i, row in enumerate(self.board):
            print(f"{i:2}", end=" ")
            for cell in row:
                print(f"{cell:2}", end="")
            print()
        print()

    def make_move(self, row, col):
        """落子"""
        if not (0 <= row < self.size and 0 <= col < self.size):
            return False, "位置超出棋盘范围"

        if self.board[row][col] != ' ':
            return False, "该位置已有棋子"

        self.board[row][col] = self.current_player
        self.moves += 1

        if self.check_win(row, col):
            self.winner = self.current_player
            return True, f"{self.current_player} 获胜！"

        if self.moves >= self.max_moves:
            self.winner = '平局'
            return True, "平局！"

        # 切换玩家
        self.current_player = 'O' if self.current_player == 'X' else 'X'
        return True, "落子成功"

    def check_win(self, row, col):
        """检查是否获胜"""
        player = self.board[row][col]
        directions = [
            (0, 1),   # 水平
            (1, 0),   # 垂直
            (1, 1),   # 对角线 \
            (1, -1)   # 对角线 /
        ]

        for dr, dc in directions:
            count = 1
            # 正向检查
            for i in range(1, 5):
                r, c = row + dr * i, col + dc * i
                if not (0 <= r < self.size and 0 <= c < self.size):
                    break
                if self.board[r][c] != player:
                    break
                count += 1
            # 反向检查
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

    def play(self):
        """开始游戏"""
        print("=" * 50)
        print("       五子棋游戏 (Gobang)")
        print("=" * 50)
        print("规则: 双方轮流落子，先连成五子者获胜")
        print("格式: 输入坐标，如 '7 7' 表示在第7行第7列落子")
        print("输入 'quit' 退出游戏\n")

        self.display()

        while not self.winner:
            player_name = "黑棋" if self.current_player == 'X' else "白棋"
            print(f"\n{player_name} ({self.current_player}) 落子: ", end="")

            try:
                user_input = input().strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("游戏结束！")
                    break

                parts = user_input.split()
                if len(parts) != 2:
                    print("格式错误，请输入两个数字，如: 7 7")
                    continue

                row, col = int(parts[0]), int(parts[1])

                success, message = self.make_move(row, col)
                print(message)

                if success:
                    self.display()

            except ValueError:
                print("输入错误，请输入数字")
            except KeyboardInterrupt:
                print("\n\n游戏结束！")
                break
            except Exception as e:
                print(f"发生错误: {e}")

        if self.winner:
            print(f"\n{'='*50}")
            if self.winner == '平局':
                print("         平局！")
            else:
                winner = "黑棋" if self.winner == 'X' else "白棋"
                print(f"       {winner} ({self.winner}) 获胜！")
            print(f"{'='*50}\n")


def main():
    """主函数"""
    print("欢迎来到五子棋游戏！\n")

    # 询问棋盘大小
    while True:
        try:
            size_input = input("请输入棋盘大小 (默认15，推荐15): ").strip()
            if size_input:
                size = int(size_input)
            else:
                size = 15

            if size < 5 or size > 30:
                print("棋盘大小建议在 5-30 之间")
                continue

            break
        except ValueError:
            print("请输入有效数字")

    game = Gobang(size)
    game.play()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n再见！")
        sys.exit(0)
