class TicTacToe:
    ALL_SPACES = list('123456789')  # Keys for the game board dictionary
    X, O, BLANK = 'X', 'O', ' '  # Constants for board values

    def __init__(self):
        self.board = self.get_blank_board()
        self.current_player = self.X
        self.next_player = self.O

    def get_blank_board(self):
        """Creates a new, blank game board."""
        return {space: self.BLANK for space in self.ALL_SPACES}

    def get_board_str(self):
        """Returns a string representation of the board."""
        b = self.board
        return f'''
                {b['1']}|{b['2']}|{b['3']} 1 2 3 
                -+-+- 
                {b['4']}|{b['5']}|{b['6']} 4 5 6 
                -+-+- 
                {b['7']}|{b['8']}|{b['9']} 7 8 9'''

    def is_valid_space(self, space):
        """Returns True if the space on the board is valid and empty."""
        return space in self.ALL_SPACES and self.board[space] == self.BLANK

    def is_winner(self, player):
        """Returns True if the player has won on this board."""
        b, p = self.board, player
        return ((b['1'] == b['2'] == b['3'] == p) or
                (b['4'] == b['5'] == b['6'] == p) or
                (b['7'] == b['8'] == b['9'] == p) or
                (b['1'] == b['4'] == b['7'] == p) or
                (b['2'] == b['5'] == b['8'] == p) or
                (b['3'] == b['6'] == b['9'] == p) or
                (b['3'] == b['5'] == b['7'] == p) or
                (b['1'] == b['5'] == b['9'] == p))

    def is_board_full(self):
        """Returns True if all spaces on the board are taken."""
        return all(self.board[space] != self.BLANK for space in self.ALL_SPACES)

    def update_board(self, space, mark):
        """Sets the board space to the given mark."""
        self.board[space] = mark

    def play(self):
        """Main game loop."""
        print('Welcome to Tic Tac Toe!')
        while True:
            print(self.get_board_str())

            move = None
            while not self.is_valid_space(move):
                print(f'What is {self.current_player}\'s move? (1-9)')
                move = input()
                if move not in self.ALL_SPACES:
                    print("Please select a number from 1 to 9.")
                    move = None
                    continue

            self.update_board(move, self.current_player)

            if self.is_winner(self.current_player):
                print(self.get_board_str())
                print(f'{self.current_player} has won the game!')
                break
            elif self.is_board_full():
                print(self.get_board_str())
                print('The game is a tie!')
                break

            self.current_player, self.next_player = self.next_player, self.current_player
        print('Thanks for playing!')

game = TicTacToe()
game.play()

