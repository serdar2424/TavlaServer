from models.board_configuration import BoardConfiguration, Point

def test_default_board_configuration():
    board_config = BoardConfiguration()
    assert len(board_config.points) == 24
    assert board_config.points[0] == Point(player1=0, player2=2)
    assert board_config.points[5] == Point(player1=5, player2=0)
    assert board_config.bar == Point(player1=0, player2=0)

def test_custom_board_configuration():
    custom_points = [
        Point(player1=1, player2=1),
        Point(player1=2, player2=2),
        Point(player1=3, player2=3),
        Point(player1=4, player2=4),
        Point(player1=5, player2=5),
        Point(player1=6, player2=6),
        Point(player1=7, player2=7),
        Point(player1=8, player2=8),
        Point(player1=9, player2=9),
        Point(player1=10, player2=10),
        Point(player1=11, player2=11),
        Point(player1=12, player2=12),
        Point(player1=13, player2=13),
        Point(player1=14, player2=14),
        Point(player1=15, player2=15),
        Point(player1=16, player2=16),
        Point(player1=17, player2=17),
        Point(player1=18, player2=18),
        Point(player1=19, player2=19),
        Point(player1=20, player2=20),
        Point(player1=21, player2=21),
        Point(player1=22, player2=22),
        Point(player1=23, player2=23),
        Point(player1=24, player2=24)
    ]
    board_config = BoardConfiguration(points=custom_points, bar=Point(player1=1, player2=1))
    assert len(board_config.points) == 24
    assert board_config.points[0] == Point(player1=1, player2=1)
    assert board_config.points[23] == Point(player1=24, player2=24)
    assert board_config.bar == Point(player1=1, player2=1)