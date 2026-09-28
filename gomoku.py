import pickle
import os

maxx = 10
maxy = 10
check_board = [[0 for _ in range(maxy)] for _ in range(maxx)]

# 三方棋子：1 黑方，2 白方，3 红方
PLAYER_COUNT = 3
PLAYER_NAMES = {1: '黑方', 2: '白方', 3: '红方'}
CHESS_MARK = {0: '空', 1: '黑', 2: '白', 3: '红'}


class save_load():
    def __init__(self, maxx, maxy):
        self.maxx = maxx
        self.maxy = maxy
        self.who = 0            # 当前轮到谁：0 黑方，1 白方，2 红方
        self.check_board = None

    def save(self, check_board, who):
        fpath = input('请输入保存路径：')
        self.check_board = check_board
        self.who = who
        with open(fpath, 'wb') as file:
            pickle.dump(self, file)

    def load(self):
        fpath = input('请输入棋盘路径：')
        if os.access(fpath, os.F_OK):
            with open(fpath, 'rb') as file:
                return pickle.load(file)
        else:
            print('文件不存在！')
            return None


# 判读棋局
def inrange(xPoint, yPoint):
    return 0 <= xPoint < maxx and 0 <= yPoint < maxy


def check_five_row(check_board, xPoint, yPoint, xDir, yDir):
    count = 1
    t = check_board[xPoint][yPoint]

    # 沿正方向统计同色棋子
    x, y = xPoint + xDir, yPoint + yDir
    while inrange(x, y) and check_board[x][y] == t:
        count += 1
        x += xDir
        y += yDir

    # 沿反方向统计同色棋子
    x, y = xPoint - xDir, yPoint - yDir
    while inrange(x, y) and check_board[x][y] == t:
        count += 1
        x -= xDir
        y -= yDir

    return count >= 5


def isWin(check_board, xPoint, yPoint):
    result1 = check_five_row(check_board, xPoint, yPoint, 1, 0)   # 横向
    result2 = check_five_row(check_board, xPoint, yPoint, 0, 1)   # 纵向
    result3 = check_five_row(check_board, xPoint, yPoint, 1, 1)   # 斜向 \\
    result4 = check_five_row(check_board, xPoint, yPoint, -1, 1)  # 斜向 /

    # 任意一个方向连成五子即获胜
    return result1 or result2 or result3 or result4
# 判读棋局


# 显示棋盘
def print_check_board(check_board):
    print('       五子棋（黑 / 白 / 红 三人对弈）')
    print('    ' + ''.join(f'{j:^6}' for j in range(maxy)))
    for i in range(maxx):
        print(f'{i:<4}', end='')
        for j in range(maxy):
            print(f'  {CHESS_MARK[check_board[i][j]]}  ', end='')
        print()
# 显示棋盘


# 记录棋局
def record(check_board):
    end_chess = False
    who = 0  # 0 黑方，1 白方，2 红方，黑方先手

    print_check_board(check_board)
    while not end_chess:
        stone = who + 1
        t = input(f'请下子（x,y），现在由{PLAYER_NAMES[stone]}下子：').split(',')

        if len(t) == 2:
            try:
                x = int(t[0].strip())
                y = int(t[1].strip())
            except ValueError:
                print('输入坐标有误，请重新输入！')
                continue

            if not inrange(x, y):
                print('坐标超出棋盘范围，请重下！')
                continue

            if check_board[x][y] == 0:
                check_board[x][y] = stone
                # 判断棋局
                result = isWin(check_board, x, y)
                # 判断棋局

                if result:
                    print(f'{PLAYER_NAMES[stone]}赢！')
                    end_chess = True
                else:
                    who = (who + 1) % PLAYER_COUNT   # 黑 -> 白 -> 红 -> 黑 循环
                    print_check_board(check_board)
            else:
                print('该位置已经有子，请重下！')
        elif len(t) == 1:
            cmd = t[0].strip().upper()
            if cmd == 'S':
                begin_end.save(check_board, who)
            elif cmd == 'L':
                status = begin_end.load()
                if status is not None:
                    check_board = status.check_board
                    who = status.who
                    print_check_board(check_board)
            else:
                print('输入有误，请重新输入！')
        else:
            print('输入有误，请重新输入！')
# 记录棋局


# 主程序
if __name__ == '__main__':
    begin_end = save_load(maxx, maxy)
    record(check_board)
# 主程序
