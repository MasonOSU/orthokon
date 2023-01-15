"""orthokon_upload game"""

import os.path
import pathlib
import sys
import itertools
import pygame as pg
# pylint: disable = no-name-in-module
from pygame import K_ESCAPE, KEYDOWN, MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP, QUIT, SRCALPHA


class Game:
    """imports object states from other classes;
    runs main logic... test commit"""

    def __init__(self):
        pg.display.init()
        self._window = [pg.display.Info().current_w, pg.display.Info().current_h]
        self._screen = pg.display.set_mode(self._window)
        self._background = Utility.load("background", self._window)
        self._pieces, self._squares = pg.sprite.Group(), pg.sprite.Group()
        self._current, self._origin = None, None
        self._highlight, self._move = None, False
        self._player = "white"

    def env_setup(self):
        """environment setup that doesn't require main loop"""
        board = Board(self._window)
        pg.display.set_caption("Orthokon")
        pg.display.set_icon(Utility.load("game_icon", None))
        board.index(self._pieces, self._squares)

    def highlight(self):
        """draws colors on active squares"""
        for square in self._squares:
            if square.rect.collidepoint(self._current.rect.center):
                square.image.fill((0, 100, 0, 200))
            else:
                square.image.fill((0, 0, 0, 0))
        self._highlight.image.fill((0, 0, 77, 200))

    def move(self, event):
        """watches for move event"""

        if EventMouseDown.determine(event):
            self.move_begin(event)
            self._move = self._current.rect.collidepoint(event.pos) if self._current else False
        if self._move:
            if EventMouseMotion.determine(event):
                self._current.rect.center = event.pos
                self.highlight()
            if EventMouseUp.determine(event):
                self._move = False
                self.move_end()
                self._current = None
                self._origin = None

    def move_begin(self, event):
        """sets current piece being moved"""
        allow = self._player[0].upper() + self._player[1:]
        allow = globals()[allow]
        for piece, square in itertools.product(self._pieces, self._squares):
            if EventMouseDown.select(event, piece.rect) and isinstance(piece, allow):
                self._current = piece
                self._origin = self._current.rect.center
                Piece.draw(self._current, self._pieces, piece)
            if self._origin and square.rect.collidepoint(self._origin):
                self._highlight = square

    def move_end(self):
        """checks move validity"""
        board = Board(self._window)
        border = board.get_rect()
        for piece, square in itertools.product(self._pieces, self._squares):
            Logic.attempt(border, self._current, self._origin, piece, square)
            Logic.pathfind(self._current, self._origin, square)
            Logic.collision(self._current, piece, self._origin, square)

        for square in self._squares:
            Logic.morph(self._current, self._origin, self._pieces, square)

        if not Logic.threshold(self._current.rect.center, self._origin):
            self._player = self.player_change()

    def player_change(self):
        """sets next player by turn"""
        obj = self._player[0].upper() + self._player[1:]
        if isinstance(self._current, globals()[obj]):
            self._player = "black" if self._player == "white" else "white"
        return self._player

    def refresh(self):
        """redraws environment after each game change"""
        board, button = Board(self._window), Button(self._window)
        clock = pg.time.Clock()

        self._screen.blit(self._background, [0, 0])
        board.draw(self._screen)
        self._squares.draw(self._screen)
        self._pieces.draw(self._screen)
        button.restart_draw(self._screen)
        clock.tick(30)
        pg.display.update()

    def start(self):
        """contains main game loop"""
        button = Button(self._window)
        self.env_setup()
        while True:
            for event in pg.event.get():
                EventHandler.manage(event)
                self.move(event)
                button.restart(event)
            self.refresh()


class Button:
    """menu stuff"""

    def __init__(self, size):
        self._size = size[0] * 0.08, size[1] * 0.05
        self._pos = size[0] * 0.05, size[1] * 0.05
        self._restart = Utility.load("button_new_game", self._size)
        self._restart_rect = self._restart.get_rect(topleft=self._pos)

    def restart(self, event):
        """starts new game"""
        if EventMouseDown.select(event, self._restart_rect):
            Game().start()

    def restart_draw(self, surface):
        """draws restart button"""
        return surface.blit(self._restart, self._restart_rect)


class Logic:
    """main rules logic"""

    @staticmethod
    def attempt(border, current, origin, piece, square):
        """initial attempt, determines boundaries"""
        boundary = not border.collidepoint(current.rect.center)
        conflict = (current.rect.colliderect(piece.rect) and current is not piece)

        if boundary or conflict:
            current.rect.center = origin
        if square.rect.colliderect(current.rect):
            current.rect.center = square.rect.center

    @staticmethod
    def collision(current, piece, origin, square):
        """determines if player collision in path"""
        end = current.rect.center
        collide = square.rect.colliderect(piece.rect)

        vertical = Logic.collision_vertical(collide, end, origin, square)
        horizontal = Logic.collision_horizontal(collide, end, origin, square)
        diagonal = Logic.collision_diagonal(collide, end, origin, square)

        if vertical or horizontal or diagonal:
            current.rect.center = origin

    @staticmethod
    def collision_diagonal(collide, end, origin, square):
        """helper function for collision"""
        path_vert = end[1] < square.rect.center[1] < origin[1] \
                    or origin[1] < square.rect.center[1] < end[1]
        path_hor = end[0] < square.rect.center[0] < origin[0] \
                   or origin[0] < square.rect.center[0] < end[0]

        path_diagonal = path_vert and path_hor
        logic_diagonal = path_diagonal and collide
        collide_diagonal = Logic.diagonal(origin, square) and logic_diagonal

        return collide_diagonal

    @staticmethod
    def collision_vertical(collide, end, origin, square):
        """helper function for collision"""
        end_vert = abs(end[0] - origin[0]) < square.rect[2] / 2
        path_vert = end[1] < square.rect.center[1] < origin[1] \
                    or origin[1] < square.rect.center[1] < end[1]
        logic_vert = end_vert and path_vert and collide
        collide_vert = Logic.vertical(origin, square) and logic_vert

        return collide_vert

    @staticmethod
    def collision_horizontal(collide, end, origin, square):
        """helper function for collision"""
        end_hor = abs(end[1] - origin[1]) < square.rect[3] / 2
        path_hor = end[0] < square.rect.center[0] < origin[0] \
                   or origin[0] < square.rect.center[0] < end[0]
        logic_hor = end_hor and path_hor and collide
        return Logic.horizontal(origin, square) and logic_hor

    @staticmethod
    def diagonal(origin, square, threshold=0.11):
        """determines if diagonal path"""
        diff_x = abs(origin[0] - square.rect.center[0])
        diff_y = abs(origin[1] - square.rect.center[1])
        if diff_y != 0 and diff_x != 0:
            ratio_x = diff_x / diff_y
            ratio_y = diff_y / diff_x
            return abs(ratio_x - ratio_y) < threshold
        return False

    @staticmethod
    def horizontal(origin, square):
        """determines if horizontal path"""
        return abs(square.rect.center[1] - origin[1]) < square.rect[3] / 2

    @staticmethod
    def morph(current, origin, group, square):
        """allows piece morphing"""
        left = current.rect.center[0] - square.rect[2], current.rect.center[1]
        right = current.rect.center[0] + square.rect[2], current.rect.center[1]
        above = current.rect.center[0], current.rect.center[1] - square.rect[2]
        down = current.rect.center[0], current.rect.center[1] + square.rect[2]
        horizontal = square.rect.collidepoint(left) or square.rect.collidepoint(right)
        vertical = square.rect.collidepoint(down) or square.rect.collidepoint(above)

        for piece in group:
            morph_white = isinstance(current, White) and isinstance(piece, Black)
            morph_black = isinstance(current, Black) and isinstance(piece, White)
            collide = square.rect.colliderect(piece.rect)
            present = (horizontal or vertical) and collide

            if not Logic.threshold(current.rect.center, origin):
                if morph_white and present:
                    size, pos = square.rect.size, square.rect
                    piece.kill()
                    del piece
                    group.add(White(size, pos))
                if morph_black and present:
                    size, pos = square.rect.size, square.rect
                    piece.kill()
                    del piece
                    group.add(Black(size, pos))

    @staticmethod
    def pathfind(current, origin, square):
        """judges if vertical or horizontal move"""
        vertical = Logic.vertical(origin, square)
        horizontal = Logic.horizontal(origin, square)
        diagonal = Logic.diagonal(origin, square)

        if current.rect.colliderect(square.rect):
            if vertical:
                return "vertical"
            if horizontal:
                return "horizontal"
            if diagonal:
                return "diagonal"
            current.rect.center = origin
        return False

    @staticmethod
    def threshold(pos1, pos2, error=5):
        """rounding error calc"""
        error_x = abs(pos1[0] - pos2[0]) <= error
        error_y = abs(pos1[1] - pos2[1]) <= error
        return error_x and error_y

    @staticmethod
    def vertical(origin, square):
        """determines if vertical path"""
        return abs(square.rect.center[0] - origin[0]) < square.rect[2] / 2


class Board:
    """contains game board attributes"""

    def __init__(self, window):
        pg.sprite.Sprite().__init__()
        self._board_size = [window[0] * 0.35, window[1] * 0.65]
        self._board_pos = [(window[0] - self._board_size[0]) / 2,
                           ((window[1] - self._board_size[1]) * 1.4 / 2) * 1.05]
        self._board = Utility.load("board", self._board_size)
        self._board_rect = self._board.get_rect(topleft=self._board_pos)
        self._square_size = self._board_size[0] / 4, self._board_size[1] / 4

    def convert(self, row, col):
        """converts row, col integers to screen coordinates"""
        # vice-versa more intuitive for board visual
        row, col = int(col), int(row)
        not_row1 = self._board_pos[0] + (self._square_size[0] * row) - self._square_size[0]
        not_col1 = self._board_pos[1] + ((self._square_size[1] * col) - self._square_size[1])
        row = self._board_pos[0] if row == 1 else not_row1
        col = self._board_pos[1] if col == 1 else not_col1
        return [row, col]

    def draw(self, surface):
        """draws board object"""
        surface.blit(self._board, self._board_rect)

    def get_rect(self):
        """access board rect"""
        return self._board_rect

    def index(self, p_group, s_group):
        """returns square sprite to add, draw"""
        array = [self.convert((num + 1), (num + 1)) for num in range(4)]
        for ((_, col), (row, _)) in itertools.product(array, array):
            square = Square(self._square_size, [row, col])
            square.add(s_group)
            if col == array[0][1]:
                black = Black(self._square_size, [row, col])
                p_group.add(black)
            if col == array[3][1]:
                white = White(self._square_size, [row, col])
                p_group.add(white)


# pylint: disable = too-few-public-methods
class Square(pg.sprite.Sprite):
    """contains square sprite"""

    def __init__(self, size, pos):
        super().__init__()
        self.image = pg.Surface(size, SRCALPHA)
        self.rect = self.image.get_rect(topleft=pos)


class Piece(pg.sprite.Sprite):
    """parent class for colors"""

    def __init__(self, size, pos):
        super().__init__()
        self._size = size[0] * 0.65, size[1] * 0.8
        self._pos = [pos[0] + ((size[0] - self._size[0]) / 2),
                     pos[1] + ((size[1] - self._size[1]) / 2)]

    @staticmethod
    def draw(current, group, piece):
        """draws current over other pieces for aesthetics"""
        if current is piece:
            piece.kill()
            del piece
            group.add(current)


class White(Piece):
    """child class for white sprite"""

    def __init__(self, size, pos):
        super().__init__(size, pos)
        self.image = Utility.load("white", self._size)
        self.rect = self.image.get_rect(topleft=self._pos)


class Black(Piece):
    """child class for black sprite"""

    def __init__(self, size, pos):
        super().__init__(size, pos)
        self.image = Utility.load("black", self._size)
        self.rect = self.image.get_rect(topleft=self._pos)


class EventHandler:
    """manages dictionary of all events"""
    all = {}

    @staticmethod
    def add(key, event):
        """creates new event type for dictionary"""
        EventHandler.all.setdefault(key, [event])

    @staticmethod
    def determine(event):
        """passes event to proper class"""

    @staticmethod
    def manage(event):
        """signals correct events"""
        EventHandler.add(QUIT, EventExit)
        EventHandler.add(KEYDOWN, EventExit)
        EventHandler.add(MOUSEBUTTONDOWN, EventMouseDown)
        EventHandler.add(MOUSEMOTION, EventMouseMotion)
        EventHandler.add(MOUSEBUTTONUP, EventMouseUp)
        EventHandler.notify(event)

    @staticmethod
    def notify(event):
        """signals start of event"""
        if event.type in EventHandler.all:
            for func in EventHandler.all[event.type]:
                func.determine(event)


class EventExit(EventHandler):
    """exits window"""

    @staticmethod
    def determine(event):
        """allows event for escape key or button click"""
        if event.type in [QUIT] or event.key == K_ESCAPE:
            sys.exit(0)


class EventMouseDown(EventHandler):
    """handles piece-, button-select events"""

    @staticmethod
    def determine(event):
        """signals if mouse is down"""
        left = pg.mouse.get_pressed()[0]
        return event.type == MOUSEBUTTONDOWN and left

    @staticmethod
    def select(event, rect):
        """returns piece collision"""
        return EventMouseDown.determine(event) and rect.collidepoint(event.pos)


class EventMouseMotion(EventHandler):
    """handles mouse motion event"""

    @staticmethod
    def determine(event):
        """signals if mouse motion"""
        return event.type == MOUSEMOTION


class EventMouseUp(EventHandler):
    """handles mouse button up event"""

    @staticmethod
    def determine(event):
        """alerts mouse button up"""
        return event.type == MOUSEBUTTONUP


class Utility:
    """contains common static functions"""

    working_dir = pathlib.Path(__file__).parent.resolve()
    rel_dir = os.path.join(working_dir, "res")

    @staticmethod
    def load(src, size):
        """loads, converts, stretches image from relative path"""
        src = os.path.join(Utility.rel_dir, (src + ".png"))
        img = pg.image.load(src).convert_alpha()
        return pg.transform.smoothscale(img, size) if size is not None else img


if __name__ == "__main__":
    game = Game()
    game.start()
