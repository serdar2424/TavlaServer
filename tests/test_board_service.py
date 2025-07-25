from services.board import get_pieces_summary, is_gammon, is_backgammon, NUMBER_OF_PLAYER_PIECES
from models.board_configuration import BoardConfiguration, Point


def test_get_pieces_summary_base():
    base_board = BoardConfiguration()

    on_board1, on_bar1, on_opp1 = get_pieces_summary(board_config=base_board, is_player1=True)
    on_board2, on_bar2, on_opp2 = get_pieces_summary(board_config=base_board, is_player1=False)

    assert on_board1 == NUMBER_OF_PLAYER_PIECES
    assert on_board1 == on_board2
    assert on_bar1 == 0
    assert on_bar1 == on_bar2
    assert on_opp1 == 2
    assert on_opp1 == on_opp2


def test_get_pieces_summary_custom():
    base_board = BoardConfiguration()
    base_board.bar.player1 = 4
    base_board.points[22].player1 = 5
    base_board.points[2].player2 = 5

    on_board1, on_bar1, on_opp1 = get_pieces_summary(board_config=base_board, is_player1=True)
    on_board2, on_bar2, on_opp2 = get_pieces_summary(board_config=base_board, is_player1=False)

    assert on_board1 == 20
    assert on_board2 == 20
    assert on_bar1 == 4
    assert on_bar2 == 0
    assert on_opp1 == 7
    assert on_opp2 == 7


def test_is_gammon():
    board = BoardConfiguration()
    assert is_gammon(board, is_player1=True) == False
    assert is_gammon(board, is_player1=False) == False

    board.points = [Point(0, 0) for _ in board.points]
    assert is_gammon(board, is_player1=True) == False
    assert is_gammon(board, is_player1=False) == False

    board.points[7] = Point(0, 15)
    assert is_gammon(board, is_player1=True) == True
    assert is_gammon(board, is_player1=False) == False

    board.points[7] = Point(15, 0)
    assert is_gammon(board, is_player1=True) == False
    assert is_gammon(board, is_player1=False) == True


def test_is_backgammong():
    board = BoardConfiguration()
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == False

    board.points = [Point(0, 0) for _ in board.points]
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == False

    board.points[7] = Point(0, 15)
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == False

    board.points[7] = Point(15, 0)
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == False

    board.points[7] = Point(0, 8)
    board.points[0] = Point(0, 7)
    assert is_backgammon(board, is_player1=True) == True
    assert is_backgammon(board, is_player1=False) == False

    board.points[0] = Point(0, 0)
    board.bar = Point(0, 7)
    assert is_backgammon(board, is_player1=True) == True
    assert is_backgammon(board, is_player1=False) == False

    board.points[7] = Point(8, 0)
    board.points[0] = Point(0, 0)
    board.points[23] = Point(7, 0)
    board.bar = Point(0, 0)
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == True

    board.points[23] = Point(0, 0)
    board.bar = Point(7, 0)
    assert is_backgammon(board, is_player1=True) == False
    assert is_backgammon(board, is_player1=False) == True