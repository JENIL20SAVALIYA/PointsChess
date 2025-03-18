import chess
import chess.svg
import sys
from PyQt5.QtCore import Qt, QTimer, QMimeData
from PyQt5.QtGui import QDrag, QPixmap, QPainter
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, QGridLayout,
                            QFrame, QSplitter, QToolBar)
import time
import io

class ChessPieceWidget(QLabel):
    def __init__(self, piece_type, piece_color, parent=None):
        super().__init__(parent)
        self.piece_type = piece_type
        self.piece_color = piece_color
        
        # Create SVG for this piece
        piece_map = {
            (chess.PAWN, chess.WHITE): "white-pawn",
            (chess.KNIGHT, chess.WHITE): "white-knight",
            (chess.BISHOP, chess.WHITE): "white-bishop",
            (chess.ROOK, chess.WHITE): "white-rook",
            (chess.QUEEN, chess.WHITE): "white-queen",
            (chess.KING, chess.WHITE): "white-king",
            (chess.PAWN, chess.BLACK): "black-pawn",
            (chess.KNIGHT, chess.BLACK): "black-knight",
            (chess.BISHOP, chess.BLACK): "black-bishop",
            (chess.ROOK, chess.BLACK): "black-rook",
            (chess.QUEEN, chess.BLACK): "black-queen",
            (chess.KING, chess.BLACK): "black-king",
        }
        
        # Create piece SVG
        piece_svg = chess.svg.piece(chess.Piece(piece_type, piece_color))
        
        # Convert SVG to pixmap
        renderer = QSvgRenderer()
        renderer.load(bytes(piece_svg, 'utf-8'))
        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.transparent)
        
        # Use QPainter to paint on the pixmap
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        # Set pixmap to label
        self.setPixmap(pixmap)
        self.setFixedSize(50, 50)
        
        # Enable dragging
        self.setAcceptDrops(False)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        # Start drag operation
        mime_data = QMimeData()
        mime_data.setText(f"{self.piece_type},{self.piece_color}")
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self.pixmap())
        drag.setHotSpot(event.pos())
        
        drag.exec_(Qt.CopyAction)

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
        self.svg_widget.mouseMoveEvent = self.mouse_move_event
        
        # Setup drag and drop
        self.svg_widget.setAcceptDrops(True)
        self.svg_widget.dragEnterEvent = self.drag_enter_event
        self.svg_widget.dropEvent = self.drop_event
        
        # Update the board display
        self.update_board()
        
    def update_board(self):
        """Update the board display"""
        svg_data = chess.svg.board(self.board, size=600).encode('UTF-8')
        self.svg_widget.load(svg_data)
        
    def get_square_at_position(self, pos):
        """Get chess square at mouse position"""
        x = pos.x() * 8 // self.svg_widget.width()
        y = (self.svg_widget.height() - pos.y()) * 8 // self.svg_widget.height()
        
        # Validate coordinates (ensure they're within the board)
        if x < 0 or x > 7 or y < 0 or y > 7:
            return None
            
        # Calculate square index (0-63)
        return chess.square(x, y)
        
    def mouse_press_event(self, event):
        """Handle mouse press events for piece movement"""
        square = self.get_square_at_position(event.pos())
        
        if square is None:
            return
            
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
                
    def mouse_move_event(self, event):
        """Handle mouse move events for piece dragging"""
        # Only implement if needed for highlighting squares
        pass
    
    def drag_enter_event(self, event):
        """Handle drag enter events for piece placement"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def drop_event(self, event):
        """Handle drop events for piece placement"""
        if event.mimeData().hasText():
            piece_data = event.mimeData().text().split(',')
            if len(piece_data) != 2:
                return
                
            try:
                piece_type = int(piece_data[0])
                piece_color = bool(int(piece_data[1]))
                
                # Get the square at the drop position
                square = self.get_square_at_position(event.pos())
                if square is not None:
                    # Place the piece on the board
                    self.board.set_piece_at(square, chess.Piece(piece_type, piece_color))
                    self.update_board()
                    event.acceptProposedAction()
            except (ValueError, IndexError):
                pass

class PieceSetupPanel(QWidget):
    def __init__(self, chess_board, parent=None):
        super().__init__(parent)
        self.chess_board = chess_board
        
        # Create layouts
        main_layout = QVBoxLayout()
        
        # Add a palette of pieces for dragging
        piece_palette = QGridLayout()
        piece_palette.setSpacing(5)
        
        # Add white pieces
        white_pieces = [
            (chess.PAWN, "P"),
            (chess.KNIGHT, "N"),
            (chess.BISHOP, "B"),
            (chess.ROOK, "R"),
            (chess.QUEEN, "Q"),
            (chess.KING, "K")
        ]
        
        # Add black pieces
        black_pieces = [
            (chess.PAWN, "P"),
            (chess.KNIGHT, "N"),
            (chess.BISHOP, "B"),
            (chess.ROOK, "R"),
            (chess.QUEEN, "Q"),
            (chess.KING, "K")
        ]
        
        # Create piece widgets
        row = 0
        col = 0
        for piece_type, symbol in white_pieces:
            piece_widget = ChessPieceWidget(piece_type, chess.WHITE)
            piece_palette.addWidget(piece_widget, row, col)
            piece_palette.addWidget(QLabel(symbol), row, col+1)
            col += 2
            
        row = 1
        col = 0
        for piece_type, symbol in black_pieces:
            piece_widget = ChessPieceWidget(piece_type, chess.BLACK)
            piece_palette.addWidget(piece_widget, row, col)
            piece_palette.addWidget(QLabel(symbol), row, col+1)
            col += 2
            
        # Add piece palette to main layout
        piece_frame = QFrame()
        piece_frame.setFrameShape(QFrame.StyledPanel)
        piece_frame.setLayout(piece_palette)
        main_layout.addWidget(QLabel("Drag pieces to place them on the board:"))
        main_layout.addWidget(piece_frame)
        
        # Clear board button
        self.clear_button = QPushButton("Clear Board")
        self.clear_button.clicked.connect(self.clear_board)
        main_layout.addWidget(self.clear_button)
        
        # Add delete zone for removing pieces
        delete_label = QLabel("Drop here to remove pieces")
        delete_label.setAlignment(Qt.AlignCenter)
        delete_label.setStyleSheet("background-color: #ffdddd; border: 1px solid #ff0000;")
        delete_label.setMinimumHeight(50)
        delete_label.setAcceptDrops(True)
        delete_label.dragEnterEvent = self.delete_drag_enter
        delete_label.dropEvent = self.delete_drop
        main_layout.addWidget(delete_label)
        
        # Set layout
        self.setLayout(main_layout)
        
    def clear_board(self):
        """Clear the board"""
        self.chess_board.board.clear()
        self.chess_board.update_board()
        
    def delete_drag_enter(self, event):
        """Handle drag enter events for piece deletion"""
        event.acceptProposedAction()
        
    def delete_drop(self, event):
        """Handle drop events for piece deletion"""
        # No need to do anything - just accepting the drop means
        # the piece wasn't placed on the board
        event.acceptProposedAction()

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