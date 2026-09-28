# -*- coding: utf-8 -*-
"""三人五子棋（图形界面版）
黑 / 白 / 红 三方轮流，鼠标点击棋盘交叉点落子，先连成五子者胜。
零第三方依赖，仅使用 Python 标准库 tkinter。
"""
import os
import pickle
import tkinter as tk
from tkinter import messagebox, filedialog

# ---------------- 基本参数 ----------------
ROWS = 10          # 行数（x: 0~9）
COLS = 10          # 列数（y: 0~9）
CELL = 52          # 每格像素
MARGIN = 40        # 棋盘边距
BOARD_W = MARGIN * 2 + CELL * (COLS - 1)
BOARD_H = MARGIN * 2 + CELL * (ROWS - 1)
STONE_R = 21       # 棋子半径

PLAYER_NAMES = {1: '黑方', 2: '白方', 3: '红方'}
PLAYER_COLORS = {1: '#111111', 2: '#F5F5F5', 3: '#D32F2F'}
PLAYER_OUTLINE = {1: '#000000', 2: '#777777', 3: '#7B0000'}
PLAYER_TURN_TEXT = {1: '#111111', 2: '#666666', 3: '#D32F2F'}
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (-1, 1))


def inrange(x, y):
    return 0 <= x < ROWS and 0 <= y < COLS


def win_line(board, x, y):
    """若 (x,y) 处棋子形成五连，返回 (方向, 五连坐标列表)；否则返回 None。"""
    t = board[x][y]
    if t == 0:
        return None
    for dx, dy in DIRECTIONS:
        line = [(x, y)]
        # 正向
        nx, ny = x + dx, y + dy
        while inrange(nx, ny) and board[nx][ny] == t:
            line.append((nx, ny))
            nx += dx
            ny += dy
        # 反向
        nx, ny = x - dx, y - dy
        while inrange(nx, ny) and board[nx][ny] == t:
            line.insert(0, (nx, ny))
            nx -= dx
            ny -= dy
        if len(line) >= 5:
            return (dx, dy), line
    return None


class GomokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title('三人五子棋（黑 / 白 / 红）')
        self.root.resizable(False, False)

        # 顶部状态条
        top = tk.Frame(root)
        top.pack(fill='x', padx=8, pady=(8, 2))
        self.turn_lbl = tk.Label(top, text='', font=('微软雅黑', 14, 'bold'))
        self.turn_lbl.pack(side='left')
        self.tip_lbl = tk.Label(top, text='点击棋盘交叉点落子',
                                font=('微软雅黑', 10), fg='#888')
        self.tip_lbl.pack(side='right')

        # 棋盘
        self.canvas = tk.Canvas(root, width=BOARD_W, height=BOARD_H,
                                bg='#E8B96A', highlightthickness=1,
                                highlightbackground='#8A5A1E')
        self.canvas.pack(padx=10, pady=6)
        self.canvas.bind('<Button-1>', self.on_click)

        # 底部按钮
        btns = tk.Frame(root)
        btns.pack(pady=(0, 10))
        tk.Button(btns, text='重新开始', width=10, command=self.restart).pack(side='left', padx=6)
        tk.Button(btns, text='悔棋', width=10, command=self.undo).pack(side='left', padx=6)
        tk.Button(btns, text='保存棋局', width=10, command=self.save_game).pack(side='left', padx=6)
        tk.Button(btns, text='读取棋局', width=10, command=self.load_game).pack(side='left', padx=6)

        self.restart()

    # ---------- 状态 ----------
    def restart(self):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.history = []       # (x, y, player)
        self.who = 0            # 0 黑，1 白，2 红
        self.game_over = False
        self.last_move = None
        self.draw_board()
        self.update_turn_label()

    def current_stone(self):
        return self.who + 1

    def update_turn_label(self):
        stone = self.current_stone()
        if self.game_over:
            return
        self.turn_lbl.config(text=f'● 轮到{PLAYER_NAMES[stone]}落子',
                             fg=PLAYER_TURN_TEXT[stone])

    # ---------- 绘制 ----------
    def grid_pos(self, x, y):
        return MARGIN + y * CELL, MARGIN + x * CELL

    def draw_board(self):
        self.canvas.delete('all')
        # 网格线
        for i in range(ROWS):
            x1, y1 = self.grid_pos(i, 0)
            x2, y2 = self.grid_pos(i, COLS - 1)
            self.canvas.create_line(x1, y1, x2, y2, fill='#7A4E12')
        for j in range(COLS):
            x1, y1 = self.grid_pos(0, j)
            x2, y2 = self.grid_pos(ROWS - 1, j)
            self.canvas.create_line(x1, y1, x2, y2, fill='#7A4E12')
        # 坐标标注
        for i in range(ROWS):
            px, py = self.grid_pos(i, 0)
            self.canvas.create_text(px, 14, text=str(i), fill='#7A4E12', font=('Consolas', 9))
        for j in range(COLS):
            px, py = self.grid_pos(0, j)
            self.canvas.create_text(14, py, text=str(j), fill='#7A4E12', font=('Consolas', 9))
        # 棋子
        for i in range(ROWS):
            for j in range(COLS):
                if self.board[i][j] != 0:
                    self.draw_stone(i, j, self.board[i][j])
        # 最后一手标记
        if self.last_move:
            x, y = self.last_move
            px, py = self.grid_pos(x, y)
            self.canvas.create_line(px - 6, py, px + 6, py, fill='#1E88E5', width=2)
            self.canvas.create_line(px, py - 6, px, py + 6, fill='#1E88E5', width=2)

    def draw_stone(self, x, y, stone):
        px, py = self.grid_pos(x, y)
        self.canvas.create_oval(px - STONE_R, py - STONE_R,
                                px + STONE_R, py + STONE_R,
                                fill=PLAYER_COLORS[stone],
                                outline=PLAYER_OUTLINE[stone], width=2)

    def highlight_win(self, points):
        for x, y in points:
            px, py = self.grid_pos(x, y)
            self.canvas.create_oval(px - STONE_R + 3, py - STONE_R + 3,
                                    px + STONE_R - 3, py + STONE_R - 3,
                                    outline='#FFEB3B', width=3)

    # ---------- 交互 ----------
    def pixel_to_cell(self, px, py):
        y = round((px - MARGIN) / CELL)
        x = round((py - MARGIN) / CELL)
        if not inrange(x, y):
            return None
        gx, gy = self.grid_pos(x, y)
        if (px - gx) ** 2 + (py - gy) ** 2 > (CELL // 2) ** 2:
            return None
        return x, y

    def on_click(self, event):
        if self.game_over:
            return
        cell = self.pixel_to_cell(event.x, event.y)
        if cell is None:
            return
        x, y = cell
        if self.board[x][y] != 0:
            self.tip_lbl.config(text='该位置已有棋子！', fg='#D32F2F')
            return
        stone = self.current_stone()
        self.board[x][y] = stone
        self.history.append((x, y, stone))
        self.last_move = (x, y)
        self.tip_lbl.config(text='点击棋盘交叉点落子', fg='#888')

        result = win_line(self.board, x, y)
        if result:
            self.game_over = True
            _, points = result
            self.draw_board()
            self.highlight_win(points)
            self.turn_lbl.config(text=f'🎉 {PLAYER_NAMES[stone]}获胜！',
                                 fg=PLAYER_TURN_TEXT[stone])
            messagebox.showinfo('游戏结束', f'{PLAYER_NAMES[stone]}连成五子，获胜！')
            return

        if len(self.history) == ROWS * COLS:
            self.game_over = True
            self.draw_board()
            self.turn_lbl.config(text='棋盘已满，平局！', fg='#333')
            messagebox.showinfo('游戏结束', '棋盘已满，本局平局！')
            return

        self.who = (self.who + 1) % 3
        self.draw_board()
        self.update_turn_label()

    def undo(self):
        if self.game_over or not self.history:
            return
        x, y, _ = self.history.pop()
        self.board[x][y] = 0
        self.who = (self.who - 1) % 3
        self.last_move = self.history[-1][:2] if self.history else None
        self.draw_board()
        self.update_turn_label()

    # ---------- 存档 ----------
    def save_game(self):
        path = filedialog.asksaveasfilename(
            title='保存棋局', defaultextension='.pkl',
            filetypes=[('五子棋存档', '*.pkl'), ('所有文件', '*.*')])
        if not path:
            return
        data = {'board': self.board, 'history': self.history,
                'who': self.who, 'last_move': self.last_move}
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            self.tip_lbl.config(text=f'已保存：{os.path.basename(path)}', fg='#2E7D32')
        except OSError as e:
            messagebox.showerror('保存失败', str(e))

    def load_game(self):
        path = filedialog.askopenfilename(
            title='读取棋局',
            filetypes=[('五子棋存档', '*.pkl'), ('所有文件', '*.*')])
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.board = data['board']
            self.history = data['history']
            self.who = data['who']
            self.last_move = data.get('last_move')
            self.game_over = False
            self.draw_board()
            self.update_turn_label()
            self.tip_lbl.config(text=f'已读取：{os.path.basename(path)}', fg='#2E7D32')
        except (OSError, pickle.PickleError, KeyError, TypeError) as e:
            messagebox.showerror('读取失败', f'无法读取该存档：\n{e}')


if __name__ == '__main__':
    root = tk.Tk()
    app = GomokuApp(root)
    root.mainloop()
