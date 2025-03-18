import chess
import chess.svg
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, QGridLayout,
                            QFrame, QSplitter)
import time

class PointsChessEngine:
    def __init__(self):
        # Point values for each piece type
        self.piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0  # King has no capture value
        }
        
        # Track points for each player
        self.white_points = 0
        self.black_points = 0
        
        # Track moves made
        self.moves_made = 0
        self.max_moves = 6  # 6 moves per player
        
        # Track if extra move is granted
        self.extra_move_granted = False
        
    def reset(self):
        """Reset the engine state for a new game"""
        self.white_points = 0
        self.black_points = 0
        self.moves_made = 0
        self.extra_move_granted = False
        
    def evaluate_position(self, board):
        """Evaluate the current position based on points captured"""
        score = self.white_points - self.black_points
        
        # Check if checkmate is possible
        if board.is_checkmate():
            # If white is checkmated, return very negative score
            # If black is checkmated, return very positive score
            return -10000 if board.turn == chess.WHITE else 10000
            
        return score
    
    def is_piece_supported(self, board, move):
        """Check if the piece being captured is supported by any other piece"""
        if not board.is_capture(move):
            return False
            
        to_square = move.to_square
        capturing_piece = board.piece_at(move.from_square)
        
        # Get the color of the piece being captured
        captured_color = not board.turn
        
        # Check if any piece of the captured color attacks the square
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == captured_color:
                if to_square in board.attacks(square):
                    return True
        
        return False
    
    def calculate_best_move(self, board, depth=3, is_last_move=False):
        """Find the best move considering points chess rules"""
        best_score = float('-inf') if board.turn == chess.WHITE else float('inf')
        best_move = None
        
        legal_moves = list(board.legal_moves)
        
        # Sort moves to check captures first (optimization)
        legal_moves.sort(key=lambda move: board.is_capture(move), reverse=True)
        
        for move in legal_moves:
            # Make the move
            captured_piece = board.piece_at(move.to_square)
            board.push(move)
            
            # Calculate score after move
            if captured_piece:
                capture_value = self.piece_values[captured_piece.piece_type]
                if board.turn == chess.BLACK:  # White captured
                    self.white_points += capture_value
                else:  # Black captured
                    self.black_points += capture_value
            
            # Check for checkmate (immediate win)
            if board.is_checkmate():
                score = 10000 if board.turn == chess.BLACK else -10000
            # If last move and supported piece was captured, need to consider opponent's extra move
            elif is_last_move and captured_piece and self.is_piece_supported(board, move):
                # Opponent gets extra move, so evaluate after that move
                extra_move = self.calculate_best_move(board, depth-1, False)
                if extra_move:
                    # Opponent will make their best move, so use that evaluation
                    score = self.evaluate_position(board)
                else:
                    score = self.evaluate_position(board)
            elif depth > 1:
                # Regular minimax recursion
                next_move = self.calculate_best_move(board, depth-1, False)
                score = self.evaluate_position(board)
            else:
                score = self.evaluate_position(board)
            
            # Undo the move and point calculation
            if captured_piece:
                capture_value = self.piece_values[captured_piece.piece_type]
                if board.turn == chess.WHITE:  # Black captured
                    self.black_points -= capture_value
                else:  # White captured
                    self.white_points -= capture_value
            board.pop()
            
            # Update best move
            if board.turn == chess.WHITE:
                if score > best_score:
                    best_score = score
                    best_move = move
            else:
                if score < best_score:
                    best_score = score
                    best_move = move
        
        return best_move

class ChessBoardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board(chess.STARTING_FEN)
        self.board.clear()  # Start with empty board for manual setup
        
        # Create SVG widget to display the board
        self.svg_widget = QSvgWidget()
        self.svg_widget.setGeometry(0, 0, 600, 600)
        
        # Initialize the layout
        layout = QVBoxLayout()
        layout.addWidget(self.svg_widget)
        self.setLayout(layout)
        
        # Connect mouse events for piece movement
        self.selected_square = None
        self.svg_widget.mousePressEvent = self.mouse_press_event
        
        # Update the board display
        self.update_board()
        
    def update_board(self):
        """Update the board display"""
        svg_data = chess.svg.board(self.board, size=600).encode('UTF-8')
        self.svg_widget.load(svg_data)
        
    def mouse_press_event(self, event):
        """Handle mouse press events for piece movement"""
        # Calculate square coordinates based on mouse position
        x = event.pos().x() * 8 // self.svg_widget.width()
        y = (self.svg_widget.height() - event.pos().y()) * 8 // self.svg_widget.height()
        
        # Validate coordinates (ensure they're within the board)
        if x < 0 or x > 7 or y < 0 or y > 7:
            return
            
        # Calculate square index (0-63)
        square = chess.square(x, y)
        
        # If a square is already selected, try to make a move
        if self.selected_square is not None:
            # Create a move from the selected square to the clicked square
            move = chess.Move(self.selected_square, square)
            
            # Check if the move is legal
            if move in self.board.legal_moves:
                self.board.push(move)
                self.update_board()
            self.selected_square = None
            self.update_board()
        else:
            # If the clicked square has a piece, select it
            if self.board.piece_at(square) is not None:
                self.selected_square = square
                self.update_board()

class PieceSetupPanel(QWidget):
    def __init__(self, chess_board, parent=None):
        super().__init__(parent)
        self.chess_board = chess_board
        
        # Create layouts
        main_layout = QVBoxLayout()
        
        # Piece selection dropdown
        piece_layout = QHBoxLayout()
        self.piece_dropdown = QComboBox()
        pieces = ["White Pawn", "White Knight", "White Bishop", "White Rook", 
                 "White Queen", "White King", "Black Pawn", "Black Knight", 
                 "Black Bishop", "Black Rook", "Black Queen", "Black King", "Empty"]
        self.piece_dropdown.addItems(pieces)
        piece_layout.addWidget(QLabel("Piece:"))
        piece_layout.addWidget(self.piece_dropdown)
        
        # Square selection dropdown
        self.square_dropdown = QComboBox()
        squares = [chess.square_name(square) for square in range(64)]
        self.square_dropdown.addItems(squares)
        piece_layout.addWidget(QLabel("Square:"))
        piece_layout.addWidget(self.square_dropdown)
        
        # Add piece button
        self.add_button = QPushButton("Place Piece")
        self.add_button.clicked.connect(self.place_piece)
        piece_layout.addWidget(self.add_button)
        
        main_layout.addLayout(piece_layout)
        
        # Clear board button
        self.clear_button = QPushButton("Clear Board")
        self.clear_button.clicked.connect(self.clear_board)
        main_layout.addWidget(self.clear_button)
        
        # Set layout
        self.setLayout(main_layout)
        
    def place_piece(self):
        """Place a piece on the board"""
        piece_text = self.piece_dropdown.currentText()
        square_text = self.square_dropdown.currentText()
        
        # Map piece text to chess.Piece
        piece_map = {
            "White Pawn": chess.Piece(chess.PAWN, chess.WHITE),
            "White Knight": chess.Piece(chess.KNIGHT, chess.WHITE),
            "White Bishop": chess.Piece(chess.BISHOP, chess.WHITE),
            "White Rook": chess.Piece(chess.ROOK, chess.WHITE),
            "White Queen": chess.Piece(chess.QUEEN, chess.WHITE),
            "White King": chess.Piece(chess.KING, chess.WHITE),
            "Black Pawn": chess.Piece(chess.PAWN, chess.BLACK),
            "Black Knight": chess.Piece(chess.KNIGHT, chess.BLACK),
            "Black Bishop": chess.Piece(chess.BISHOP, chess.BLACK),
            "Black Rook": chess.Piece(chess.ROOK, chess.BLACK),
            "Black Queen": chess.Piece(chess.QUEEN, chess.BLACK),
            "Black King": chess.Piece(chess.KING, chess.BLACK),
            "Empty": None
        }
        
        # Get the square index
        square = chess.parse_square(square_text)
        
        # Place the piece on the board
        self.chess_board.board.set_piece_at(square, piece_map[piece_text])
        self.chess_board.update_board()
        
    def clear_board(self):
        """Clear the board"""
        self.chess_board.board.clear()
        self.chess_board.update_board()

class PointsChessApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up the main window
        self.setWindowTitle("Points Chess Assistant")
        self.setGeometry(100, 100, 900, 700)
        
        # Create the chess board
        self.chess_board = ChessBoardWidget()
        
        # Create the engine
        self.engine = PointsChessEngine()
        
        # Create the control panel
        self.control_panel = QWidget()
        control_layout = QVBoxLayout()
        
        # Player controls
        player_layout = QHBoxLayout()
        self.white_first_button = QPushButton("White First")
        self.white_first_button.clicked.connect(lambda: self.set_starting_player(chess.WHITE))
        self.black_first_button = QPushButton("Black First")
        self.black_first_button.clicked.connect(lambda: self.set_starting_player(chess.BLACK))
        player_layout.addWidget(self.white_first_button)
        player_layout.addWidget(self.black_first_button)
        control_layout.addLayout(player_layout)
        
        # Move buttons
        move_layout = QHBoxLayout()
        self.best_move_button = QPushButton("Calculate Best Move")
        self.best_move_button.clicked.connect(self.calculate_best_move)
        self.skip_move_button = QPushButton("Skip Turn")
        self.skip_move_button.clicked.connect(self.skip_turn)
        move_layout.addWidget(self.best_move_button)
        move_layout.addWidget(self.skip_move_button)
        control_layout.addLayout(move_layout)
        
        # New game button
        self.new_game_button = QPushButton("New Game")
        self.new_game_button.clicked.connect(self.new_game)
        control_layout.addWidget(self.new_game_button)
        
        # Status display
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        status_layout = QVBoxLayout()
        
        # Turn indicator
        self.turn_label = QLabel("Current Turn: White")
        status_layout.addWidget(self.turn_label)
        
        # Points display
        points_layout = QHBoxLayout()
        self.white_points_label = QLabel("White Points: 0")
        self.black_points_label = QLabel("Black Points: 0")
        points_layout.addWidget(self.white_points_label)
        points_layout.addWidget(self.black_points_label)
        status_layout.addLayout(points_layout)
        
        # Moves counter
        self.moves_label = QLabel("Moves: 0/6")
        status_layout.addWidget(self.moves_label)
        
        # Engine thinking status
        self.engine_status = QLabel("Engine: Ready")
        status_layout.addWidget(self.engine_status)
        
        self.status_frame.setLayout(status_layout)
        control_layout.addWidget(self.status_frame)
        
        # Piece setup panel
        self.setup_panel = PieceSetupPanel(self.chess_board)
        control_layout.addWidget(self.setup_panel)
        
        # Set control panel layout
        self.control_panel.setLayout(control_layout)
        
        # Split the window
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.chess_board)
        splitter.addWidget(self.control_panel)
        splitter.setSizes([600, 300])
        
        # Set the central widget
        self.setCentralWidget(splitter)
        
        # Game state
        self.game_active = False
        
    def set_starting_player(self, color):
        """Set which player goes first"""
        if not self.game_active:
            self.chess_board.board.turn = color
            self.game_active = True
            self.engine.reset()
            self.update_status()
            
    def calculate_best_move(self):
        """Calculate and show the best move"""
        if not self.game_active:
            return
            
        # Update status
        self.engine_status.setText("Engine: Calculating...")
        QApplication.processEvents()
        
        # Determine if this is the last move
        is_last_move = self.engine.moves_made >= 5
        
        # Calculate best move
        start_time = time.time()
        move = self.engine.calculate_best_move(self.chess_board.board, depth=4, is_last_move=is_last_move)
        end_time = time.time()
        
        if move:
            # Get the piece type at the destination square (for capture calculation)
            captured_piece = self.chess_board.board.piece_at(move.to_square)
            
            # Make the move
            self.chess_board.board.push(move)
            
            # Update points if a capture was made
            if captured_piece:
                capture_value = self.engine.piece_values[captured_piece.piece_type]
                if self.chess_board.board.turn == chess.BLACK:  # White captured
                    self.engine.white_points += capture_value
                else:  # Black captured
                    self.engine.black_points += capture_value
                    
                # Check for extra move on last turn
                if is_last_move and self.engine.is_piece_supported(self.chess_board.board, move):
                    self.engine.extra_move_granted = True
            
            # Update moves counter
            self.engine.moves_made += 1
            
            # Update display
            self.chess_board.update_board()
            self.update_status()
            
            # Show calculation time
            calc_time = end_time - start_time
            self.engine_status.setText(f"Engine: Move found in {calc_time:.2f} seconds")
            
            # Check for game end
            self.check_game_end()
        else:
            self.engine_status.setText("Engine: No legal moves found")
            
    def skip_turn(self):
        """Skip the current player's turn"""
        if not self.game_active:
            return
            
        # Switch turns
        self.chess_board.board.turn = not self.chess_board.board.turn
        
        # Update moves counter
        self.engine.moves_made += 1
        
        # Update display
        self.update_status()
        
        # Check for game end
        self.check_game_end()
        
    def new_game(self):
        """Start a new game"""
        # Reset the engine
        self.engine.reset()
        
        # Reset the board (but don't clear it)
        self.chess_board.board.turn = chess.WHITE
        
        # Reset game state
        self.game_active = False
        
        # Update display
        self.update_status()
        self.engine_status.setText("Engine: Ready")
        
    def update_status(self):
        """Update the status display"""
        # Update turn indicator
        turn_text = "White" if self.chess_board.board.turn == chess.WHITE else "Black"
        self.turn_label.setText(f"Current Turn: {turn_text}")
        
        # Update points
        self.white_points_label.setText(f"White Points: {self.engine.white_points}")
        self.black_points_label.setText(f"Black Points: {self.engine.black_points}")
        
        # Update moves counter
        moves_left = 6 - self.engine.moves_made
        if self.engine.extra_move_granted:
            moves_left += 1
        self.moves_label.setText(f"Moves: {self.engine.moves_made}/6 ({moves_left} left)")
        
    def check_game_end(self):
        """Check if the game has ended"""
        # Check for checkmate
        if self.chess_board.board.is_checkmate():
            winner = "Black" if self.chess_board.board.turn == chess.WHITE else "White"
            self.engine_status.setText(f"Game Over: {winner} wins by checkmate!")
            self.game_active = False
            return
            
        # Check if we've reached the move limit
        if self.engine.moves_made >= 6 and not self.engine.extra_move_granted:
            # Determine winner by points
            if self.engine.white_points > self.engine.black_points:
                self.engine_status.setText("Game Over: White wins by points!")
            elif self.engine.black_points > self.engine.white_points:
                self.engine_status.setText("Game Over: Black wins by points!")
            else:
                self.engine_status.setText("Game Over: Draw!")
            self.game_active = False
        # Check if we've used the extra move
        elif self.engine.moves_made >= 7:
            # Determine winner by points
            if self.engine.white_points > self.engine.black_points:
                self.engine_status.setText("Game Over: White wins by points!")
            elif self.engine.black_points > self.engine.white_points:
                self.engine_status.setText("Game Over: Black wins by points!")
            else:
                self.engine_status.setText("Game Over: Draw!")
            self.game_active = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PointsChessApp()
    window.show()
    sys.exit(app.exec_())
