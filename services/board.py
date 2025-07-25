from models.board_configuration import BoardConfiguration


NUMBER_OF_PLAYER_PIECES = 15


def is_gammon(board_config: BoardConfiguration, is_player1: bool) -> bool:
    '''
        Determines if a player committed a gammon.
        
        Args:
            board_config (BoardConfiguration): The configuration of the game board.
            is_player1 (bool): Whether to check for gammon by player1 or player2.
        Returns:
            bool: Whether the player has committed a gammon. 
    '''

    on_board_player, on_bar_player, _ = get_pieces_summary(board_config, is_player1=is_player1)
    on_board_opp, on_bar_opp, _ = get_pieces_summary(board_config, is_player1=not is_player1)

    return on_board_player + on_bar_player == 0 and on_board_opp + on_bar_opp == NUMBER_OF_PLAYER_PIECES
    

def is_backgammon(board_config: BoardConfiguration, is_player1: bool) -> bool:
    '''
        Determines if a player committed a backgammon.
        
        Args:
            board_config (BoardConfiguration): The configuration of the game board.
            is_player1 (bool): Whether to check for backgammon by player1 or player2.
        Returns:
            bool: Whether the player has committed a backgammon. 
    '''

    on_board_player, on_bar_player, _ = get_pieces_summary(board_config, is_player1=is_player1)
    on_board_opp, on_bar_opp, on_opp_base_opp = get_pieces_summary(board_config, is_player1=not is_player1)

    return (on_board_player + on_bar_player) == 0 and (on_board_opp + on_bar_opp) == NUMBER_OF_PLAYER_PIECES and (on_bar_opp + on_opp_base_opp) > 0
    

def get_pieces_summary(board_config: BoardConfiguration, is_player1: bool) -> tuple[int, int, int]:
    '''
        Returns a summary of the player's pieces distribution on a given board.

        Args:
            Args:
            board_config (BoardConfiguration): The game board configuration.
            is_player1 (bool): Whether to count for player1 or player2.
        Returns:
            (int, int, int): A tuple containing:
                - The number of pieces on the board.
                - The number of pieces on the bar.
                - The number of pieces in the opponent's home board.
    '''

    if is_player1:
        on_board = sum(point.player1 for point in board_config.points)
        on_bar = board_config.bar.player1
        on_opponent_base = sum(point.player1 for point in board_config.points[18: 24])

        return on_board, on_bar, on_opponent_base
    else:
        on_board = sum(point.player2 for point in board_config.points)
        on_bar = board_config.bar.player2
        on_opponent_base = sum(point.player2 for point in board_config.points[0: 6])
        
        return on_board, on_bar, on_opponent_base