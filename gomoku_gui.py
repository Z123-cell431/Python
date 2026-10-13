# -*- coding: utf-8 -*-
"""三人五子棋（完整图形界面版）
黑 / 白 / 红 三方轮流，鼠标点击棋盘交叉点落子，先连成五子者胜。
支持自定义玩家姓名、多局累计比分、计时、移动历史、悔棋与存档读档。
仅使用 Python 标准库 tkinter，无需安装任何依赖。
"""
import os
import time
import pickle
import tkinter as tk
from tkinter import messagebox, filedialog

# ---------------- 棋盘参数 ----------------
ROWS = 10
COLS = 10
CELL = 50
MARGIN = 36
BOARD_W = MARGIN * 2 + CELL * (COLS - 1)
BOARD_H = MARGIN * 2 + CELL * (ROWS - 1)
STONE_R = 20
STAR_POINTS = [(2, 2), (2, 7), (7, 2), (7, 7), (4, 4)]

# ---------------- 玩家配置 ----------------
# (棋子值, 默认名, 主色, 描边, 高光)
PLAYER_DEFS = [
    (1, '黑方', '#1A1A1A', '#000000', '#5A5A5A'),
    (2, '白方', '#FAFAFA', '#9E9E9E', '#FFFFFF'),
    (3, '红方', '#E53935', '#7B0000', '#FF8A80'),
]
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (-1, 1))
COL_LETTERS = 'ABCDEFGHIJ'


def inrange(x, y):
    return 0 <= x < ROWS and 0 <= y < COLS


def win_line(board, x, y):
    """若 (x,y) 处棋子形成五连，返回 (方向, 五连坐标列表)；否则 None。"""
    t = board[x][y]
    if t == 0:
        return None
    for dx, dy in DIRECTIONS:
        line = [(x, y)]
        nx, ny = x + dx, y + dy
        while inrange(nx, ny) and board[nx][ny] == t:
            line.append((nx, ny))
            nx += dx
            ny += dy
        nx, ny = x - dx, y - dy
        while inrange(nx, ny) and board[nx][ny] == t:
            line.insert(0, (nx, ny))
            nx -= dx
            ny -= dy
        if len(line) >= 5:
            return (dx, dy), line
    return None


def move_label(x, y):
    return f'{COL_LETTERS[y]}{x + 1}'


class StartDialog:
    """开局前设置三名玩家姓名，模态对话框。"""
    def __init__(self, parent):
        self.names = None
        self.top = tk.Toplevel(parent)
        self.top.title('玩家设置')
        self.top.resizable(False, False)
        self.top.grab_set()
        self.top.transient(parent)

        tk.Label(self.top, text='三人五子棋 · 请输入玩家姓名',
                 font=('微软雅黑', 12, 'bold'), pady=10).pack()

        form = tk.Frame(self.top)
        form.pack(padx=20)
        self.entries = []
        for i, (pid, default, fill, _, _) in enumerate(PLAYER_DEFS):
            row = tk.Frame(form)
            row.pack(anchor='w', pady=5)
            cv = tk.Canvas(row, width=26, height=26, bg='#FAFAFA',
                           highlightthickness=0)
            cv.create_oval(4, 4, 22, 22, fill=fill, outline='#333')
            cv.pack(side='left', padx=(0, 10))
            e = tk.Entry(row, width=18, font=('微软雅黑', 10))
            e.insert(0, default)
            e.pack(side='left')
            self.entries.append(e)
        self.entries[0].focus_set()

        btns = tk.Frame(self.top)
        btns.pack(pady=12)
        tk.Button(btns, text='开始对弈', width=12,
                  command=self.on_ok).pack(side='left', padx=8)
        tk.Button(btns, text='使用默认', width=12,
                  command=self.on_default).pack(side='left', padx=8)
        self.top.bind('<Return>', lambda e: self.on_ok())
        self.top.protocol('WM_DELETE_WINDOW', self.on_default)
        parent.wait_window(self.top)

    def on_ok(self):
        self.names = [e.get().strip() or PLAYER_DEFS[i][1]
                     for i, e in enumerate(self.entries)]
        self.top.destroy()

    def on_default(self):
        self.names = [p[1] for p in PLAYER_DEFS]
        self.top.destroy()


class GomokuApp:
    def __init__(self, root):
        self.root = root
        self.root.title('三人五子棋')
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        # 玩家姓名
        dlg = StartDialog(root)
        self.names = dlg.names or [p[1] for p in PLAYER_DEFS]

        # 累计比分与局数
        self.scores = [0, 0, 0]      # 三方各自胜局数
        self.round_no = 0            # 已进行的局数
        self.start_new_round(first=True)

        # ---------- 布局 ----------
        main = tk.Frame(root)
        main.pack(padx=10, pady=10)

        # 左：棋盘区
        left = tk.Frame(main)
        left.pack(side='left', padx=(0, 10))

        # 顶栏：当前回合 + 计时
        top = tk.Frame(left)
        top.pack(fill='x')
        self.turn_lbl = tk.Label(top, text='', font=('微软雅黑', 13, 'bold'))
        self.turn_lbl.pack(side='left')
        self.timer_lbl = tk.Label(top, text='00:00', font=('Consolas', 11),
                                  fg='#555')
        self.timer_lbl.pack(side='right')

        self.canvas = tk.Canvas(left, width=BOARD_W, height=BOARD_H,
                                bg='#E8B96A', highlightthickness=1,
                                highlightbackground='#8A5A1E')
        self.canvas.pack(pady=(4, 4))
        self.canvas.bind('<Button-1>', self.on_click)

        bottom = tk.Frame(left)
        bottom.pack()
        tk.Button(bottom, text='新局', width=9, command=self.new_round).pack(side='left', padx=3)
        tk.Button(bottom, text='悔棋', width=9, command=self.undo).pack(side='left', padx=3)
        tk.Button(bottom, text='保存', width=9, command=self.save_game).pack(side='left', padx=3)
        tk.Button(bottom, text='读档', width=9, command=self.load_game).pack(side='left', padx=3)

        # 右：信息面板
        right = tk.Frame(main, width=240)
        right.pack(side='left', fill='y')
        right.propagate(False)

        tk.Label(right, text='比分面板', font=('微软雅黑', 11, 'bold'),
                 pady=6).pack(fill='x')

        self.player_cards = []
        for i, (pid, _, fill, outline, hl) in enumerate(PLAYER_DEFS):
            card = tk.Frame(right, relief='solid', bd=1)
            card.pack(fill='x', padx=8, pady=4)
            top2 = tk.Frame(card)
            top2.pack(fill='x', padx=6, pady=(4, 0))
            cv = tk.Canvas(top2, width=22, height=22, bg=right['bg'],
                           highlightthickness=0)
            cv.create_oval(3, 3, 19, 19, fill=fill, outline=outline)
            cv.pack(side='left', padx=(0, 6))
            self.name_lbls = getattr(self, 'name_lbls', [])
            nl = tk.Label(top2, text=self.names[i], font=('微软雅黑', 10, 'bold'))
            nl.pack(side='left')
            self.name_lbls.append(nl)
            self.score_lbls = getattr(self, 'score_lbls', [])
            sl = tk.Label(card, text=f'胜局：{self.scores[i]}',
                          font=('Consolas', 11), fg='#2E7D32')
            sl.pack(anchor='w', padx=8, pady=(0, 4))
            self.score_lbls.append(sl)
            self.player_cards.append(card)

        # 局数与步数
        info = tk.Frame(right)
        info.pack(fill='x', padx=8, pady=(6, 4))
        self.round_lbl = tk.Label(info, text=f'第 {self.round_no + 1} 局',
                                  font=('微软雅黑', 10))
        self.round_lbl.pack(anchor='w')
        self.move_cnt_lbl = tk.Label(info, text='步数：0',
                                     font=('微软雅黑', 10))
        self.move_cnt_lbl.pack(anchor='w')

        # 移动历史
        tk.Label(right, text='移动历史',
                 font=('微软雅黑', 10, 'bold')).pack(fill='x', pady=(10, 2))
        hist_frame = tk.Frame(right)
        hist_frame.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        sb = tk.Scrollbar(hist_frame)
        sb.pack(side='right', fill='y')
        self.history_box = tk.Listbox(hist_frame, height=12,
                                     font=('Consolas', 9),
                                     yscrollcommand=sb.set)
        self.history_box.pack(side='left', fill='both', expand=True)
        sb.config(command=self.history_box.yview)

        # 计时
        self.timer_id = None
        self.start_time = time.time()
        self.tick_timer()

        self.draw_board()
        self.update_turn_label()

    # ---------- 回合控制 ----------
    def start_new_round(self, first=False):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.history = []
        self.who = 0
        self.game_over = False
        self.last_move = None
        self.start_time = time.time()
        if not first:
            self.round_no += 1

    def new_round(self):
        if hasattr(self, 'timer_id') and self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.start_new_round(first=False)
        self.refresh_panel()
        self.history_box.delete(0, 'end')
        self.draw_board()
        self.update_turn_label()
        self.tick_timer()

    def current_stone(self):
        return self.who + 1

    def update_turn_label(self):
        stone = self.current_stone()
        _, _, fill, _, _ = PLAYER_DEFS[stone - 1]
        if self.game_over:
            return
        self.turn_lbl.config(text=f'● 轮到 {self.names[stone - 1]} 落子',
                             fg=fill)

    def refresh_panel(self):
        for i in range(PLAYER_DEFS.__len__()):
            self.name_lbls[i].config(text=self.names[i])
            self.score_lbls[i].config(text=f'胜局：{self.scores[i]}')
            # 当前回合高亮
            bg = '#FFF3E0' if (i == self.who and not self.game_over) else '#FFFFFF'
            self.player_cards[i].config(bg=bg)
        self.round_lbl.config(text=f'第 {self.round_no + 1} 局')
        self.move_cnt_lbl.config(text=f'步数：{len(self.history)}')

    # ---------- 计时 ----------
    def tick_timer(self):
        if not self.game_over:
            elapsed = int(time.time() - self.start_time)
            mm, ss = divmod(elapsed, 60)
            self.timer_lbl.config(text=f'{mm:02d}:{ss:02d}')
        self.timer_id = self.root.after(1000, self.tick_timer)

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
        # 星位
        for sx, sy in STAR_POINTS:
            px, py = self.grid_pos(sx, sy)
            self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                                    fill='#3E2410', outline='')
        # 坐标
        for i in range(ROWS):
            px, py = self.grid_pos(i, 0)
            self.canvas.create_text(px, 14, text=str(i + 1),
                                    fill='#5D3A12', font=('Consolas', 8))
        for j in range(COLS):
            px, py = self.grid_pos(0, j)
            self.canvas.create_text(14, py, text=COL_LETTERS[j],
                                    fill='#5D3A12', font=('Consolas', 8))
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
        _, _, fill, outline, hl = PLAYER_DEFS[stone - 1]
        # 投影
        self.canvas.create_oval(px - STONE_R + 2, py - STONE_R + 3,
                                px + STONE_R + 2, py + STONE_R + 3,
                                fill='#000000', outline='', stipple='gray50')
        # 主体
        self.canvas.create_oval(px - STONE_R, py - STONE_R,
                                px + STONE_R, py + STONE_R,
                                fill=fill, outline=outline, width=2)
        # 高光
        self.canvas.create_oval(px - STONE_R + 4, py - STONE_R + 4,
                                px - 2, py - 2,
                                fill=hl, outline='')

    def highlight_win(self, points):
        for x, y in points:
            px, py = self.grid_pos(x, y)
            self.canvas.create_oval(px - STONE_R + 3, py - STONE_R + 3,
                                    px + STONE_R - 3, py + STONE_R - 3,
                                    outline='#FFD600', width=3)

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
            self.turn_lbl.config(
                text=f'● 该位置已有棋子，{self.names[self.who]} 请重下',
                fg='#D32F2F')
            return
        stone = self.current_stone()
        self.board[x][y] = stone
        self.history.append((x, y, stone, self.who))
        self.last_move = (x, y)

        # 写入历史列表
        self.history_box.insert('end',
            f'{len(self.history):>2}. {self.names[self.who]} {move_label(x, y)}')
        self.history_box.see('end')

        result = win_line(self.board, x, y)
        if result:
            self.game_over = True
            _, points = result
            self.scores[self.who] += 1
            self.draw_board()
            self.highlight_win(points)
            self.refresh_panel()
            self.turn_lbl.config(
                text=f'🎉 {self.names[self.who]} 连成五子，获胜！',
                fg=PLAYER_DEFS[stone - 1][2])
            self.root.after(300, self.after_win, stone)
            return

        if len(self.history) == ROWS * COLS:
            self.game_over = True
            self.draw_board()
            self.refresh_panel()
            self.turn_lbl.config(text='棋盘已满，本局平局！', fg='#333')
            self.root.after(300, self.after_draw)
            return

        self.who = (self.who + 1) % 3
        self.draw_board()
        self.refresh_panel()
        self.update_turn_label()

    def after_win(self, stone):
        winner = self.names[stone - 1]
        again = messagebox.askyesno('本局结束',
            f'{winner} 获胜！\n当前比分：'
            f'{self.names[0]} {self.scores[0]} / '
            f'{self.names[1]} {self.scores[1]} / '
            f'{self.names[2]} {self.scores[2]}\n\n开始下一局？')
        if again:
            self.new_round()

    def after_draw(self):
        again = messagebox.askyesno('本局结束', '棋盘已满，本局平局！\n开始下一局？')
        if again:
            self.new_round()

    def undo(self):
        if self.game_over or not self.history:
            return
        x, y, _, _ = self.history.pop()
        self.board[x][y] = 0
        self.who = (self.who - 1) % 3
        self.last_move = self.history[-1][:2] if self.history else None
        self.history_box.delete(self.history_box.size() - 1)
        self.draw_board()
        self.refresh_panel()
        self.update_turn_label()

    # ---------- 存档 ----------
    def save_game(self):
        path = filedialog.asksaveasfilename(
            title='保存棋局', defaultextension='.pkl',
            filetypes=[('五子棋存档', '*.pkl'), ('所有文件', '*.*')])
        if not path:
            return
        data = {
            'board': self.board, 'history': self.history,
            'who': self.who, 'last_move': self.last_move,
            'names': self.names, 'scores': self.scores,
            'round_no': self.round_no,
        }
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            self.turn_lbl.config(text=f'● 已保存：{os.path.basename(path)}',
                                  fg='#2E7D32')
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
            self.names = data.get('names', self.names)
            self.scores = data.get('scores', [0, 0, 0])
            self.round_no = data.get('round_no', 0)
            self.game_over = False
            self.start_time = time.time()
            # 重建历史列表
            self.history_box.delete(0, 'end')
            for idx, (x, y, stone, who) in enumerate(self.history):
                self.history_box.insert('end',
                    f'{idx + 1:>2}. {self.names[who]} {move_label(x, y)}')
            self.history_box.see('end')
            self.draw_board()
            self.refresh_panel()
            self.update_turn_label()
            self.turn_lbl.config(text=f'● 已读取：{os.path.basename(path)}',
                                 fg='#2E7D32')
        except (OSError, pickle.PickleError, KeyError, TypeError) as e:
            messagebox.showerror('读取失败', f'无法读取该存档：\n{e}')

    def on_close(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = GomokuApp(root)
    root.mainloop()
